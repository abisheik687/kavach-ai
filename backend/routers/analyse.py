"""
Internal trace:
- Wrong before: this router only imported correctly from the backend directory, so repo-root uvicorn launches failed before the API mounted.
- Fixed now: the upload route works in both execution modes while keeping the same validation and cleanup behavior.
"""

from __future__ import annotations

import time

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile

try:
    from ..config import settings
    from ..models.loader import get_model_registry
    from ..pipelines.audio_pipeline import analyse_audio_file
    from ..pipelines.image_pipeline import analyse_image_file
    from ..pipelines.video_pipeline import analyse_video_file
    from ..schemas.request import UploadValidationInfo, validate_upload
    from ..schemas.response import AnalysisResult, AudioResult
    from ..utils.file_utils import AppError, cleanup_path, persist_upload_to_temp
    from ..utils.runtime import run_analysis
except ImportError:
    from config import settings
    from models.loader import get_model_registry
    from pipelines.audio_pipeline import analyse_audio_file
    from pipelines.image_pipeline import analyse_image_file
    from pipelines.video_pipeline import analyse_video_file
    from schemas.request import UploadValidationInfo, validate_upload
    from schemas.response import AnalysisResult, AudioResult
    from utils.file_utils import AppError, cleanup_path, persist_upload_to_temp
    from utils.runtime import run_analysis


router = APIRouter(tags=['analysis'])
SAFE_RESULT_CODES = {'ANALYSIS_TIMEOUT', 'ANALYSIS_STAGE_FAILED', 'VIDEO_ANALYSIS_FAILED'}


def _standardize_result(result: AnalysisResult, processing_time_ms: int, model_versions: dict[str, str]) -> AnalysisResult:
    verdict = result.verdict or 'UNCERTAIN'
    result.type = result.file_type or result.type
    result.prediction = verdict.lower()
    result.confidence = round((result.overall_confidence or 0.0) * 100.0, 2)
    result.processing_time_ms = processing_time_ms
    result.processing_time = f'{processing_time_ms} ms'
    result.model_versions = model_versions
    return result


def _safe_fallback_result(file_type: str, stage: str, code: str, model_versions: dict[str, str]) -> AnalysisResult:
    warning = f'{stage} failed or timed out; returned safe fallback result'
    result = AnalysisResult(
        type=file_type,
        prediction='uncertain',
        confidence=50.0,
        processing_time='0 ms',
        file_type=file_type,
        verdict='UNCERTAIN',
        overall_confidence=0.5,
        fake_probability=0.5,
        warnings=[warning, f'Diagnostic code: {code}'],
        model_versions=model_versions,
    )
    if file_type == 'audio':
        result.audio_result = AudioResult(
            verdict='UNCERTAIN',
            fake_probability=0.5,
            waveform=[],
            mode='safe-fallback',
            model='safe-fallback',
        )
    return result


async def _run_demo_safe(coro, *, timeout_seconds: int, stage: str, validation: UploadValidationInfo, model_versions: dict[str, str]) -> AnalysisResult:
    try:
        return await run_analysis(coro, timeout_seconds=timeout_seconds, stage=stage)
    except AppError as exc:
        if settings.demo_safe_results and exc.code in SAFE_RESULT_CODES:
            return _safe_fallback_result(validation.file_type, stage, exc.code, model_versions)
        raise


@router.post('/analyse', response_model=AnalysisResult)
async def analyse(
    background_tasks: BackgroundTasks,
    validation: UploadValidationInfo = Depends(validate_upload),
    file: UploadFile = File(...),
) -> AnalysisResult:
    started_at = time.perf_counter()
    temp_path = await persist_upload_to_temp(file, validation)
    background_tasks.add_task(cleanup_path, temp_path)

    registry = get_model_registry()

    if validation.file_type == 'image':
        result = await _run_demo_safe(
            analyse_image_file(temp_path, registry, validation),
            timeout_seconds=settings.image_timeout_seconds,
            stage='Image analysis',
            validation=validation,
            model_versions=registry.model_versions,
        )
    elif validation.file_type == 'video':
        result = await _run_demo_safe(
            analyse_video_file(temp_path, registry, validation, background_tasks),
            timeout_seconds=settings.video_timeout_seconds,
            stage='Video analysis',
            validation=validation,
            model_versions=registry.model_versions,
        )
    else:
        result = await _run_demo_safe(
            analyse_audio_file(temp_path, registry, validation),
            timeout_seconds=settings.audio_timeout_seconds,
            stage='Audio analysis',
            validation=validation,
            model_versions=registry.model_versions,
        )

    processing_time_ms = int((time.perf_counter() - started_at) * 1000)
    return _standardize_result(result, processing_time_ms, registry.model_versions)
