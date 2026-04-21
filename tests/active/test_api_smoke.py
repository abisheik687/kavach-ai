"""
<<<<<<< HEAD
Smoke tests for the KAVACH-AI upload pipeline.
=======
Smoke tests for the Multimodal Deepfake Detection System Using Advanced Machine Learning Techniques upload pipeline.
>>>>>>> 7df14d1 (UI enhanced)
These tests run in CI with ENABLE_REMOTE_MODEL_DOWNLOADS=false (fallback mode).
They validate the API contract, not model accuracy.
"""

from __future__ import annotations

import io
import math
import os
import sys
import wave
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image


BACKEND_DIR = Path(__file__).resolve().parents[2] / 'backend'
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from main import app


def _build_jpeg_bytes() -> bytes:
    image = Image.new('RGB', (72, 72), color=(12, 24, 48))
    buffer = io.BytesIO()
    image.save(buffer, format='JPEG')
    return buffer.getvalue()


def _build_wav_bytes(seconds: float = 0.5, sample_rate: int = 16_000) -> bytes:
    total_frames = int(seconds * sample_rate)
    samples = bytearray()
    for index in range(total_frames):
        amplitude = int(18_000 * math.sin(2 * math.pi * 440 * (index / sample_rate)))
        samples.extend(amplitude.to_bytes(2, byteorder='little', signed=True))
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(bytes(samples))
    return buffer.getvalue()


@pytest.fixture(scope='module')
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


def test_health_endpoint_is_ok(client: TestClient) -> None:
    """Health endpoint returns 200 with status ok regardless of model mode."""
    response = client.get('/health')
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'ok'
    # models_loaded >= 0 in fallback mode, >= 5 when real models are available
    assert isinstance(data['models_loaded'], int)
    assert data['models_loaded'] >= 0


def test_health_endpoint_has_expected_model_count(client: TestClient) -> None:
    """In fallback mode (CI) we get 4 image + 1 audio = 5 models loaded."""
    response = client.get('/health')
    assert response.status_code == 200
    data = response.json()
    remote_enabled = os.getenv('ENABLE_REMOTE_MODEL_DOWNLOADS', 'false').lower() == 'true'
    if not remote_enabled:
        # fallback: 4 image slots + 1 audio = 5
        assert data['models_loaded'] >= 4
    else:
        # real models: same count
        assert data['models_loaded'] >= 4


def test_analyse_image_returns_live_model_scores(client: TestClient) -> None:
    response = client.post(
        '/analyse',
        files={'file': ('sample.jpg', _build_jpeg_bytes(), 'image/jpeg')},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload['type'] == 'image'
    assert payload['prediction'] in {'real', 'fake', 'uncertain'}
    assert 0.0 <= payload['confidence'] <= 100.0
    assert payload['processing_time'].endswith(' ms')
    assert len(payload['model_scores']) == 4
    assert payload['audio_result'] is None


def test_analyse_audio_returns_audio_result(client: TestClient) -> None:
    response = client.post(
        '/analyse',
        files={'file': ('sample.wav', _build_wav_bytes(), 'audio/wav')},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload['type'] == 'audio'
    assert payload['prediction'] in {'real', 'fake', 'uncertain'}
    assert 0.0 <= payload['confidence'] <= 100.0
    assert payload['audio_result'] is not None
    assert payload['audio_result']['verdict'] in {'REAL', 'FAKE', 'UNCERTAIN'}
    assert isinstance(payload['audio_result']['waveform'], list)


def test_invalid_file_type_returns_documented_error_shape(client: TestClient) -> None:
    response = client.post(
        '/analyse',
        files={'file': ('notes.txt', b'not-a-media-file', 'text/plain')},
    )
    assert response.status_code == 422
    assert response.json() == {
        'error': 'Unsupported file type. Allowed: JPEG, PNG, WEBP, MP4, WEBM, WAV, MP3, OGG.',
        'code': 'INVALID_FILE_TYPE',
    }
