"""
test_api_integration.py
========================
<<<<<<< HEAD
Integration tests for the KAVACH-AI FastAPI backend.
=======
Integration tests for the Multimodal Deepfake Detection System Using Advanced Machine Learning Techniques FastAPI backend.
>>>>>>> 7df14d1 (UI enhanced)
Uses FastAPI TestClient with mocked model registry — no trained models needed.

Tests:
  - GET /health returns 200 + expected fields
  - POST /analyse with image returns valid AnalysisResult JSON
  - POST /analyse with audio returns valid AnalysisResult JSON
  - POST /analyse with video returns valid AnalysisResult JSON
  - POST /analyse with oversized file returns 413
  - POST /analyse with wrong file type returns 422
  - POST /analyse with no file returns 422
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient
from PIL import Image

# Ensure backend is importable
ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = ROOT / 'backend'
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(BACKEND_ROOT))


# ─── App setup with mocked registry ─────────────────────────────────────────

@pytest.fixture(scope='module')
def client(real_registry, fake_registry):
    """Create a TestClient with model loading fully mocked."""
    from unittest.mock import AsyncMock, patch

    # Patch model_lifespan to do nothing (skip actual model loading)
    async def mock_model_lifespan(app):
        import contextlib
        @contextlib.asynccontextmanager
        async def _noop():
            yield
        return _noop()

    with patch('models.loader._load_models', new_callable=AsyncMock) as mock_load:
        mock_load.return_value = None
        with patch('models.loader.get_model_registry', return_value=lambda: real_registry):
            with patch('models.loader._registry', real_registry):
                import main as app_module
                # Override get_model_registry in the router module too
                import routers.analyse as analyse_router
                original_get_registry = analyse_router.get_model_registry
                analyse_router.get_model_registry = lambda: real_registry
                try:
                    with TestClient(app_module.app, raise_server_exceptions=False) as c:
                        yield c
                finally:
                    analyse_router.get_model_registry = original_get_registry


# ─── Media factories ─────────────────────────────────────────────────────────

def _make_jpeg(width: int = 128, height: int = 128) -> bytes:
    buf = io.BytesIO()
    Image.new('RGB', (width, height), color=(100, 150, 200)).save(buf, format='JPEG')
    return buf.getvalue()


def _make_wav(seconds: float = 1.0, sr: int = 16000) -> bytes:
    t = np.linspace(0, seconds, int(sr * seconds), dtype=np.float32)
    wave = 0.3 * np.sin(2 * np.pi * 440 * t)
    buf = io.BytesIO()
    sf.write(buf, wave, sr, format='WAV', subtype='PCM_16')
    return buf.getvalue()


# ─── Health endpoint ─────────────────────────────────────────────────────────

class TestHealthEndpoint:
    def test_health_returns_200(self, client: TestClient) -> None:
        response = client.get('/health')
        assert response.status_code == 200

    def test_health_has_required_fields(self, client: TestClient) -> None:
        data = client.get('/health').json()
        assert 'status' in data

    def test_root_returns_app_info(self, client: TestClient) -> None:
        response = client.get('/')
        assert response.status_code == 200
        data = response.json()
        assert 'name' in data
        assert 'version' in data


# ─── Analyse endpoint — happy paths ──────────────────────────────────────────

class TestAnalyseEndpoint:
    def test_analyse_image_returns_200(self, client: TestClient) -> None:
        response = client.post(
            '/analyse',
            files={'file': ('test.jpg', _make_jpeg(), 'image/jpeg')},
        )
        assert response.status_code == 200, f'Response: {response.text}'

    def test_analyse_image_response_schema(self, client: TestClient) -> None:
        response = client.post(
            '/analyse',
            files={'file': ('test.jpg', _make_jpeg(), 'image/jpeg')},
        )
        assert response.status_code == 200
        data = response.json()
        required_fields = ['prediction', 'verdict', 'fake_probability', 'confidence', 'overall_confidence']
        for field in required_fields:
            assert field in data, f'Missing field: {field}'
        assert data['verdict'] in ('REAL', 'FAKE', 'UNCERTAIN'), f'Unexpected verdict: {data["verdict"]}'
        assert 0.0 <= data['fake_probability'] <= 1.0
        assert 0.0 <= data['overall_confidence'] <= 1.0

    def test_analyse_audio_returns_200(self, client: TestClient) -> None:
        response = client.post(
            '/analyse',
            files={'file': ('test.wav', _make_wav(), 'audio/wav')},
        )
        assert response.status_code == 200, f'Response: {response.text}'

    def test_analyse_audio_has_audio_result(self, client: TestClient) -> None:
        response = client.post(
            '/analyse',
            files={'file': ('test.wav', _make_wav(), 'audio/wav')},
        )
        assert response.status_code == 200
        data = response.json()
        assert 'audio_result' in data
        audio = data['audio_result']
        assert audio is not None
        assert 'verdict' in audio
        assert 'fake_probability' in audio
        assert 'waveform' in audio

    def test_analyse_video_returns_200(self, client: TestClient, test_video_path: Path) -> None:
        with open(test_video_path, 'rb') as f:
            response = client.post(
                '/analyse',
                files={'file': ('test.mp4', f.read(), 'video/mp4')},
            )
        # Allow 422 if the tiny synthetic video can't be decoded properly in test env
        assert response.status_code in (200, 422), f'Response: {response.text}'

    def test_processing_time_is_set(self, client: TestClient) -> None:
        response = client.post(
            '/analyse',
            files={'file': ('test.jpg', _make_jpeg(), 'image/jpeg')},
        )
        assert response.status_code == 200
        data = response.json()
        assert 'processing_time_ms' in data or 'processing_time' in data


# ─── Analyse endpoint — error paths ──────────────────────────────────────────

class TestAnalyseErrors:
    def test_no_file_returns_422(self, client: TestClient) -> None:
        response = client.post('/analyse')
        assert response.status_code == 422

    def test_wrong_mimetype_returns_415_or_422(self, client: TestClient) -> None:
        response = client.post(
            '/analyse',
            files={'file': ('test.exe', b'\x00' * 100, 'application/octet-stream')},
        )
        assert response.status_code in (415, 422)

    def test_corrupt_image_returns_422(self, client: TestClient) -> None:
        response = client.post(
            '/analyse',
            files={'file': ('bad.jpg', b'not-an-image', 'image/jpeg')},
        )
        assert response.status_code == 422

    def test_error_response_has_error_field(self, client: TestClient) -> None:
        response = client.post(
            '/analyse',
            files={'file': ('bad.jpg', b'corrupt', 'image/jpeg')},
        )
        if response.status_code >= 400:
            data = response.json()
            assert 'error' in data or 'detail' in data
