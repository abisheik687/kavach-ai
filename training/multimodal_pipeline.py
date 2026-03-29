from __future__ import annotations

import csv
import json
import math
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import librosa
import numpy as np
import soundfile as sf
import torch
import torch.nn.functional as F
import yaml
from PIL import Image
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import GroupShuffleSplit
from torch import nn
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler
from torchvision import transforms

from training.runtime_models import (
    build_audio_model,
    build_image_model,
    build_video_model,
    save_training_artifact,
)


IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
VIDEO_EXTS = {'.mp4', '.avi', '.mov', '.mkv', '.webm'}
AUDIO_EXTS = {'.wav', '.mp3', '.ogg', '.flac', '.m4a'}
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]


@dataclass
class DatasetSource:
    name: str
    path: str
    modalities: list[str]


@dataclass
class ModalityConfig:
    architecture: str
    batch_size: int
    epochs: int
    learning_rate: float
    weight_decay: float
    pretrained: bool = True
    image_size: int = 224
    clip_frames: int = 16
    clip_stride: int = 4
    sample_rate: int = 16000
    max_audio_seconds: int = 4
    n_mels: int = 128
    num_workers: int = 0
    grad_clip: float = 1.0
    early_stop_patience: int = 4
    export_onnx: bool = True


@dataclass
class RunConfig:
    seed: int
    output_root: str
    manifest_root: str
    train_ratio: float
    val_ratio: float
    test_ratio: float
    datasets: list[DatasetSource]
    image: ModalityConfig
    audio: ModalityConfig
    video: ModalityConfig


def _read_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding='utf-8'))


def load_config(path: str | Path) -> RunConfig:
    payload = _read_yaml(Path(path))
    datasets = [DatasetSource(**item) for item in payload['datasets']]
    return RunConfig(
        seed=payload.get('seed', 42),
        output_root=payload.get('output_root', 'training/artifacts'),
        manifest_root=payload.get('manifest_root', 'training/manifests'),
        train_ratio=payload.get('train_ratio', 0.7),
        val_ratio=payload.get('val_ratio', 0.15),
        test_ratio=payload.get('test_ratio', 0.15),
        datasets=datasets,
        image=ModalityConfig(**payload['image']),
        audio=ModalityConfig(**payload['audio']),
        video=ModalityConfig(**payload['video']),
    )


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def infer_label_from_path(path: Path) -> int | None:
    parts = {part.lower() for part in path.parts}
    if 'real' in parts or 'bonafide' in parts:
        return 0
    if 'fake' in parts or 'spoof' in parts:
        return 1
    return None


def infer_group_id(path: Path) -> str:
    parent = path.parent.name
    stem = path.stem
    for token in ('_', '-', ' '):
        if token in stem:
            stem = stem.split(token)[0]
            break
    return f'{parent}:{stem}'


def build_manifest(config: RunConfig, modality: str) -> Path:
    manifest_root = Path(config.manifest_root)
    manifest_root.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_root / f'{modality}_manifest.csv'
    rows: list[dict[str, Any]] = []

    valid_exts = IMAGE_EXTS if modality == 'image' else VIDEO_EXTS if modality == 'video' else AUDIO_EXTS

    for dataset in config.datasets:
        if modality not in dataset.modalities:
            continue
        base = Path(dataset.path)
        if not base.exists():
            continue
        for path in sorted(base.rglob('*')):
            if path.suffix.lower() not in valid_exts:
                continue
            label = infer_label_from_path(path)
            if label is None:
                continue
            rows.append(
                {
                    'dataset': dataset.name,
                    'modality': modality,
                    'path': str(path),
                    'label': label,
                    'group_id': infer_group_id(path),
                }
            )

    if not rows:
        fieldnames = ['dataset', 'modality', 'path', 'label', 'group_id', 'split']
        with manifest_path.open('w', newline='', encoding='utf-8') as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
        return manifest_path

    groups = np.array([row['group_id'] for row in rows])
    labels = np.array([row['label'] for row in rows])
    indices = np.arange(len(rows))

    first_split = GroupShuffleSplit(n_splits=1, train_size=config.train_ratio, random_state=config.seed)
    train_idx, temp_idx = next(first_split.split(indices, labels, groups))

    remaining = config.val_ratio + config.test_ratio
    val_fraction_of_temp = 0.5 if remaining == 0 else config.val_ratio / remaining
    second_split = GroupShuffleSplit(n_splits=1, train_size=val_fraction_of_temp, random_state=config.seed + 1)
    val_rel_idx, test_rel_idx = next(
        second_split.split(indices[temp_idx], labels[temp_idx], groups[temp_idx])
    )

    split_map = {idx: 'train' for idx in train_idx}
    for idx in temp_idx[val_rel_idx]:
        split_map[idx] = 'val'
    for idx in temp_idx[test_rel_idx]:
        split_map[idx] = 'test'

    for idx, row in enumerate(rows):
        row['split'] = split_map[idx]

    fieldnames = ['dataset', 'modality', 'path', 'label', 'group_id', 'split']
    with manifest_path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return manifest_path


class ImageDataset(Dataset):
    def __init__(self, rows: list[dict[str, Any]], image_size: int, train: bool) -> None:
        self.rows = rows
        common = [
            transforms.Resize((image_size, image_size)),
            transforms.ToTensor(),
            transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
        ]
        if train:
            self.transform = transforms.Compose(
                [
                    transforms.Resize((image_size, image_size)),
                    transforms.RandomHorizontalFlip(),
                    transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.15, hue=0.02),
                    transforms.RandomApply([transforms.GaussianBlur(3, sigma=(0.1, 1.6))], p=0.2),
                ]
                + common[1:]
            )
        else:
            self.transform = transforms.Compose(common)

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor]:
        row = self.rows[index]
        image = Image.open(row['path']).convert('RGB')
        return self.transform(image), torch.tensor(int(row['label']), dtype=torch.long)


class AudioDataset(Dataset):
    def __init__(self, rows: list[dict[str, Any]], cfg: ModalityConfig, train: bool) -> None:
        self.rows = rows
        self.cfg = cfg
        self.train = train

    def __len__(self) -> int:
        return len(self.rows)

    def _waveform_to_image(self, audio: np.ndarray, sample_rate: int) -> torch.Tensor:
        if sample_rate != self.cfg.sample_rate:
            audio = librosa.resample(audio, orig_sr=sample_rate, target_sr=self.cfg.sample_rate)
        max_samples = self.cfg.sample_rate * self.cfg.max_audio_seconds
        audio = audio[:max_samples]
        if audio.shape[0] < max_samples:
            audio = np.pad(audio, (0, max_samples - audio.shape[0]))
        if self.train and random.random() < 0.4:
            audio = audio + np.random.normal(0, 0.003, size=audio.shape[0])
        mel = librosa.feature.melspectrogram(
            y=audio,
            sr=self.cfg.sample_rate,
            n_fft=1024,
            hop_length=256,
            n_mels=self.cfg.n_mels,
        )
        log_mel = librosa.power_to_db(mel + 1e-6).astype(np.float32)
        log_mel = (log_mel - log_mel.min()) / max(log_mel.max() - log_mel.min(), 1e-6)
        tensor = torch.from_numpy(log_mel).unsqueeze(0).repeat(3, 1, 1)
        return tensor

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor]:
        row = self.rows[index]
        audio, sample_rate = sf.read(row['path'], always_2d=False)
        if isinstance(audio, np.ndarray) and audio.ndim > 1:
            audio = audio.mean(axis=1)
        audio = np.asarray(audio, dtype=np.float32)
        tensor = self._waveform_to_image(audio, sample_rate)
        return tensor, torch.tensor(int(row['label']), dtype=torch.long)


class VideoDataset(Dataset):
    def __init__(self, rows: list[dict[str, Any]], cfg: ModalityConfig, train: bool) -> None:
        self.rows = rows
        self.cfg = cfg
        self.train = train

    def __len__(self) -> int:
        return len(self.rows)

    def _load_clip(self, path: str) -> torch.Tensor:
        capture = cv2.VideoCapture(path)
        frames: list[np.ndarray] = []
        idx = 0
        try:
            while len(frames) < self.cfg.clip_frames:
                ok, frame = capture.read()
                if not ok:
                    break
                if idx % self.cfg.clip_stride == 0:
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    frame = cv2.resize(frame, (self.cfg.image_size, self.cfg.image_size))
                    if self.train and random.random() < 0.3:
                        frame = cv2.GaussianBlur(frame, (3, 3), 0)
                    frames.append(frame)
                idx += 1
        finally:
            capture.release()
        if not frames:
            frames = [np.zeros((self.cfg.image_size, self.cfg.image_size, 3), dtype=np.uint8)]
        while len(frames) < self.cfg.clip_frames:
            frames.append(frames[-1].copy())
        clip = np.stack(frames[: self.cfg.clip_frames]).astype(np.float32) / 255.0
        clip = (clip - np.asarray(IMAGENET_MEAN, dtype=np.float32)) / np.asarray(IMAGENET_STD, dtype=np.float32)
        return torch.from_numpy(clip).permute(3, 0, 1, 2)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor]:
        row = self.rows[index]
        return self._load_clip(row['path']), torch.tensor(int(row['label']), dtype=torch.long)


def load_manifest_rows(manifest_path: Path, split: str) -> list[dict[str, Any]]:
    with manifest_path.open('r', newline='', encoding='utf-8') as handle:
        return [row for row in csv.DictReader(handle) if row.get('split') == split]


def create_test_dataloader(manifest_path: Path, modality: str, cfg: ModalityConfig) -> DataLoader:
    """Create a DataLoader for test-only evaluation (used in cross-dataset evaluation).

    Unlike create_dataloaders(), this does NOT require train/val splits.
    """
    rows = load_manifest_rows(manifest_path, 'test')
    if not rows:
        # Try loading all rows if split column is missing/inconsistent
        with manifest_path.open('r', newline='', encoding='utf-8') as handle:
            rows = list(__import__('csv').DictReader(handle))
    if not rows:
        raise RuntimeError(f'No samples found in {manifest_path}')
    if modality == 'image':
        dataset = ImageDataset(rows, cfg.image_size, train=False)
    elif modality == 'audio':
        dataset = AudioDataset(rows, cfg, train=False)
    else:
        dataset = VideoDataset(rows, cfg, train=False)
    return DataLoader(dataset, batch_size=cfg.batch_size, shuffle=False, num_workers=cfg.num_workers)


def create_dataloaders(manifest_path: Path, modality: str, cfg: ModalityConfig) -> dict[str, DataLoader]:
    rows = {split: load_manifest_rows(manifest_path, split) for split in ('train', 'val', 'test')}
    if not rows['train']:
        raise RuntimeError(
            f'No training samples found for {modality}. Populate the dataset paths in training/multimodal_config.yaml first.'
        )
    if not rows['val']:
        raise RuntimeError(
            f'No validation samples found for {modality}. Ensure the dataset contains enough grouped samples for a val split.'
        )
    if not rows['test']:
        raise RuntimeError(
            f'No test samples found for {modality}. Ensure the dataset contains enough grouped samples for a test split.'
        )
    if modality == 'image':
        datasets = {
            split: ImageDataset(split_rows, cfg.image_size, train=split == 'train')
            for split, split_rows in rows.items()
        }
    elif modality == 'audio':
        datasets = {
            split: AudioDataset(split_rows, cfg, train=split == 'train')
            for split, split_rows in rows.items()
        }
    else:
        datasets = {
            split: VideoDataset(split_rows, cfg, train=split == 'train')
            for split, split_rows in rows.items()
        }

    labels = [int(row['label']) for row in rows['train']]
    class_counts = np.bincount(labels) if labels else np.array([1, 1])
    class_weights = 1.0 / np.maximum(class_counts, 1)
    sample_weights = torch.tensor([class_weights[label] for label in labels], dtype=torch.float32) if labels else torch.tensor([])
    sampler = (
        WeightedRandomSampler(sample_weights, num_samples=len(sample_weights), replacement=True)
        if len(sample_weights) > 0
        else None
    )

    return {
        'train': DataLoader(
            datasets['train'],
            batch_size=cfg.batch_size,
            sampler=sampler,
            shuffle=sampler is None and len(datasets['train']) > 0,
            num_workers=cfg.num_workers,
        ),
        'val': DataLoader(datasets['val'], batch_size=cfg.batch_size, shuffle=False, num_workers=cfg.num_workers),
        'test': DataLoader(datasets['test'], batch_size=cfg.batch_size, shuffle=False, num_workers=cfg.num_workers),
    }


def _compute_metrics(labels: list[int], probs: list[float]) -> dict[str, float]:
    if not labels:
        return {'accuracy': 0.0, 'precision': 0.0, 'recall': 0.0, 'f1': 0.0, 'auc': 0.0}
    preds = [1 if prob >= 0.5 else 0 for prob in probs]
    metrics = {
        'accuracy': float(accuracy_score(labels, preds)),
        'precision': float(precision_score(labels, preds, zero_division=0)),
        'recall': float(recall_score(labels, preds, zero_division=0)),
        'f1': float(f1_score(labels, preds, zero_division=0)),
    }
    try:
        metrics['auc'] = float(roc_auc_score(labels, probs))
    except ValueError:
        metrics['auc'] = 0.0
    return metrics


def _run_epoch(
    model: nn.Module,
    loader: DataLoader,
    optimizer: torch.optim.Optimizer | None,
    device: str,
    grad_clip: float,
) -> dict[str, float]:
    is_train = optimizer is not None
    model.train(is_train)
    criterion = nn.CrossEntropyLoss()
    total_loss = 0.0
    labels_all: list[int] = []
    probs_all: list[float] = []

    for batch_inputs, batch_labels in loader:
        batch_inputs = batch_inputs.to(device)
        batch_labels = batch_labels.to(device)
        logits = model(batch_inputs)
        loss = criterion(logits, batch_labels)
        if is_train:
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
            optimizer.step()
        total_loss += float(loss.item()) * batch_labels.size(0)
        probs = torch.softmax(logits.detach(), dim=1)[:, 1].cpu().tolist()
        labels_all.extend(batch_labels.cpu().tolist())
        probs_all.extend(probs)

    metrics = _compute_metrics(labels_all, probs_all)
    metrics['loss'] = total_loss / max(len(labels_all), 1)
    return metrics


def _build_model(modality: str, cfg: ModalityConfig) -> nn.Module:
    if modality == 'image':
        return build_image_model(cfg.architecture, pretrained=cfg.pretrained)
    if modality == 'audio':
        return build_audio_model(cfg.architecture, pretrained=cfg.pretrained)
    return build_video_model(cfg.architecture, pretrained=cfg.pretrained)


def _export_onnx(model: nn.Module, modality: str, cfg: ModalityConfig, output_path: Path, device: str) -> None:
    model.eval()
    if modality == 'video':
        dummy = torch.randn(1, 3, cfg.clip_frames, cfg.image_size, cfg.image_size, device=device)
    else:
        dummy = torch.randn(1, 3, cfg.image_size, cfg.image_size, device=device)
    try:
        torch.onnx.export(
            model,
            dummy,
            str(output_path),
            input_names=['input'],
            output_names=['logits'],
            dynamic_axes={'input': {0: 'batch'}, 'logits': {0: 'batch'}},
            opset_version=17,
        )
    except Exception:
        return


def _write_misclassifications(
    model: nn.Module,
    loader: DataLoader,
    device: str,
    output_path: Path,
    rows: list[dict[str, Any]],
) -> None:
    model.eval()
    pointer = 0
    records: list[dict[str, Any]] = []
    with torch.no_grad():
        for batch_inputs, batch_labels in loader:
            logits = model(batch_inputs.to(device))
            probs = torch.softmax(logits, dim=1)[:, 1].cpu().tolist()
            preds = [1 if prob >= 0.5 else 0 for prob in probs]
            labels = batch_labels.tolist()
            for idx, (pred, label, prob) in enumerate(zip(preds, labels, probs)):
                row = rows[pointer + idx]
                if pred != label:
                    records.append(
                        {
                            'path': row['path'],
                            'dataset': row['dataset'],
                            'label': label,
                            'predicted': pred,
                            'fake_probability': round(prob, 6),
                        }
                    )
            pointer += len(labels)
    output_path.write_text(json.dumps(records, indent=2), encoding='utf-8')


def train_modality(config: RunConfig, modality: str) -> dict[str, Any]:
    cfg = getattr(config, modality)
    manifest_path = build_manifest(config, modality)
    loaders = create_dataloaders(manifest_path, modality, cfg)
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    model = _build_model(modality, cfg).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=cfg.learning_rate, weight_decay=cfg.weight_decay)

    best_state: dict[str, torch.Tensor] | None = None
    best_val_auc = -math.inf
    best_epoch = 0
    patience = 0
    history: list[dict[str, Any]] = []

    for epoch in range(1, cfg.epochs + 1):
        train_metrics = _run_epoch(model, loaders['train'], optimizer, device, cfg.grad_clip)
        with torch.no_grad():
            val_metrics = _run_epoch(model, loaders['val'], None, device, cfg.grad_clip)
        history.append({'epoch': epoch, 'train': train_metrics, 'val': val_metrics})
        if val_metrics['auc'] > best_val_auc:
            best_val_auc = val_metrics['auc']
            best_state = {key: value.detach().cpu() for key, value in model.state_dict().items()}
            best_epoch = epoch
            patience = 0
        else:
            patience += 1
            if patience >= cfg.early_stop_patience:
                break

    if best_state is not None:
        model.load_state_dict(best_state)

    with torch.no_grad():
        test_metrics = _run_epoch(model, loaders['test'], None, device, cfg.grad_clip)

    output_dir = Path(config.output_root) / modality / f'{cfg.architecture}_{int(time.time())}'
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_copy = output_dir / 'manifest.csv'
    manifest_copy.write_text(manifest_path.read_text(encoding='utf-8'), encoding='utf-8')
    (output_dir / 'history.json').write_text(json.dumps(history, indent=2), encoding='utf-8')

    preprocessing = {
        'image_size': cfg.image_size,
        'clip_frames': cfg.clip_frames,
        'clip_stride': cfg.clip_stride,
        'sample_rate': cfg.sample_rate,
        'max_audio_seconds': cfg.max_audio_seconds,
        'n_mels': cfg.n_mels,
    }
    checkpoint_path, metadata_path = save_training_artifact(
        model=model.cpu(),
        output_dir=output_dir,
        modality=modality,
        architecture=cfg.architecture,
        metrics={'val_auc': best_val_auc, **test_metrics, 'best_epoch': best_epoch},
        preprocessing=preprocessing,
        datasets=[item.name for item in config.datasets if modality in item.modalities],
    )
    if cfg.export_onnx:
        _export_onnx(model.to(device), modality, cfg, output_dir / 'model.onnx', device)
    test_rows = load_manifest_rows(manifest_path, 'test')
    _write_misclassifications(model.to(device), loaders['test'], device, output_dir / 'misclassified.json', test_rows)

    cross_dataset: dict[str, dict[str, float]] = {}
    for dataset_name in sorted({row['dataset'] for row in test_rows}):
        dataset_rows = [row for row in test_rows if row['dataset'] == dataset_name]
        if not dataset_rows:
            continue
        temp_manifest = output_dir / f'{dataset_name}_test.csv'
        with temp_manifest.open('w', newline='', encoding='utf-8') as handle:
            writer = csv.DictWriter(handle, fieldnames=['dataset', 'modality', 'path', 'label', 'group_id', 'split'])
            writer.writeheader()
            writer.writerows([{**row, 'split': 'test'} for row in dataset_rows])
        # Use create_test_dataloader (not create_dataloaders) — this manifest only has test rows
        dataset_loader = create_test_dataloader(temp_manifest, modality, cfg)
        with torch.no_grad():
            cross_dataset[dataset_name] = _run_epoch(model.to(device), dataset_loader, None, device, cfg.grad_clip)

    report = {
        'modality': modality,
        'architecture': cfg.architecture,
        'artifact_dir': str(output_dir),
        'checkpoint_path': str(checkpoint_path),
        'metadata_path': str(metadata_path),
        'best_epoch': best_epoch,
        'best_val_auc': best_val_auc,
        'test_metrics': test_metrics,
        'cross_dataset': cross_dataset,
    }
    (output_dir / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report
