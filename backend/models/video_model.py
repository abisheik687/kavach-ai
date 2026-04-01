"""
Internal trace:
- Wrong before: the temporal video adapter only imported from one cwd layout, which broke package-mode launches even before fallback aggregation could run.
- Fixed now: the adapter supports both execution modes while preserving the same primary/fallback behavior.

Open-source temporal video detector adapter.

Primary path:
- Hugging Face video-classification model (VideoMAE-compatible) loaded from a cached local path
  or from the public model hub when remote downloads are enabled.

Fallback path:
- None. The video pipeline keeps running with frame-level spatial analysis plus temporal score
  aggregation even when a temporal model is unavailable.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

try:
    from ..config import settings
    from ..utils.file_utils import clamp
except ImportError:
    from config import settings
    from utils.file_utils import clamp


@dataclass
class VideoModelHandle:
    infer: Callable[[str], float]
    mode: str
    model_name: str


def _label_to_fake_probability(label: str, score: float) -> float:
    normalized = label.lower()
    if any(token in normalized for token in ('real', 'authentic', 'bonafide')):
        return clamp(1.0 - score)
    if any(token in normalized for token in ('fake', 'deepfake', 'spoof', 'manipulated')):
        return clamp(score)
    return 0.5


def build_video_model() -> VideoModelHandle | None:
    from transformers import pipeline

    model_ref = settings.model_video_local_path or settings.model_video_repo
    classifier = pipeline(
        task='video-classification',
        model=model_ref,
        device=-1,
    )

    def infer(video_path: str) -> float:
        outputs = classifier(video_path, top_k=2)
        if not outputs:
            return 0.5
        scores = [_label_to_fake_probability(item.get('label', ''), float(item.get('score', 0.0))) for item in outputs]
        return clamp(max(scores, key=lambda item: abs(item - 0.5)))

    model_name = Path(model_ref).name if Path(str(model_ref)).exists() else str(model_ref)
    return VideoModelHandle(infer=infer, mode='primary', model_name=model_name)
