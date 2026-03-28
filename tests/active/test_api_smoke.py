"""
Internal trace:
- Wrong before: CI only exercised archived tests for deleted modules, so the current upload pipeline had no reliable automated coverage.
- Fixed now: these smoke tests validate the live FastAPI contract for health, image uploads, audio uploads, and invalid file rejection.
"""

from __future__ import annotations

import io
import math
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


def test_health_endpoint_reports_loaded_model_slots(client: TestClient) -> None:
    response = client.get('/health')

    assert response.status_code == 200
    assert response.json() == {'status': 'ok', 'models_loaded': 5}


def test_analyse_image_returns_live_model_scores(client: TestClient) -> None:
    response = client.post(
        '/analyse',
        files={'file': ('sample.jpg', _build_jpeg_bytes(), 'image/jpeg')},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload['file_type'] == 'image'
    assert payload['verdict'] in {'REAL', 'FAKE', 'UNCERTAIN'}
    assert len(payload['model_scores']) == 4
    assert payload['audio_result'] is None


def test_analyse_audio_returns_audio_result(client: TestClient) -> None:
    response = client.post(
        '/analyse',
        files={'file': ('sample.wav', _build_wav_bytes(), 'audio/wav')},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload['file_type'] == 'audio'
    assert payload['audio_result'] is not None
    assert payload['audio_result']['verdict'] in {'REAL', 'FAKE'}
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
