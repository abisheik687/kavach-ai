"""
<<<<<<< HEAD
conftest.py — shared test fixtures for KAVACH-AI tests
=======
conftest.py — shared test fixtures for Multimodal Deepfake Detection System Using Advanced Machine Learning Techniques tests
>>>>>>> 7df14d1 (UI enhanced)

Provides:
  - mock_registry: a ModelRegistry with a simple always-0.4 scorer (REAL verdict)
  - fake_registry: a ModelRegistry with a simple always-0.8 scorer (FAKE verdict)
  - test_image_path, test_audio_path, test_video_path: tmp synthetic files
"""

from __future__ import annotations

import io
import os
import tempfile
import uuid
from pathlib import Path
from typing import Callable
from unittest.mock import MagicMock

import numpy as np
import pytest
import soundfile as sf
from PIL import Image


TEMP_DIR = Path(os.getenv('TEMP_DIR', Path(__file__).resolve().parents[1] / 'temp')).resolve()
TEMP_DIR.mkdir(parents=True, exist_ok=True)
tempfile.tempdir = str(TEMP_DIR)


# ─── Synthetic media fixtures ─────────────────────────────────────────────────

@pytest.fixture(scope='session')
def test_image_bytes() -> bytes:
    """A valid 128×128 JPEG image."""
    img = Image.new('RGB', (128, 128), color=(100, 150, 200))
    buf = io.BytesIO()
    img.save(buf, format='JPEG')
    return buf.getvalue()


@pytest.fixture(scope='session')
def test_audio_bytes() -> bytes:
    """A valid 1-second mono WAV file at 16 kHz."""
    sr = 16000
    t = np.linspace(0, 1.0, sr, dtype=np.float32)
    wave = 0.3 * np.sin(2 * np.pi * 440 * t)
    buf = io.BytesIO()
    sf.write(buf, wave, sr, format='WAV', subtype='PCM_16')
    return buf.getvalue()


@pytest.fixture(scope='session')
def test_image_path() -> Path:
    p = TEMP_DIR / f'test_{uuid.uuid4().hex}.jpg'
    img = Image.new('RGB', (128, 128), color=(80, 120, 160))
    img.save(str(p), format='JPEG')
    return p


@pytest.fixture(scope='session')
def test_audio_path() -> Path:
    p = TEMP_DIR / f'test_{uuid.uuid4().hex}.wav'
    sr = 16000
    t = np.linspace(0, 2.0, sr * 2, dtype=np.float32)
    wave = 0.3 * np.sin(2 * np.pi * 440 * t)
    sf.write(str(p), wave, sr, subtype='PCM_16')
    return p


@pytest.fixture(scope='session')
def test_video_path() -> Path:
    """A tiny 10-frame AVI video."""
    import cv2
    p = TEMP_DIR / f'test_{uuid.uuid4().hex}.avi'
    writer = cv2.VideoWriter(str(p), cv2.VideoWriter_fourcc(*'XVID'), 10, (64, 64))
    for i in range(10):
        frame = np.full((64, 64, 3), i * 20, dtype=np.uint8)
        writer.write(frame)
    writer.release()
    return p


# ─── Registry fixtures ────────────────────────────────────────────────────────

def _make_registry(fake_prob: float):
    """Create a ModelRegistry where every model returns `fake_prob`."""
    import sys
    import os
    # Ensure backend is importable
    backend_root = Path(__file__).resolve().parents[1] / 'backend'
    if str(backend_root) not in sys.path:
        sys.path.insert(0, str(backend_root))
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from models.loader import ModelRegistry, LoadedImageModel
    from models.audio_model import AudioModelHandle
    from models.video_model import VideoModelHandle
    from models.image_models import ImageModelSlot

    infer_fn: Callable = lambda *_: fake_prob

    slot = ImageModelSlot(
        key='mock',
        label='MockModel',
        weight=1.0,
        repo_id='mock',
        loader=lambda: (infer_fn, 'mock'),
    )
    reg = ModelRegistry()
    reg.image_models.append(LoadedImageModel(slot=slot, infer=infer_fn, mode='mock'))
    reg.audio_model = AudioModelHandle(infer=lambda *_: fake_prob, mode='mock')
    reg.video_model = VideoModelHandle(infer=lambda _: fake_prob, mode='mock', model_name='mock')
    return reg


@pytest.fixture(scope='session')
def real_registry():
    return _make_registry(0.1)   # always predicts REAL


@pytest.fixture(scope='session')
def fake_registry():
    return _make_registry(0.9)   # always predicts FAKE
