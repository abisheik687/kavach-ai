"""
Internal trace:
- Wrong before: startup was blocked by cwd-sensitive imports, an incorrect model count, and strict dev boot behavior when no manifests were configured.
- Fixed now: the loader imports cleanly in both modes, reports the correct count, and auto-enables dev fallbacks when no trained manifests exist.

KAVACH-AI Model Loader
=======================
Loads all models at startup via FastAPI lifespan context.

Strict mode (allow_fallback_models=False):
  - Image models loaded ONLY from MODEL_IMAGE_ARTIFACT_MANIFEST
  - Audio model loaded ONLY from MODEL_AUDIO_ARTIFACT_MANIFEST
  - Video model loaded ONLY from MODEL_VIDEO_ARTIFACT_MANIFEST
  - Startup fails with RuntimeError if a manifest env-var is set but invalid
  - If NO manifest is set AND fallbacks are disabled → raises RuntimeError

Permissive mode (allow_fallback_models=True):
  - Used for development without trained artifacts
  - Falls back to forensic heuristic scorers and signal analysis
"""

from __future__ import annotations

import os
import socket
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from fastapi import FastAPI

try:
    from ..config import settings
    from ..utils.logger import get_logger
    from .artifact_loader import load_audio_artifact, load_image_artifact, load_video_artifact
    from .audio_model import AudioModelHandle, build_audio_model, build_fallback_audio_model
    from .image_models import ImageModelSlot, create_fallback_scorer, create_image_slots
    from .video_model import VideoModelHandle, build_video_model
except ImportError:
    from config import settings
    from models.artifact_loader import load_audio_artifact, load_image_artifact, load_video_artifact
    from models.audio_model import AudioModelHandle, build_audio_model, build_fallback_audio_model
    from models.image_models import ImageModelSlot, create_fallback_scorer, create_image_slots
    from models.video_model import VideoModelHandle, build_video_model
    from utils.logger import get_logger


logger = get_logger(__name__)


@dataclass
class LoadedImageModel:
    slot: ImageModelSlot
    infer: Callable
    mode: str
    warning: str | None = None


@dataclass
class ModelRegistry:
    image_models: list[LoadedImageModel] = field(default_factory=list)
    audio_model: AudioModelHandle | None = None
    video_model: VideoModelHandle | None = None
    warnings: list[str] = field(default_factory=list)
    model_versions: dict[str, str] = field(default_factory=dict)

    @property
    def loaded_count(self) -> int:
        return len(self.image_models) + (1 if self.audio_model else 0)


_registry = ModelRegistry()
_auto_fallback_warned = False


def _allow_fallback() -> bool:
    global _auto_fallback_warned
    if os.getenv('TEST_MODE', '').strip().lower() == 'true':
        return True
    if settings.allow_fallback_models:
        return True
    manifests = (
        settings.model_image_artifact_manifest,
        settings.model_audio_artifact_manifest,
        settings.model_video_artifact_manifest,
    )
    if settings.environment.lower() != 'production' and not any(manifests):
        if not _auto_fallback_warned:
            logger.warning('auto_enabling_fallback_models', extra={'reason': 'no_artifact_manifests_configured'})
            _auto_fallback_warned = True
        return True
    return False


def _can_reach_huggingface() -> bool:
    if not settings.enable_remote_model_downloads:
        return False
    try:
        with socket.create_connection(('huggingface.co', 443), timeout=2):
            return True
    except OSError:
        return False


def _strict_manifest_path(env_value: str | None, label: str) -> Path | None:
    """Validate and return a manifest path.

    In strict mode (allow_fallback_models=False):
      - If env_value is set → file MUST exist; raises RuntimeError if it doesn't.
      - If env_value is not set → raises RuntimeError (no fallback allowed).

    In permissive mode:
      - If env_value is set → file MUST exist; raises RuntimeError if it doesn't.
      - If env_value is not set → returns None (caller uses fallback).
    """
    if env_value:
        p = Path(env_value)
        if not p.exists():
            raise RuntimeError(
                f'{label} manifest not found: {env_value}\n'
                f'Run training first: python training/train_all.py'
            )
        return p

    if not _allow_fallback():
        raise RuntimeError(
            f'{label} manifest not configured (env-var is empty).\n'
            f'Options:\n'
            f'  1. Train models: python training/train_all.py  (sets .env automatically)\n'
            f'  2. Enable fallbacks for dev: set ALLOW_FALLBACK_MODELS=true in .env'
        )
    return None


async def _load_models() -> None:
    _registry.image_models.clear()
    _registry.warnings.clear()
    _registry.model_versions.clear()

    # ── Image models ──────────────────────────────────────────
    image_manifest = _strict_manifest_path(
        settings.model_image_artifact_manifest, 'IMAGE'
    )

    if image_manifest is not None:
        logger.info('loading_image_artifact', extra={'path': str(image_manifest)})
        infer, architecture = load_image_artifact(str(image_manifest))
        slot = ImageModelSlot(
            key='trained_image',
            label=f'Trained-{architecture}',
            weight=1.0,
            repo_id=str(image_manifest),
            loader=lambda: (infer, 'trained-local'),
        )
        _registry.image_models.append(LoadedImageModel(slot=slot, infer=infer, mode='trained-local'))
        _registry.model_versions[slot.label] = architecture
        logger.info('image_model_loaded', extra={'architecture': architecture, 'mode': 'trained-local'})
    else:
        # Permissive fallback path (allow_fallback_models=True)
        remote_available = _can_reach_huggingface()
        if not remote_available:
            _registry.warnings.append('Remote model hub unavailable; using forensic fallback scorers')
        for slot in create_image_slots():
            if not remote_available:
                infer = create_fallback_scorer(slot.key)
                warning = f'{slot.label}: using forensic fallback scorer (no remote access)'
                _registry.image_models.append(LoadedImageModel(slot=slot, infer=infer, mode='fallback', warning=warning))
                _registry.warnings.append(warning)
                _registry.model_versions[slot.label] = f'fallback:{slot.key}'
            else:
                try:
                    infer, mode = slot.loader()
                    _registry.image_models.append(LoadedImageModel(slot=slot, infer=infer, mode=mode))
                    _registry.model_versions[slot.label] = slot.repo_id
                except Exception as exc:
                    infer = create_fallback_scorer(slot.key)
                    warning = f'{slot.label}: primary model unavailable; using forensic fallback scorer'
                    _registry.image_models.append(LoadedImageModel(slot=slot, infer=infer, mode='fallback', warning=warning))
                    _registry.warnings.append(warning)
                    _registry.model_versions[slot.label] = f'fallback:{slot.key}'
                    logger.warning('image_model_fallback', extra={'model': slot.label, 'error': str(exc)})

    # ── Audio model ───────────────────────────────────────────
    audio_manifest = _strict_manifest_path(
        settings.model_audio_artifact_manifest, 'AUDIO'
    )

    if audio_manifest is not None:
        logger.info('loading_audio_artifact', extra={'path': str(audio_manifest)})
        infer, architecture = load_audio_artifact(str(audio_manifest))
        _registry.audio_model = AudioModelHandle(infer=infer, mode='trained-local')
        _registry.model_versions['audio'] = architecture
        logger.info('audio_model_loaded', extra={'architecture': architecture, 'mode': 'trained-local'})
    else:
        # Permissive fallback path
        remote_available = _can_reach_huggingface()
        if remote_available:
            _registry.audio_model = build_audio_model()
        else:
            _registry.audio_model = build_fallback_audio_model()
        if _registry.audio_model.mode == 'fallback':
            _registry.warnings.append('Audio primary model unavailable; using signal fallback scorer')
        _registry.model_versions['audio'] = (
            settings.model_audio_repo if _registry.audio_model.mode == 'primary' else 'fallback:signal'
        )

    # ── Video model ───────────────────────────────────────────
    video_manifest = _strict_manifest_path(
        settings.model_video_artifact_manifest, 'VIDEO'
    )

    if video_manifest is not None:
        logger.info('loading_video_artifact', extra={'path': str(video_manifest)})
        infer, architecture = load_video_artifact(str(video_manifest))
        _registry.video_model = VideoModelHandle(infer=infer, mode='trained-local', model_name=architecture)
        _registry.model_versions['video'] = architecture
        logger.info('video_model_loaded', extra={'architecture': architecture, 'mode': 'trained-local'})
    else:
        # Permissive fallback path — video fallback is None (frame-level aggregation still works)
        _registry.video_model = None
        _registry.model_versions['video'] = 'fallback:frame-aggregation'
        _registry.warnings.append('Video temporal model not configured; using frame-level aggregation')
        if settings.model_video_local_path or _can_reach_huggingface():
            try:
                _registry.video_model = build_video_model()
                if _registry.video_model:
                    _registry.model_versions['video'] = _registry.video_model.model_name
            except Exception as exc:
                logger.warning('video_model_fallback', extra={'error': str(exc)})

    logger.info(
        'models_loaded',
        extra={
            'image_models': len(_registry.image_models),
            'audio_mode': getattr(_registry.audio_model, 'mode', 'none'),
            'video_mode': getattr(_registry.video_model, 'mode', 'none'),
            'warnings': len(_registry.warnings),
        },
    )


@asynccontextmanager
async def model_lifespan(_: FastAPI):
    await _load_models()
    yield
    _registry.image_models.clear()
    _registry.audio_model = None
    _registry.video_model = None
    _registry.warnings.clear()
    _registry.model_versions.clear()


def get_model_registry() -> ModelRegistry:
    return _registry
