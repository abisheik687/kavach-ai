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
    app_name: str = "KAVACH-AI"
    app_version: str = "2.0.0"
    environment: str = "development"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"

    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:4173",
            "http://127.0.0.1:4173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
    )

    model_cache_dir: Path = Path(tempfile.gettempdir()) / "kavach-ai" / "models"
    temp_dir: Path = Path(tempfile.gettempdir()) / "kavach-ai" / "uploads"

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
    demo_safe_results: bool = True

    allow_fallback_models: bool = False
    enable_remote_model_downloads: bool = False
    hf_inference_mode: str = "local_only"
    hf_weekly_budget_usd: float = 0.0
    block_hf_credit_usage: bool = True
    hf_token: str | None = None
    hf_deep_analysis_enabled: bool = False
    hf_budget_limit_usd: float = 25.0
    hf_cost_per_deep_scan_usd: float = 0.20
    hf_deep_mode: str = "endpoint"
    hf_endpoint_name: str | None = None
    hf_endpoint_namespace: str | None = None
    hf_endpoint_url: str | None = None
    hf_auto_scale_to_zero: bool = True
    hf_deep_cache_ttl_seconds: int = 48 * 60 * 60

    detection_profile: str = "review"
    default_image_threshold: float = 0.35
    default_audio_threshold: float = 0.52
    disagreement_threshold: float = 0.4
    tta_enabled: bool = False

    model_vit_repo: str = "prithivMLmods/Deep-Fake-Detector-Model"
    model_efficientnet_repo: str = "Wvolf/EfficientNet_Deepfake"
    model_xception_repo: str = "not-lain/xception-deepfake"
    model_convnext_repo: str = "facebook/convnext-base-224"
    model_vit_label_order: str = "fake_first"
    model_efficientnet_label_order: str = "real_first"
    model_xception_label_order: str = "real_first"
    model_convnext_label_order: str = "real_first"
    model_label_order_check_image: str | None = None
    model_audio_repo: str = "mo-thecreator/deepfake-audio-detector"
    model_video_repo: str = "muneeb1812/videomae-base-fake-video-classification"
    model_video_local_path: str | None = None
    local_image_calibrator_path: str | None = "../models/local_image_calibrator.json"

    model_image_artifact_manifest: str | None = None
    model_audio_artifact_manifest: str | None = None
    model_video_artifact_manifest: str | None = None

    ffmpeg_binary: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
settings.model_cache_dir.mkdir(parents=True, exist_ok=True)
settings.temp_dir.mkdir(parents=True, exist_ok=True)
