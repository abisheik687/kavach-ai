"""
Internal trace:
- Wrong before: ensemble scoring also depended on cwd-sensitive imports, so package execution could fail before any route loaded.
- Fixed now: the ensemble module is package-safe while preserving the single threshold and uncertainty policy.
"""

from __future__ import annotations

from statistics import mean

try:
    from ..config import settings
except ImportError:
    from config import settings


def _review_thresholds(kind: str) -> tuple[float, float]:
    if kind == 'audio':
        return 0.55, 0.70
    return 0.55, 0.72


def classify_probability(fake_probability: float, kind: str = 'image', threshold: float | None = None) -> tuple[str, float]:
    confidence = max(fake_probability, 1.0 - fake_probability)
    if settings.detection_profile.strip().lower() == 'review':
        real_cutoff, fake_cutoff = _review_thresholds(kind)
        if fake_probability < real_cutoff:
            return 'REAL', 1.0 - fake_probability
        if fake_probability >= fake_cutoff:
            return 'FAKE', fake_probability
        return 'UNCERTAIN', confidence

    decision_threshold = settings.default_image_threshold if threshold is None else threshold
    if fake_probability >= decision_threshold:
        return 'FAKE', fake_probability
    return 'REAL', 1.0 - fake_probability


def combine_weighted_scores(scores: list[tuple[float, float]], threshold: float | None = None) -> tuple[float, str, float]:
    if not scores:
        return 0.5, 'UNCERTAIN', 0.5

    total_weight = sum(weight for _, weight in scores)
    weighted_mean = sum(prob * weight for prob, weight in scores) / max(total_weight, 1e-6)
    max_fake_signal = max(prob for prob, _ in scores)
    fake_probability = (0.6 * weighted_mean) + (0.4 * max_fake_signal)
    spread = max(prob for prob, _ in scores) - min(prob for prob, _ in scores)
    if settings.detection_profile.strip().lower() == 'review':
        verdict, confidence = classify_probability(fake_probability, 'image', threshold)
        return fake_probability, verdict, confidence
    if spread > settings.disagreement_threshold:
        return fake_probability, 'UNCERTAIN', max(fake_probability, 1.0 - fake_probability)
    verdict, confidence = classify_probability(fake_probability, 'image', threshold)
    return fake_probability, verdict, confidence


def aggregate_video_scores(frame_scores: list[float]) -> tuple[float, str, float]:
    if not frame_scores:
        return 0.5, 'UNCERTAIN', 0.5
    fake_probability = (0.7 * mean(frame_scores)) + (0.3 * max(frame_scores))
    spread = max(frame_scores) - min(frame_scores)
    if settings.detection_profile.strip().lower() == 'review':
        verdict, confidence = classify_probability(fake_probability, 'video')
        return fake_probability, verdict, confidence
    if spread > settings.disagreement_threshold:
        return fake_probability, 'UNCERTAIN', max(fake_probability, 1.0 - fake_probability)
    verdict, confidence = classify_probability(fake_probability, 'video')
    return fake_probability, verdict, confidence
