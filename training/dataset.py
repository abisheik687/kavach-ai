"""
<<<<<<< HEAD
KAVACH-AI Training Dataset — PyTorch Dataset class
=======
Multimodal Deepfake Detection System Using Advanced Machine Learning Techniques Training Dataset — PyTorch Dataset class
>>>>>>> 7df14d1 (UI enhanced)
===================================================
Reads dataset_manifest.csv.
Applies augmentation pipeline on training split only.
All splits share the same normalisation (ImageNet stats).
"""
import csv
import io
import random
from pathlib import Path
from typing import Literal

import numpy as np
import torch
from PIL import Image
from torch.utils.data import Dataset, DataLoader, WeightedRandomSampler
from torchvision import transforms
from torchvision.transforms import functional as TF

# ImageNet normalisation — same as HuggingFace ViT and timm defaults
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD  = [0.229, 0.224, 0.225]
IMG_SIZE      = 224


class JPEGCompressionAugment:
    """
    Simulate JPEG compression artefacts — critical for deepfake detection.
    Real social-media deepfakes are almost always JPEG-compressed.
    """
    def __init__(self, quality_low: int = 50, quality_high: int = 95):
        self.quality_low  = quality_low
        self.quality_high = quality_high

    def __call__(self, img: Image.Image) -> Image.Image:
        quality = random.randint(self.quality_low, self.quality_high)
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=quality)
        buf.seek(0)
        return Image.open(buf).copy()  # .copy() detaches from BytesIO


def build_transforms(split: Literal['train','val','test']) -> transforms.Compose:
    """
    Return the correct transform pipeline for the given split.
    Training: augmentation + normalise.
    Val/Test: resize + normalise only.
    """
    normalise = transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD)

    if split == 'train':
        return transforms.Compose([
            transforms.Resize((IMG_SIZE, IMG_SIZE)),
            # ── Geometric augmentations ──────────────────────────────
            transforms.RandomHorizontalFlip(p=0.5),
            transforms.RandomRotation(degrees=10),
            transforms.RandomPerspective(distortion_scale=0.1, p=0.2),
            # ── Colour augmentations ─────────────────────────────────
            transforms.ColorJitter(
                brightness=0.2, contrast=0.2,
                saturation=0.1, hue=0.02,
            ),
            transforms.RandomGrayscale(p=0.03),
            # ── Compression artefact simulation ──────────────────────
            JPEGCompressionAugment(quality_low=50, quality_high=95),
            # ── Occasional blur (mimic low-quality deepfakes) ────────
            transforms.RandomApply([transforms.GaussianBlur(3, sigma=(0.1,2.0))], p=0.15),
            # ── Tensor + normalise ───────────────────────────────────
            transforms.ToTensor(),
            normalise,
        ])
    else:
        return transforms.Compose([
            transforms.Resize((IMG_SIZE, IMG_SIZE)),
            transforms.ToTensor(),
            normalise,
        ])


class DeepfakeDataset(Dataset):
    """
<<<<<<< HEAD
    KAVACH-AI deepfake detection dataset.
=======
    Multimodal Deepfake Detection System Using Advanced Machine Learning Techniques deepfake detection dataset.
>>>>>>> 7df14d1 (UI enhanced)
    Reads from dataset_manifest.csv.

    Args:
        manifest_path:  Path to dataset_manifest.csv
        split:          'train' | 'val' | 'test'
        transform:      Override default transforms (optional)
        max_samples:    Cap the dataset size (useful for quick tests)
    """

    def __init__(
        self,
        manifest_path: str | Path,
        split: Literal['train','val','test'],
        transform=None,
        max_samples: int | None = None,
    ):
        self.split     = split
        self.transform = transform or build_transforms(split)
        self.records   = []

        with open(manifest_path, newline='') as f:
            for row in csv.DictReader(f):
                if row['split'] == split:
                    self.records.append({
                        'filepath': row['filepath'],
                        'label':    int(row['label']),
                        'source':   row['source'],
                    })

        if max_samples:
            self.records = self.records[:max_samples]

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, int]:
        rec  = self.records[idx]
        img  = Image.open(rec['filepath']).convert('RGB')
        tensor = self.transform(img)
        return tensor, rec['label']

    def class_weights(self) -> torch.Tensor:
        """
        Compute per-class inverse frequency weights.
        Use with WeightedRandomSampler to handle class imbalance.
        """
        labels = [r['label'] for r in self.records]
        counts = np.bincount(labels)
        weights = 1.0 / counts
        sample_weights = torch.tensor([weights[l] for l in labels], dtype=torch.float)
        return sample_weights


def build_dataloaders(
    manifest_path: str | Path,
    batch_size: int = 32,
    num_workers: int = 4,
    balanced_sampling: bool = True,
) -> dict[str, DataLoader]:
    """
    Convenience factory — returns {'train': ..., 'val': ..., 'test': ...}.

    Args:
        balanced_sampling:  If True, uses WeightedRandomSampler on training
                            set to handle class imbalance automatically.
    """
    loaders = {}
    for split in ('train', 'val', 'test'):
        ds = DeepfakeDataset(manifest_path, split=split)
        if split == 'train' and balanced_sampling:
            sample_weights = ds.class_weights()
            sampler = WeightedRandomSampler(
                weights=sample_weights,
                num_samples=len(ds),
                replacement=True,
            )
            loader = DataLoader(ds, batch_size=batch_size, sampler=sampler,
                                num_workers=num_workers, pin_memory=True,
                                persistent_workers=num_workers > 0)
        else:
            loader = DataLoader(ds, batch_size=batch_size, shuffle=False,
                                num_workers=num_workers, pin_memory=True,
                                persistent_workers=num_workers > 0)
        loaders[split] = loader
    return loaders


if __name__ == '__main__':
    # Smoke test
    import sys
    manifest = sys.argv[1] if len(sys.argv) > 1 else 'training/dataset_manifest.csv'
    loaders = build_dataloaders(manifest, batch_size=8, num_workers=0)
    for split, loader in loaders.items():
        batch, labels = next(iter(loader))
        print(f'{split:>5}  batches={len(loader)}  sample shape={batch.shape}  labels={labels.tolist()}')
    print('dataset.py smoke test PASSED')
