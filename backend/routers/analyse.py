"""
Internal trace:
- Wrong before: uploads were split across multiple endpoints with inconsistent validation, mixed JSON/file inputs, and live-analysis paths that hid cleanup failures.
- Fixed now: one multipart upload endpoint validates files, writes temporary media safely, runs the correct pipeline, and always returns the documented JSON/error shape.
"""

from __future__ import annotations

import time

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile

from config import settings
from models.loader import get_model_registry
from pipelines.audio_pipeline import analyse_audio_file
from pipelines.image_pipeline import analyse_image_file
from pipelines.video_pipeline import analyse_video_file
from schemas.request import UploadValidationInfo, validate_upload
from schemas.response import AnalysisResult
from utils.file_utils import cleanup_path, persist_upload_to_temp
from utils.runtime import run_analysis


router = APIRouter(tags=['analysis'])


def _standardize_result(result: AnalysisResult, processing_time_ms: int, model_versions: dict[str, str]) -> AnalysisResult:
    verdict = result.verdict or 'UNCERTAIN'
    result.type = result.file_type or result.type
    result.prediction = verdict.lower()
    result.confidence = round((result.overall_confidence or 0.0) * 100.0, 2)
    result.processing_time_ms = processing_time_ms
    result.processing_time = f'{processing_time_ms} ms'
    result.model_versions = model_versions
    return result


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
        result = await run_analysis(
            analyse_image_file(temp_path, registry, validation),
            timeout_seconds=settings.image_timeout_seconds,
            stage='Image analysis',
        )
    elif validation.file_type == 'video':
        result = await run_analysis(
            analyse_video_file(temp_path, registry, validation, background_tasks),
            timeout_seconds=settings.video_timeout_seconds,
            stage='Video analysis',
        )
    else:
        result = await run_analysis(
            analyse_audio_file(temp_path, registry, validation),
            timeout_seconds=settings.audio_timeout_seconds,
            stage='Audio analysis',
        )

    processing_time_ms = int((time.perf_counter() - started_at) * 1000)
    return _standardize_result(result, processing_time_ms, registry.model_versions)
