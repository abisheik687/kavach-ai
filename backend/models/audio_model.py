"""
Internal trace:
- Wrong before: audio analysis was purely heuristic while claiming a RawNet/LCNN pipeline, and it mixed visualization logic with inference.
- Fixed now: startup loads a Wav2Vec2-based detector when available and falls back to a transparent signal-based scorer when weights are unavailable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
from scipy import signal

from config import settings
from utils.file_utils import clamp


def _resample(audio: np.ndarray, sample_rate: int, target_rate: int = 16000) -> np.ndarray:
    if sample_rate == target_rate or audio.size == 0:
        return audio.astype(np.float32, copy=False)
    gcd = np.gcd(sample_rate, target_rate)
    up = target_rate // gcd
    down = sample_rate // gcd
    return signal.resample_poly(audio, up, down).astype(np.float32, copy=False)


def _spectral_flatness(audio: np.ndarray) -> float:
    spectrum = np.abs(np.fft.rfft(audio)) + 1e-6
    geometric_mean = float(np.exp(np.mean(np.log(spectrum))))
    arithmetic_mean = float(np.mean(spectrum))
    return clamp(geometric_mean / max(arithmetic_mean, 1e-6))


def _spectral_contrast(audio: np.ndarray) -> float:
    spectrum = np.abs(np.fft.rfft(audio)) + 1e-6
    if spectrum.size < 8:
        return 0.0
    bands = np.array_split(spectrum, 6)
    contrasts = []
    for band in bands:
        if band.size == 0:
            continue
        high = np.percentile(band, 90)
        low = np.percentile(band, 10)
        contrasts.append(float(high - low))
    return float(np.mean(contrasts)) if contrasts else 0.0


def signal_fallback(audio: np.ndarray, sample_rate: int) -> float:
    audio = _resample(np.asarray(audio, dtype=np.float32), sample_rate, 16000)
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    if peak < 1e-4:
        return 0.5
    normalized = audio / peak
    spectral_flatness = _spectral_flatness(normalized)
    zero_crossing = float(np.mean(np.abs(np.diff(np.signbit(normalized).astype(np.float32)))))
    contrast = _spectral_contrast(normalized)
    score = (spectral_flatness * 1.8) + (zero_crossing * 0.9) + (contrast * 0.08)
    return clamp(score)


@dataclass
class AudioModelHandle:
    infer: Callable[[np.ndarray, int], float]
    mode: str


def build_fallback_audio_model() -> AudioModelHandle:
    return AudioModelHandle(infer=signal_fallback, mode='fallback')


def build_audio_model() -> AudioModelHandle:
    import torch
    from transformers import Wav2Vec2FeatureExtractor, Wav2Vec2ForSequenceClassification

    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    try:
        extractor = Wav2Vec2FeatureExtractor.from_pretrained(settings.model_audio_repo)
        model = Wav2Vec2ForSequenceClassification.from_pretrained(settings.model_audio_repo)
        model.eval().to(device)

        def infer(audio: np.ndarray, sample_rate: int) -> float:
            inputs = extractor(audio, sampling_rate=sample_rate, return_tensors='pt', padding=True)
            inputs = {key: value.to(device) for key, value in inputs.items()}
            with torch.no_grad():
                logits = model(**inputs).logits
                probs = torch.softmax(logits, dim=-1)[0].detach().cpu().numpy()
            id2label = {int(key): value.lower() for key, value in model.config.id2label.items()}
            fake_indices = [index for index, label in id2label.items() if 'fake' in label or 'spoof' in label]
            if fake_indices:
                return clamp(float(sum(probs[index] for index in fake_indices)))
            return clamp(float(probs[-1]))

        return AudioModelHandle(infer=infer, mode='primary')
    except Exception:
        return build_fallback_audio_model()
