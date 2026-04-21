"""
<<<<<<< HEAD
KAVACH-AI End-to-End Validation Script
=======
Multimodal Deepfake Detection System Using Advanced Machine Learning Techniques End-to-End Validation Script
>>>>>>> 7df14d1 (UI enhanced)
========================================
Verifies the complete pipeline is working:
  1. Checks artifact manifests exist and are valid
  2. Tests backend health endpoint
  3. Uploads test image/audio/video to /analyse
  4. Validates response schema and model versions
  5. Prints a summary report

Usage (from project root, with backend already running):
    python scripts/validate_e2e.py

To start the backend first:
    cd backend && uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

import io
import json
import sys
import time
from pathlib import Path

import httpx
import numpy as np
import soundfile as sf
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

BACKEND_URL = 'http://localhost:8000'
MANIFEST_PATH = ROOT / 'training' / 'artifacts' / 'manifest.json'
TIMEOUT = 60.0


# ─── Result tracking ─────────────────────────────────────────────────────────

class ResultTracker:
    def __init__(self):
        self.checks: list[tuple[str, bool, str]] = []  # (name, passed, detail)

    def check(self, name: str, condition: bool, detail: str = '') -> bool:
        status = '✓' if condition else '✗'
        print(f'  [{status}] {name}' + (f': {detail}' if detail else ''))
        self.checks.append((name, condition, detail))
        return condition

    def summary(self) -> tuple[int, int]:
        passed = sum(1 for _, ok, _ in self.checks if ok)
        total = len(self.checks)
        return passed, total


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _make_jpeg() -> bytes:
    buf = io.BytesIO()
    Image.new('RGB', (224, 224), color=(100, 150, 200)).save(buf, format='JPEG')
    return buf.getvalue()


def _make_wav() -> bytes:
    sr = 16000
    t = np.linspace(0, 2.0, sr * 2, dtype=np.float32)
    wave = 0.3 * np.sin(2 * np.pi * 440 * t)
    buf = io.BytesIO()
    sf.write(buf, wave, sr, format='WAV', subtype='PCM_16')
    return buf.getvalue()


def _post_file(client: httpx.Client, filename: str, content: bytes, mime: str) -> httpx.Response:
    return client.post(
        f'{BACKEND_URL}/analyse',
        files={'file': (filename, content, mime)},
        timeout=TIMEOUT,
    )


def _divider(char: str = '─', width: int = 56) -> None:
    print(char * width)


# ─── Validation steps ─────────────────────────────────────────────────────────

def check_artifacts(tracker: ResultTracker) -> None:
    _divider()
    print('[1/5] Artifact Manifests')
    _divider()

    manifest_ok = MANIFEST_PATH.exists()
    tracker.check('master manifest.json exists', manifest_ok, str(MANIFEST_PATH) if not manifest_ok else '')
    if not manifest_ok:
        print('  Run: python training/train_all.py')
        return

    manifests = json.loads(MANIFEST_PATH.read_text())
    for modality in ('image', 'audio', 'video'):
        meta_path_str = manifests.get(modality, '')
        meta_path = Path(meta_path_str) if meta_path_str else None
        exists = meta_path is not None and meta_path.exists()
        tracker.check(f'{modality} metadata.json exists', exists, meta_path_str if not exists else '')
        if exists:
            meta = json.loads(meta_path.read_text())
            ckpt = Path(meta.get('checkpoint_path', ''))
            tracker.check(f'{modality} model.pt exists', ckpt.exists(), str(ckpt) if not ckpt.exists() else '')
            onnx = ckpt.parent / 'model.onnx'
            tracker.check(f'{modality} model.onnx exists', onnx.exists(),
                          'ONNX not exported' if not onnx.exists() else f'Using ONNX: {onnx}')


def check_backend_health(client: httpx.Client, tracker: ResultTracker) -> None:
    _divider()
    print('[2/5] Backend Health')
    _divider()
    try:
        response = client.get(f'{BACKEND_URL}/health', timeout=5.0)
        tracker.check('backend is reachable', True)
        tracker.check('health returns 200', response.status_code == 200, str(response.status_code))
        data = response.json()
        warnings = data.get('warnings', [])
        tracker.check('no fallback warnings', len(warnings) == 0,
                      f'{len(warnings)} warnings: {warnings[:2]}' if warnings else '')
        model_versions = data.get('model_versions', {})
        has_trained = any('trained' in str(v).lower() or 'efficientnet' in str(v).lower() or
                          'resnet' in str(v).lower() or 'r3d' in str(v).lower()
                          for v in model_versions.values())
        tracker.check('trained model versions loaded', has_trained, str(model_versions))
    except httpx.ConnectError:
        tracker.check('backend is reachable', False, 'Backend not running — start with: cd backend && uvicorn main:app --reload')


def check_image_analysis(client: httpx.Client, tracker: ResultTracker) -> None:
    _divider()
    print('[3/5] Image Analysis')
    _divider()
    try:
        t0 = time.time()
        response = _post_file(client, 'test.jpg', _make_jpeg(), 'image/jpeg')
        latency_ms = int((time.time() - t0) * 1000)
        tracker.check('image upload returns 200', response.status_code == 200, str(response.status_code))
        if response.status_code == 200:
            data = response.json()
            tracker.check('verdict is REAL/FAKE/UNCERTAIN', data.get('verdict') in ('REAL', 'FAKE', 'UNCERTAIN'), data.get('verdict'))
            prob = data.get('fake_probability', -1)
            tracker.check('fake_probability in [0,1]', 0.0 <= prob <= 1.0, str(prob))
            model_scores = data.get('model_scores', [])
            tracker.check('model_scores is non-empty', len(model_scores) > 0, f'{len(model_scores)} scores')
            modes = [s.get('mode', '') for s in model_scores]
            tracker.check('model mode is trained-local', all(m == 'trained-local' for m in modes), str(modes))
            tracker.check(f'latency < 10s', latency_ms < 10000, f'{latency_ms} ms')
    except httpx.ConnectError:
        tracker.check('image upload succeeds', False, 'Backend not running')


def check_audio_analysis(client: httpx.Client, tracker: ResultTracker) -> None:
    _divider()
    print('[4/5] Audio Analysis')
    _divider()
    try:
        t0 = time.time()
        response = _post_file(client, 'test.wav', _make_wav(), 'audio/wav')
        latency_ms = int((time.time() - t0) * 1000)
        tracker.check('audio upload returns 200', response.status_code == 200, str(response.status_code))
        if response.status_code == 200:
            data = response.json()
            audio_result = data.get('audio_result')
            tracker.check('audio_result is present', audio_result is not None)
            if audio_result:
                tracker.check('waveform data is present', len(audio_result.get('waveform', [])) > 0)
                tracker.check('audio mode is trained-local or mock',
                              audio_result.get('mode', '') in ('trained-local', 'primary', 'mock'),
                              audio_result.get('mode', ''))
    except httpx.ConnectError:
        tracker.check('audio upload succeeds', False, 'Backend not running')


def check_errors(client: httpx.Client, tracker: ResultTracker) -> None:
    _divider()
    print('[5/5] Error Handling')
    _divider()
    try:
        response = client.post(f'{BACKEND_URL}/analyse', timeout=10.0)
        tracker.check('missing file returns 422', response.status_code == 422, str(response.status_code))

        response = _post_file(client, 'bad.txt', b'hello world', 'text/plain')
        tracker.check('wrong type returns 4xx', response.status_code >= 400, str(response.status_code))

        response = _post_file(client, 'corrupt.jpg', b'\xff\xd8\xff\xe0' + b'\x00' * 50, 'image/jpeg')
        tracker.check('corrupt image returns 4xx', response.status_code >= 400, str(response.status_code))
    except httpx.ConnectError:
        tracker.check('error handling works', False, 'Backend not running')


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    print('═' * 56)
<<<<<<< HEAD
    print('KAVACH-AI End-to-End Validation')
=======
    print('Multimodal Deepfake Detection System Using Advanced Machine Learning Techniques End-to-End Validation')
>>>>>>> 7df14d1 (UI enhanced)
    print('═' * 56)

    tracker = ResultTracker()

    with httpx.Client() as client:
        check_artifacts(tracker)
        check_backend_health(client, tracker)
        check_image_analysis(client, tracker)
        check_audio_analysis(client, tracker)
        check_errors(client, tracker)

    passed, total = tracker.summary()
    failed = total - passed

    _divider('═')
    print(f'\nVALIDATION SUMMARY: {passed}/{total} checks passed')
    if failed > 0:
        print(f'FAILED: {failed} check(s)')
        for name, ok, detail in tracker.checks:
            if not ok:
                print(f'  ✗ {name}' + (f': {detail}' if detail else ''))
    else:
        print('ALL CHECKS PASSED ✓')
    _divider('═')

    sys.exit(0 if failed == 0 else 1)


if __name__ == '__main__':
    main()
