"""
Internal trace:
- Wrong before: package-mode launches broke on absolute imports, so the video pipeline could not even be imported from repo root.
- Fixed now: video analysis supports both execution modes and keeps the bounded decode + isolated audio extraction behavior.
"""

from __future__ import annotations

import subprocess
import tempfile
from collections import defaultdict
from pathlib import Path

import cv2
import librosa
import numpy as np
import soundfile as sf

try:
    from ..config import settings
    from ..models.ensemble import aggregate_video_scores
    from ..models.loader import ModelRegistry
    from ..schemas.response import AnalysisResult, AudioResult, ModelScore, VideoFramePreview
    from ..utils.file_utils import AppError, clamp, cleanup_path, find_ffmpeg_binary, image_to_base64
    from ..utils.runtime import run_inference
    from .audio_pipeline import _build_waveform
except ImportError:
    from config import settings
    from models.ensemble import aggregate_video_scores
    from models.loader import ModelRegistry
    from pipelines.audio_pipeline import _build_waveform
    from schemas.response import AnalysisResult, AudioResult, ModelScore, VideoFramePreview
    from utils.file_utils import AppError, clamp, cleanup_path, find_ffmpeg_binary, image_to_base64
    from utils.runtime import run_inference


def _compute_frame_indices(frame_count: int, fps: float) -> list[int]:
    if frame_count <= 0:
        return []

    max_frame_window = frame_count
    if fps > 0:
        max_frame_window = min(frame_count, int(fps * settings.max_video_seconds))

    stride = max(settings.video_frame_stride, max(max_frame_window // max(settings.max_video_frames, 1), 1))
    indices = list(range(0, max_frame_window, stride))
    return indices[: settings.max_video_frames]


def _extract_frames(video_path: Path) -> list[tuple[int, object]]:
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise ValueError('Video could not be opened')

    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
    target_indices = _compute_frame_indices(frame_count, fps)
    frames: list[tuple[int, object]] = []

    try:
        if target_indices:
            for index in target_indices:
                capture.set(cv2.CAP_PROP_POS_FRAMES, index)
                ok, frame = capture.read()
                if ok and frame is not None:
                    frames.append((index, frame))
        else:
            max_frames = settings.max_video_frames
            max_index = int(fps * settings.max_video_seconds) if fps > 0 else settings.max_video_frames * settings.video_frame_stride
            index = 0
            while len(frames) < max_frames and index <= max_index:
                ok, frame = capture.read()
                if not ok:
                    break
                if index % settings.video_frame_stride == 0:
                    frames.append((index, frame))
                index += 1
    finally:
        capture.release()

    if not frames:
        raise ValueError('Video did not yield readable frames')
    return frames


def _analyse_frame(frame, registry: ModelRegistry) -> tuple[float, list[ModelScore]]:
    from PIL import Image

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    height, width = rgb.shape[:2]
    max_side = max(height, width)
    if max_side > 720:
        scale = 720.0 / max_side
        rgb = cv2.resize(rgb, (max(int(width * scale), 1), max(int(height * scale), 1)))

    pil_image = Image.fromarray(rgb)
    weighted_scores: list[tuple[float, float]] = []
    model_scores: list[ModelScore] = []

    for loaded in registry.image_models:
        fake_probability = clamp(float(loaded.infer(pil_image)))
        weighted_scores.append((fake_probability, loaded.slot.weight))
        model_scores.append(
            ModelScore(
                model=loaded.slot.label,
                fake_prob=round(fake_probability, 4),
                weight=loaded.slot.weight,
                mode=loaded.mode,
            )
        )

    total_weight = sum(weight for _, weight in weighted_scores)
    frame_probability = sum(prob * weight for prob, weight in weighted_scores) / max(total_weight, 1e-6)
    return clamp(frame_probability), model_scores


def _extract_audio_track(video_path: Path, target_dir: Path) -> Path | None:
    ffmpeg_binary = find_ffmpeg_binary()
    if not ffmpeg_binary:
        return None

    audio_path = target_dir / 'video_audio.wav'
    command = [
        ffmpeg_binary,
        '-y',
        '-i',
        str(video_path),
        '-vn',
        '-t',
        str(settings.max_audio_seconds),
        '-acodec',
        'pcm_s16le',
        '-ar',
        '16000',
        '-ac',
        '1',
        str(audio_path),
    ]
    completed = subprocess.run(command, capture_output=True, check=False, timeout=settings.audio_timeout_seconds)
    if completed.returncode != 0 or not audio_path.exists():
        return None
    return audio_path


def _load_audio_clip(audio_path: Path) -> tuple[object, int]:
    if audio_path.suffix.lower() == '.wav':
        audio, sample_rate = sf.read(str(audio_path), always_2d=False)
        if isinstance(audio, np.ndarray) and audio.ndim > 1:
            audio = audio.mean(axis=1)
        audio = np.asarray(audio, dtype=np.float32)
        audio = audio[: settings.max_audio_seconds * sample_rate]
    else:
        audio, sample_rate = librosa.load(
            str(audio_path),
            sr=16000,
            mono=True,
            duration=settings.max_audio_seconds,
        )
    return audio, sample_rate


def _average_model_scores(model_scores_per_frame: list[list[ModelScore]]) -> list[ModelScore]:
    if not model_scores_per_frame:
        return []

    totals: dict[str, dict[str, float | str]] = defaultdict(lambda: {'sum': 0.0, 'weight': 0.0, 'mode': 'fallback'})
    counts: dict[str, int] = defaultdict(int)

    for frame_scores in model_scores_per_frame:
        for score in frame_scores:
            totals[score.model]['sum'] += score.fake_prob
            totals[score.model]['weight'] = score.weight
            totals[score.model]['mode'] = score.mode
            counts[score.model] += 1

    averaged: list[ModelScore] = []
    for score in model_scores_per_frame[0]:
        total = totals[score.model]
        averaged.append(
            ModelScore(
                model=score.model,
                fake_prob=round(float(total['sum']) / max(counts[score.model], 1), 4),
                weight=float(total['weight']),
                mode=str(total['mode']),
            )
        )
    return averaged


async def analyse_video_file(file_path: Path, registry: ModelRegistry, validation, background_tasks) -> AnalysisResult:
    try:
        frames = await run_inference(
            _extract_frames,
            file_path,
            timeout_seconds=settings.video_timeout_seconds,
            stage='Video decoding',
        )
    except AppError:
        raise
    except Exception as exc:
        raise AppError(422, 'Video could not be decoded. Upload a valid MP4 or WEBM file.', 'INVALID_VIDEO_FILE') from exc

    warnings = list(dict.fromkeys(registry.warnings))
    frame_scores: list[float] = []
    previews: list[VideoFramePreview] = []
    model_scores_per_frame: list[list[ModelScore]] = []
    preview_interval = max(len(frames) // max(settings.max_video_previews, 1), 1)

    for position, (index, frame) in enumerate(frames):
        try:
            frame_probability, model_scores = await run_inference(
                _analyse_frame,
                frame,
                registry,
                timeout_seconds=settings.image_timeout_seconds,
                stage=f'Video frame {index} inference',
            )
        except AppError:
            warnings.append(f'Frame {index} inference failed and was skipped')
            continue

        frame_scores.append(round(frame_probability, 4))
        model_scores_per_frame.append(model_scores)
        if position % preview_interval == 0 and len(previews) < settings.max_video_previews:
            previews.append(
                VideoFramePreview(
                    index=index,
                    fake_probability=round(frame_probability, 4),
                    image_base64=image_to_base64(cv2.resize(frame, (256, 144))),
                )
            )

    if not frame_scores:
        raise AppError(422, 'Video frames could not be analysed reliably.', 'VIDEO_ANALYSIS_FAILED')

    fake_probability, verdict, confidence = aggregate_video_scores(frame_scores)
    averaged_model_scores = _average_model_scores(model_scores_per_frame)
    temporal_probability = None

    if registry.video_model:
        try:
            temporal_probability = await run_inference(
                registry.video_model.infer,
                str(file_path),
                timeout_seconds=settings.video_timeout_seconds,
                stage='Video temporal inference',
            )
            temporal_probability = clamp(temporal_probability)
            fake_probability = clamp((0.6 * fake_probability) + (0.4 * temporal_probability))
            confidence = max(fake_probability, 1.0 - fake_probability)
            verdict = 'FAKE' if fake_probability > settings.default_image_threshold else 'REAL'
            averaged_model_scores.append(
                ModelScore(
                    model='VideoMAE Temporal',
                    fake_prob=round(temporal_probability, 4),
                    weight=0.4,
                    mode=registry.video_model.mode,
                )
            )
        except AppError:
            warnings.append('Video temporal model failed; using frame-level evidence only')

    audio_result = None
    temp_audio_dir = Path(tempfile.mkdtemp(prefix='kavach_video_audio_', dir=file_path.parent))
    background_tasks.add_task(cleanup_path, temp_audio_dir)

    try:
        audio_path = await run_inference(
            _extract_audio_track,
            file_path,
            temp_audio_dir,
            timeout_seconds=settings.audio_timeout_seconds,
            stage='Video audio extraction',
        )
    except AppError:
        audio_path = None
        warnings.append('Video audio extraction timed out and was skipped')

    if audio_path:
        try:
            audio, sample_rate = await run_inference(
                _load_audio_clip,
                audio_path,
                timeout_seconds=settings.audio_timeout_seconds,
                stage='Video audio decoding',
            )
            handle = registry.audio_model
            audio_probability = 0.5
            audio_mode = 'missing'
            if handle:
                try:
                    audio_probability = await run_inference(
                        handle.infer,
                        audio,
                        sample_rate,
                        timeout_seconds=settings.audio_timeout_seconds,
                        stage='Video audio inference',
                    )
                    audio_mode = handle.mode
                except AppError:
                    warnings.append('Video audio inference failed; using neutral fallback score')
            audio_probability = clamp(audio_probability)
            audio_verdict = 'FAKE' if audio_probability > settings.default_audio_threshold else 'REAL'
            audio_result = AudioResult(
                verdict=audio_verdict,
                fake_probability=round(audio_probability, 4),
                waveform=_build_waveform(audio),
                mode=audio_mode,
            )
        except AppError:
            warnings.append('Video audio track could not be analysed reliably')
    else:
        warnings.append('Video audio track could not be extracted in the current environment')

    return AnalysisResult(
        type=validation.file_type,
        prediction=verdict.lower(),
        confidence=round(confidence * 100.0, 2),
        processing_time='0 ms',
        file_type=validation.file_type,
        verdict=verdict,
        overall_confidence=round(confidence, 4),
        fake_probability=round(fake_probability, 4),
        model_scores=averaged_model_scores,
        video_frame_scores=frame_scores,
        video_frame_previews=previews,
        audio_result=audio_result,
        warnings=list(dict.fromkeys(warnings)),
    )
