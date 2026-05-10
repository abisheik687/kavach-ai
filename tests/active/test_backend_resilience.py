from __future__ import annotations

import io
import sys
import time
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient
from PIL import Image


BACKEND_DIR = Path(__file__).resolve().parents[2] / 'backend'
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from config import settings
from main import app
from pipelines import audio_pipeline, image_pipeline, video_pipeline
from utils.file_utils import AppError


def _build_jpeg_bytes() -> bytes:
    image = Image.new('RGB', (96, 96), color=(24, 80, 128))
    buffer = io.BytesIO()
    image.save(buffer, format='JPEG')
    return buffer.getvalue()


def _build_fake_mp4_bytes() -> bytes:
    return b'\x00\x00\x00\x18ftypmp42' + (b'\x00' * 2048)


def _build_wav_bytes() -> bytes:
    sample_rate = 16000
    samples = np.linspace(0, 1.0, sample_rate, dtype=np.float32)
    waveform = 0.2 * np.sin(2 * np.pi * 440 * samples)
    buffer = io.BytesIO()
    sf.write(buffer, waveform, sample_rate, format='WAV', subtype='PCM_16')
    return buffer.getvalue()


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


def test_image_timeout_returns_safe_fallback_result(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_prepare_image = image_pipeline.prepare_image

    def slow_prepare_image(_image_bytes: bytes):
        time.sleep(0.25)
        return original_prepare_image(_build_jpeg_bytes())

    monkeypatch.setattr(settings, 'image_timeout_seconds', 0.05)
    monkeypatch.setattr(settings, 'demo_safe_results', True)
    monkeypatch.setattr(image_pipeline, 'prepare_image', slow_prepare_image)

    response = client.post(
        '/analyse',
        files={'file': ('slow.jpg', _build_jpeg_bytes(), 'image/jpeg')},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload['file_type'] == 'image'
    assert payload['verdict'] == 'UNCERTAIN'
    assert payload['fake_probability'] == 0.5
    assert any('safe fallback' in warning.lower() for warning in payload['warnings'])


def test_audio_timeout_returns_safe_fallback_result(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def slow_load_audio(_file_path: Path):
        time.sleep(0.25)
        return np.zeros(16000, dtype=np.float32), 16000

    monkeypatch.setattr(settings, 'audio_timeout_seconds', 0.05)
    monkeypatch.setattr(settings, 'demo_safe_results', True)
    monkeypatch.setattr(audio_pipeline, '_load_audio', slow_load_audio)

    response = client.post(
        '/analyse',
        files={'file': ('slow.wav', _build_wav_bytes(), 'audio/wav')},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload['file_type'] == 'audio'
    assert payload['verdict'] == 'UNCERTAIN'
    assert payload['audio_result'] is not None
    assert payload['audio_result']['fake_probability'] == 0.5
    assert any('safe fallback' in warning.lower() for warning in payload['warnings'])


def test_video_all_frame_failures_return_safe_fallback_result(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frames = [(index, np.full((72, 72, 3), fill_value=index * 10, dtype=np.uint8)) for index in range(3)]

    def fail_frame(*_args):
        raise AppError(504, 'frame timed out', 'ANALYSIS_TIMEOUT')

    monkeypatch.setattr(settings, 'demo_safe_results', True)
    monkeypatch.setattr(video_pipeline, '_extract_frames', lambda _: frames)
    monkeypatch.setattr(video_pipeline, '_analyse_frame', fail_frame)

    response = client.post(
        '/analyse',
        files={'file': ('sample.mp4', _build_fake_mp4_bytes(), 'video/mp4')},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload['file_type'] == 'video'
    assert payload['verdict'] == 'UNCERTAIN'
    assert payload['video_frame_scores'] == []
    assert any('safe fallback' in warning.lower() for warning in payload['warnings'])
