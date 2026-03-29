from __future__ import annotations

import json
import sys
from pathlib import Path
import shutil
import uuid

from PIL import Image

# Ensure project root is importable
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from training.multimodal_pipeline import DatasetSource, ModalityConfig, RunConfig, build_manifest, set_seed, train_modality


def _make_image(path: Path, color: tuple[int, int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new('RGB', (48, 48), color=color).save(path)


def test_image_training_pipeline_smoke() -> None:
    tmp_path = Path('temp') / f'train-smoke-{uuid.uuid4().hex}'
    if tmp_path.exists():
        shutil.rmtree(tmp_path)
    data_root = tmp_path / 'data' / 'training' / 'faceforensics_pp'
    try:
        for idx in range(6):
            _make_image(data_root / 'real' / f'subject{idx}_frame.png', (20 + idx, 40, 60))
            _make_image(data_root / 'fake' / f'subject{idx}_frame.png', (120 + idx, 80, 40))

        config = RunConfig(
            seed=7,
            output_root=str(tmp_path / 'artifacts'),
            manifest_root=str(tmp_path / 'manifests'),
            train_ratio=0.67,
            val_ratio=0.17,
            test_ratio=0.16,
            datasets=[DatasetSource(name='faceforensics_pp', path=str(data_root), modalities=['image'])],
            image=ModalityConfig(
                architecture='resnet18',
                batch_size=2,
                epochs=1,
                learning_rate=1e-4,
                weight_decay=1e-4,
                pretrained=False,
                image_size=64,
                num_workers=0,
                early_stop_patience=1,
                export_onnx=False,
            ),
            audio=ModalityConfig(
                architecture='audio_spectrogram_resnet18',
                batch_size=2,
                epochs=1,
                learning_rate=1e-4,
                weight_decay=1e-4,
                pretrained=False,
                num_workers=0,
                export_onnx=False,
            ),
            video=ModalityConfig(
                architecture='r3d_18',
                batch_size=1,
                epochs=1,
                learning_rate=1e-4,
                weight_decay=1e-4,
                pretrained=False,
                num_workers=0,
                export_onnx=False,
            ),
        )

        set_seed(config.seed)
        manifest_path = build_manifest(config, 'image')
        assert manifest_path.exists()

        report = train_modality(config, 'image')
        assert report['modality'] == 'image'

        metadata_path = Path(report['metadata_path'])
        metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
        assert metadata['modality'] == 'image'
        assert Path(metadata['checkpoint_path']).exists()

        artifact_dir = Path(report['artifact_dir'])
        assert artifact_dir.joinpath('misclassified.json').exists(), 'misclassified.json missing'

        # report.json must exist and contain cross_dataset key
        report_path = artifact_dir / 'report.json'
        assert report_path.exists(), 'report.json missing'
        saved_report = json.loads(report_path.read_text(encoding='utf-8'))
        assert 'cross_dataset' in saved_report, f'cross_dataset key missing from report.json: {list(saved_report.keys())}'
        assert 'test_metrics' in saved_report, 'test_metrics key missing from report.json'
        assert 'best_val_auc' in saved_report, 'best_val_auc key missing from report.json'

        # history.json must exist
        history_path = artifact_dir / 'history.json'
        assert history_path.exists(), 'history.json missing'

        print(f'  Test AUC: {saved_report["test_metrics"].get("auc", 0):.4f}')
        print(f'  Best val AUC: {saved_report["best_val_auc"]:.4f}')
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)
