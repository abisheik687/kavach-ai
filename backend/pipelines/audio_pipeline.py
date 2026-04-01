"""
Internal trace:
- Wrong before: package-mode backend launches failed because this pipeline only imported via backend-local module paths.
- Fixed now: audio analysis keeps the same behavior but supports both repo-root and backend-local execution.
"""

from __future__ import annotations

from pathlib import Path

import librosa
import numpy as np
import soundfile as sf
from scipy import signal

try:
    from ..config import settings
    from ..models.loader import ModelRegistry
    from ..schemas.response import AnalysisResult, AudioResult
    from ..utils.file_utils import AppError, clamp
    from ..utils.runtime import run_inference
except ImportError:
    from config import settings
    from models.loader import ModelRegistry
    from schemas.response import AnalysisResult, AudioResult
    from utils.file_utils import AppError, clamp
    from utils.runtime import run_inference


def _build_waveform(audio: np.ndarray, points: int = 96) -> list[float]:
    if audio.size == 0:
        return []
    chunks = np.array_split(audio, points)
    return [round(float(np.mean(np.abs(chunk))), 4) for chunk in chunks if chunk.size]


def _load_audio(file_path: Path) -> tuple[np.ndarray, int]:
    suffix = file_path.suffix.lower()
    if suffix in {'.wav', '.ogg', '.flac'}:
        audio, sample_rate = sf.read(str(file_path), always_2d=False)
        if isinstance(audio, np.ndarray) and audio.ndim > 1:
            audio = audio.mean(axis=1)
        if sample_rate != 16000 and np.asarray(audio).size:
            gcd = np.gcd(sample_rate, 16000)
            audio = signal.resample_poly(np.asarray(audio, dtype=np.float32), 16000 // gcd, sample_rate // gcd)
            sample_rate = 16000
        audio = np.asarray(audio, dtype=np.float32)
        max_samples = settings.max_audio_seconds * sample_rate
        audio = audio[:max_samples]
    else:
        audio, sample_rate = librosa.load(
            str(file_path),
            sr=16000,
            mono=True,
            duration=settings.max_audio_seconds,
        )
    if audio.size == 0:
        raise ValueError('Audio track is empty')
    return audio, sample_rate


async def analyse_audio_file(file_path: Path, registry: ModelRegistry, validation) -> AnalysisResult:
    try:
        audio, sample_rate = await run_inference(
            _load_audio,
            file_path,
            timeout_seconds=settings.audio_timeout_seconds,
            stage='Audio decoding',
        )
    except AppError:
        raise
    except Exception as exc:
        raise AppError(422, 'Audio could not be decoded. Upload a valid WAV, MP3, or OGG file.', 'INVALID_AUDIO_FILE') from exc

    handle = registry.audio_model
    warnings = list(registry.warnings)
    if handle:
        try:
            fake_probability = await run_inference(
                handle.infer,
                audio,
                sample_rate,
                timeout_seconds=settings.audio_timeout_seconds,
                stage='Audio inference',
            )
        except AppError:
            warnings.append('Audio model failed during inference; using neutral fallback score')
            fake_probability = 0.5
    else:
        fake_probability = 0.5

    fake_probability = clamp(fake_probability)
    verdict = 'FAKE' if fake_probability > settings.default_audio_threshold else 'REAL'
    confidence = max(fake_probability, 1.0 - fake_probability)

    return AnalysisResult(
        type=validation.file_type,
        prediction=verdict.lower(),
        confidence=round(confidence * 100.0, 2),
        processing_time='0 ms',
        file_type=validation.file_type,
        verdict=verdict,
        overall_confidence=round(confidence, 4),
        fake_probability=round(fake_probability, 4),
        audio_result=AudioResult(
            verdict=verdict,
            fake_probability=round(fake_probability, 4),
            waveform=_build_waveform(audio),
            mode=handle.mode if handle else 'missing',
            model='ASVspoof-compatible Wav2Vec2' if handle and handle.mode == 'primary' else 'signal-fallback',
        ),
        warnings=warnings,
    )
