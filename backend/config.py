"""
KAVACH-AI backend configuration.
All settings are read from environment variables (or .env file).
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = 'KAVACH-AI'
    app_version: str = '2.0.0'
    environment: str = 'development'
    host: str = '0.0.0.0'
    port: int = 8000
    log_level: str = 'INFO'

    cors_origins: list[str] = Field(
        default_factory=lambda: [
            'http://localhost:5173',
            'http://127.0.0.1:5173',
            'http://localhost:4173',
            'http://127.0.0.1:4173',
        ]
    )

    model_cache_dir: Path = Path(tempfile.gettempdir()) / 'kavach-ai' / 'models'
    temp_dir: Path = Path(tempfile.gettempdir()) / 'kavach-ai' / 'uploads'
    upload_chunk_size_bytes: int = 1024 * 1024
    max_image_audio_bytes: int = 20 * 1024 * 1024
    max_video_bytes: int = 100 * 1024 * 1024
    max_image_pixels: int = 1280 * 1280
    max_video_frames: int = 30
    max_video_previews: int = 6
    video_frame_stride: int = 10
    max_video_seconds: int = 45
    max_audio_seconds: int = 30
    analysis_timeout_seconds: int = 120
    image_timeout_seconds: int = 30
    audio_timeout_seconds: int = 45
    video_timeout_seconds: int = 120
    max_concurrent_analyses: int = 2

    # ── Fallback control ──────────────────────────────────────────────────────
    # When False (default), backend ONLY uses trained artifacts. Startup fails
    # if a manifest env-var is set but the file is missing or invalid.
    # Set to True during development if you want heuristic fallbacks.
    allow_fallback_models: bool = False
    enable_remote_model_downloads: bool = False

    # ── Detection thresholds ──────────────────────────────────────────────────
    default_image_threshold: float = 0.52
    default_audio_threshold: float = 0.52
    disagreement_threshold: float = 0.4

    # ── HuggingFace model repos (used only when remote downloads are enabled) ─
    model_vit_repo: str = 'prithivMLmods/Deep-Fake-Detector-Model'
    model_efficientnet_repo: str = 'Wvolf/EfficientNet_Deepfake'
    model_xception_repo: str = 'not-lain/xception-deepfake'
    model_convnext_repo: str = 'facebook/convnext-base-224'
    model_audio_repo: str = 'mo-thecreator/deepfake-audio-detector'
    model_video_repo: str = 'muneeb1812/videomae-base-fake-video-classification'
    model_video_local_path: str | None = None

    # ── Trained artifact manifests (set these after running training/train_all.py) ─
    model_image_artifact_manifest: str | None = None
    model_audio_artifact_manifest: str | None = None
    model_video_artifact_manifest: str | None = None

    ffmpeg_binary: str | None = None

    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')


settings = Settings()
settings.model_cache_dir.mkdir(parents=True, exist_ok=True)
settings.temp_dir.mkdir(parents=True, exist_ok=True)
