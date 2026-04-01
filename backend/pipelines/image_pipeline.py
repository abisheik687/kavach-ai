"""
Internal trace:
- Wrong before: this pipeline only imported under one cwd layout, so repo-root app launches failed before requests could reach it.
- Fixed now: image analysis supports both package and backend-local execution without changing the response contract.
"""

from __future__ import annotations

from pathlib import Path

try:
    from ..config import settings
    from ..models.ensemble import combine_weighted_scores
    from ..models.loader import ModelRegistry
    from ..models.image_models import prepare_image
    from ..schemas.response import AnalysisResult, ModelScore
    from ..utils.file_utils import AppError, clamp
    from ..utils.runtime import run_inference
except ImportError:
    from config import settings
    from models.ensemble import combine_weighted_scores
    from models.loader import ModelRegistry
    from models.image_models import prepare_image
    from schemas.response import AnalysisResult, ModelScore
    from utils.file_utils import AppError, clamp
    from utils.runtime import run_inference


async def analyse_image_file(file_path: Path, registry: ModelRegistry, validation) -> AnalysisResult:
    try:
        image_bytes = await run_inference(
            file_path.read_bytes,
            timeout_seconds=settings.image_timeout_seconds,
            stage='Image read',
        )
        prepared_image = await run_inference(
            prepare_image,
            image_bytes,
            timeout_seconds=settings.image_timeout_seconds,
            stage='Image preprocessing',
        )
    except AppError:
        raise
    except Exception as exc:
        raise AppError(422, 'Image could not be decoded. Upload a valid JPEG, PNG, or WEBP file.', 'INVALID_IMAGE_FILE') from exc

    model_scores: list[ModelScore] = []
    warnings = list(registry.warnings)
    weighted_scores: list[tuple[float, float]] = []

    for loaded in registry.image_models:
        try:
            fake_probability = await run_inference(
                loaded.infer,
                prepared_image,
                timeout_seconds=settings.image_timeout_seconds,
                stage=f'{loaded.slot.label} image inference',
            )
        except AppError:
            fake_probability = 0.5
            warning = f'{loaded.slot.label} inference failed; using neutral score for this request'
            if warning not in warnings:
                warnings.append(warning)
        fake_probability = clamp(fake_probability)
        weighted_scores.append((fake_probability, loaded.slot.weight))
        model_scores.append(
            ModelScore(
                model=loaded.slot.label,
                fake_prob=round(fake_probability, 4),
                weight=loaded.slot.weight,
                mode=loaded.mode,
            )
        )
        if loaded.warning and loaded.warning not in warnings:
            warnings.append(loaded.warning)

    fake_probability, verdict, confidence = combine_weighted_scores(weighted_scores)
    return AnalysisResult(
        type=validation.file_type,
        prediction=verdict.lower(),
        confidence=round(confidence * 100.0, 2),
        processing_time='0 ms',
        file_type=validation.file_type,
        verdict=verdict,
        overall_confidence=round(confidence, 4),
        fake_probability=round(fake_probability, 4),
        model_scores=model_scores,
        warnings=warnings,
    )
