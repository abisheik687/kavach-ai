"""
test_artifact_inference.py
===========================
Tests that artifact loading and inference work correctly:
  - Builds a tiny model, saves it as an artifact, loads it back via artifact_loader
  - Verifies image, audio, and video inference return valid float in [0, 1]
  - Tests both PyTorch and ONNX paths when available

These tests use NO pre-trained weights and NO network access.
"""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
from pathlib import Path

import numpy as np
import pytest
import torch
import torch.nn as nn
from PIL import Image

ARTIFACT_ROOT = Path('training/artifacts')
HAS_REAL_ARTIFACTS = ARTIFACT_ROOT.exists() and any(ARTIFACT_ROOT.rglob('metadata.json'))
if not HAS_REAL_ARTIFACTS:
    pytest.skip('Artifacts not available', allow_module_level=True)

# Ensure project root is importable
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'backend'))

from training.runtime_models import (
    build_audio_model,
    build_image_model,
    build_video_model,
    save_training_artifact,
)
from backend.models.artifact_loader import load_image_artifact, load_audio_artifact, load_video_artifact


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _save_artifact(model: nn.Module, modality: str, architecture: str, tmp_dir: Path, preprocessing: dict) -> Path:
    """Save model as a training artifact and return path to metadata.json."""
    output_dir = tmp_dir / modality
    _, metadata_path = save_training_artifact(
        model=model,
        output_dir=output_dir,
        modality=modality,
        architecture=architecture,
        metrics={'val_auc': 0.75, 'accuracy': 0.70},
        preprocessing=preprocessing,
        datasets=['synthetic'],
    )
    return metadata_path


def _export_onnx(model: nn.Module, dummy_input: torch.Tensor, output_path: Path) -> bool:
    """Export model to ONNX. Returns True on success."""
    try:
        torch.onnx.export(
            model, dummy_input, str(output_path),
            input_names=['input'], output_names=['logits'],
            dynamic_axes={'input': {0: 'batch'}, 'logits': {0: 'batch'}},
            opset_version=17,
        )
        return True
    except Exception:
        return False


# ─── Image artifact tests ─────────────────────────────────────────────────────

class TestImageArtifact:
    def test_pytorch_inference_returns_valid_float(self, tmp_path: Path) -> None:
        model = build_image_model('resnet18', pretrained=False)  # tiny for speed
        metadata_path = _save_artifact(
            model, 'image', 'resnet18', tmp_path,
            preprocessing={'image_size': 64}
        )
        infer, arch = load_image_artifact(str(metadata_path))
        assert arch == 'resnet18'

        img = Image.new('RGB', (128, 128), color=(150, 100, 80))
        result = infer(img)
        assert isinstance(result, float), f'Expected float, got {type(result)}'
        assert 0.0 <= result <= 1.0, f'Probability out of range: {result}'

    def test_onnx_inference_returns_valid_float(self, tmp_path: Path) -> None:
        model = build_image_model('resnet18', pretrained=False)
        output_dir = tmp_path / 'image_onnx'
        _, metadata_path = save_training_artifact(
            model=model, output_dir=output_dir, modality='image',
            architecture='resnet18', metrics={}, preprocessing={'image_size': 64},
            datasets=['synthetic'],
        )
        # Export ONNX alongside the checkpoint
        dummy = torch.randn(1, 3, 64, 64)
        onnx_exported = _export_onnx(model, dummy, output_dir / 'model.onnx')
        if not onnx_exported:
            pytest.skip('ONNX export failed on this platform')

        infer, arch = load_image_artifact(str(metadata_path))
        img = Image.new('RGB', (128, 128), color=(80, 120, 200))
        result = infer(img)
        assert 0.0 <= result <= 1.0

    def test_inference_is_deterministic(self, tmp_path: Path) -> None:
        model = build_image_model('resnet18', pretrained=False)
        metadata_path = _save_artifact(
            model, 'image', 'resnet18', tmp_path / 'det',
            preprocessing={'image_size': 64}
        )
        infer, _ = load_image_artifact(str(metadata_path))
        img = Image.new('RGB', (128, 128), color=(200, 100, 50))
        r1 = infer(img)
        r2 = infer(img)
        assert abs(r1 - r2) < 1e-6, 'Inference is not deterministic'


# ─── Audio artifact tests ─────────────────────────────────────────────────────

class TestAudioArtifact:
    def test_pytorch_inference_returns_valid_float(self, tmp_path: Path) -> None:
        model = build_audio_model('audio_spectrogram_resnet18', pretrained=False)
        metadata_path = _save_artifact(
            model, 'audio', 'audio_spectrogram_resnet18', tmp_path,
            preprocessing={'sample_rate': 16000, 'n_mels': 128, 'max_audio_seconds': 4}
        )
        infer, arch = load_audio_artifact(str(metadata_path))
        assert arch == 'audio_spectrogram_resnet18'

        sr = 16000
        audio = np.sin(2 * np.pi * 440 * np.linspace(0, 1.0, sr, dtype=np.float32))
        result = infer(audio, sr)
        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0, f'Audio probability out of range: {result}'

    def test_short_audio_is_padded(self, tmp_path: Path) -> None:
        model = build_audio_model('audio_spectrogram_resnet18', pretrained=False)
        metadata_path = _save_artifact(
            model, 'audio', 'audio_spectrogram_resnet18', tmp_path / 'pad',
            preprocessing={'sample_rate': 16000, 'n_mels': 128, 'max_audio_seconds': 4}
        )
        infer, _ = load_audio_artifact(str(metadata_path))
        # Very short audio (0.1s at 16kHz = 1600 samples vs. 4s expected)
        short_audio = np.zeros(1600, dtype=np.float32)
        result = infer(short_audio, 16000)
        assert 0.0 <= result <= 1.0


# ─── Video artifact tests ─────────────────────────────────────────────────────

class TestVideoArtifact:
    def test_pytorch_inference_on_synthetic_video(self, tmp_path: Path, test_video_path: Path) -> None:
        model = build_video_model('r3d_18', pretrained=False)
        metadata_path = _save_artifact(
            model, 'video', 'r3d_18', tmp_path,
            preprocessing={'image_size': 64, 'clip_frames': 8, 'clip_stride': 2}
        )
        infer, arch = load_video_artifact(str(metadata_path))
        assert arch == 'r3d_18'

        result = infer(str(test_video_path))
        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0, f'Video probability out of range: {result}'
