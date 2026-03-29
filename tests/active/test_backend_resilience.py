from __future__ import annotations

import io
import sys
import time
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image


BACKEND_DIR = Path(__file__).resolve().parents[2] / 'backend'
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from config import settings
from main import app
from pipelines import image_pipeline, video_pipeline


def _build_jpeg_bytes() -> bytes:
    image = Image.new('RGB', (96, 96), color=(24, 80, 128))
    buffer = io.BytesIO()
    image.save(buffer, format='JPEG')
    return buffer.getvalue()


def _build_fake_mp4_bytes() -> bytes:
    return b'\x00\x00\x00\x18ftypmp42' + (b'\x00' * 2048)


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


def test_video_endpoint_returns_bounded_scores_when_audio_is_unavailable(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frames = [(index, np.full((72, 72, 3), fill_value=index * 10, dtype=np.uint8)) for index in range(6)]

    monkeypatch.setattr(video_pipeline, '_extract_frames', lambda _: frames)
    monkeypatch.setattr(video_pipeline, '_extract_audio_track', lambda *_args: None)

    response = client.post(
        '/analyse',
        files={'file': ('sample.mp4', _build_fake_mp4_bytes(), 'video/mp4')},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload['file_type'] == 'video'
    assert len(payload['video_frame_scores']) == len(frames)
    assert len(payload['video_frame_previews']) <= settings.max_video_previews
    assert payload['audio_result'] is None
    assert any('audio track could not be extracted' in warning.lower() for warning in payload['warnings'])


def test_image_timeout_returns_documented_error_code(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_prepare_image = image_pipeline.prepare_image

    def slow_prepare_image(_image_bytes: bytes):
        time.sleep(0.25)
        return original_prepare_image(_build_jpeg_bytes())

    monkeypatch.setattr(settings, 'image_timeout_seconds', 0.05)
    monkeypatch.setattr(image_pipeline, 'prepare_image', slow_prepare_image)

    response = client.post(
        '/analyse',
        files={'file': ('slow.jpg', _build_jpeg_bytes(), 'image/jpeg')},
    )

    assert response.status_code == 504
    assert response.json() == {
        'error': 'Image analysis timed out before analysis could finish.',
        'code': 'ANALYSIS_TIMEOUT',
    }
