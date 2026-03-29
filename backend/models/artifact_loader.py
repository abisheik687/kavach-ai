"""
KAVACH-AI Artifact Loader
==========================
Loads trained model artifacts (model.pt / model.onnx) produced by
training/train_all.py and returns callable inference functions.

Inference priority:
  1. ONNX (onnxruntime) — if model.onnx exists next to model.pt (2-5× faster)
  2. PyTorch — fallback when ONNX file is absent
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Callable

import librosa
import numpy as np
import torch
from PIL import Image
from torchvision import transforms

from utils.file_utils import clamp

logger = logging.getLogger(__name__)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _load_metadata(manifest_path: str) -> dict:
    return json.loads(Path(manifest_path).read_text(encoding='utf-8'))


def _softmax_np(logits: np.ndarray) -> np.ndarray:
    shifted = logits - logits.max()
    exp = np.exp(shifted)
    return exp / exp.sum()


def _onnx_session(onnx_path: Path):
    """Create an ONNXRuntime session with CUDA if available, else CPU."""
    import onnxruntime as ort

    providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
    try:
        session = ort.InferenceSession(str(onnx_path), providers=providers)
        active_provider = session.get_providers()[0]
        logger.info('onnx_session_created', extra={'path': str(onnx_path), 'provider': active_provider})
        return session
    except Exception as exc:
        logger.warning('onnx_session_failed', extra={'error': str(exc)})
        return None


# ─── Image artifact ───────────────────────────────────────────────────────────

def load_image_artifact(manifest_path: str) -> tuple[Callable[[Image.Image], float], str]:
    from training.runtime_models import build_image_model

    metadata = _load_metadata(manifest_path)
    architecture = metadata['architecture']
    checkpoint_path = Path(metadata['checkpoint_path'])
    onnx_path = checkpoint_path.parent / 'model.onnx'
    image_size = int(metadata.get('preprocessing', {}).get('image_size', 224))

    transform = transforms.Compose([
        transforms.Resize((image_size, image_size)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])

    # ── Try ONNX first ────────────────────────────────────────
    if onnx_path.exists():
        session = _onnx_session(onnx_path)
        if session is not None:
            input_name = session.get_inputs()[0].name

            def infer_onnx(image: Image.Image) -> float:
                tensor = transform(image).unsqueeze(0).numpy()
                output = session.run(None, {input_name: tensor})[0][0]
                probs = _softmax_np(output)
                return clamp(float(probs[1]))

            logger.info('image_artifact_loaded', extra={'mode': 'onnx', 'architecture': architecture})
            return infer_onnx, architecture

    # ── Fallback: PyTorch ─────────────────────────────────────
    model = build_image_model(architecture, pretrained=False)
    state = torch.load(str(checkpoint_path), map_location='cpu', weights_only=True)
    model.load_state_dict(state, strict=False)
    model.eval()

    def infer_pt(image: Image.Image) -> float:
        tensor = transform(image).unsqueeze(0)
        with torch.no_grad():
            logits = model(tensor)
            probs = torch.softmax(logits, dim=1)[0]
        return clamp(float(probs[1]))

    logger.info('image_artifact_loaded', extra={'mode': 'pytorch', 'architecture': architecture})
    return infer_pt, architecture


# ─── Audio artifact ───────────────────────────────────────────────────────────

def load_audio_artifact(manifest_path: str) -> tuple[Callable[[np.ndarray, int], float], str]:
    from training.runtime_models import build_audio_model

    metadata = _load_metadata(manifest_path)
    architecture = metadata['architecture']
    checkpoint_path = Path(metadata['checkpoint_path'])
    onnx_path = checkpoint_path.parent / 'model.onnx'

    preprocessing = metadata.get('preprocessing', {})
    target_sr = int(preprocessing.get('sample_rate', 16000))
    n_mels = int(preprocessing.get('n_mels', 128))
    max_audio_seconds = int(preprocessing.get('max_audio_seconds', 4))

    def _preprocess_audio(audio: np.ndarray, sample_rate: int) -> np.ndarray:
        audio = audio.astype(np.float32)
        if sample_rate != target_sr:
            audio = librosa.resample(audio, orig_sr=sample_rate, target_sr=target_sr)
        max_samples = target_sr * max_audio_seconds
        audio = audio[:max_samples]
        if audio.shape[0] < max_samples:
            audio = np.pad(audio, (0, max_samples - audio.shape[0]))
        mel = librosa.feature.melspectrogram(
            y=audio, sr=target_sr, n_fft=1024, hop_length=256, n_mels=n_mels
        )
        log_mel = librosa.power_to_db(mel + 1e-6).astype(np.float32)
        log_mel = (log_mel - log_mel.min()) / max(log_mel.max() - log_mel.min(), 1e-6)
        # (3, n_mels, time) as float32
        return np.stack([log_mel, log_mel, log_mel], axis=0)[np.newaxis]  # (1,3,H,W)

    # ── Try ONNX first ────────────────────────────────────────
    if onnx_path.exists():
        session = _onnx_session(onnx_path)
        if session is not None:
            input_name = session.get_inputs()[0].name

            def infer_audio_onnx(audio: np.ndarray, sample_rate: int) -> float:
                tensor = _preprocess_audio(audio, sample_rate)
                output = session.run(None, {input_name: tensor})[0][0]
                probs = _softmax_np(output)
                return clamp(float(probs[1]))

            logger.info('audio_artifact_loaded', extra={'mode': 'onnx', 'architecture': architecture})
            return infer_audio_onnx, architecture

    # ── Fallback: PyTorch ─────────────────────────────────────
    model = build_audio_model(architecture, pretrained=False)
    state = torch.load(str(checkpoint_path), map_location='cpu', weights_only=True)
    model.load_state_dict(state, strict=False)
    model.eval()

    def infer_audio_pt(audio: np.ndarray, sample_rate: int) -> float:
        tensor = torch.from_numpy(_preprocess_audio(audio, sample_rate))
        with torch.no_grad():
            logits = model(tensor)
            probs = torch.softmax(logits, dim=1)[0]
        return clamp(float(probs[1]))

    logger.info('audio_artifact_loaded', extra={'mode': 'pytorch', 'architecture': architecture})
    return infer_audio_pt, architecture


# ─── Video artifact ───────────────────────────────────────────────────────────

def load_video_artifact(manifest_path: str) -> tuple[Callable[[str], float], str]:
    from training.runtime_models import build_video_model

    metadata = _load_metadata(manifest_path)
    architecture = metadata['architecture']
    checkpoint_path = Path(metadata['checkpoint_path'])
    onnx_path = checkpoint_path.parent / 'model.onnx'

    preprocessing = metadata.get('preprocessing', {})
    image_size = int(preprocessing.get('image_size', 112))
    clip_frames = int(preprocessing.get('clip_frames', 16))
    clip_stride = int(preprocessing.get('clip_stride', 4))

    MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)

    def _extract_clip(video_path: str) -> np.ndarray:
        """Extract a (1, 3, T, H, W) float32 numpy clip."""
        import cv2
        capture = cv2.VideoCapture(video_path)
        frames: list[np.ndarray] = []
        index = 0
        try:
            while len(frames) < clip_frames:
                ok, frame = capture.read()
                if not ok:
                    break
                if index % clip_stride == 0:
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    frame = cv2.resize(frame, (image_size, image_size))
                    frames.append(frame)
                index += 1
        finally:
            capture.release()
        if not frames:
            frames = [np.zeros((image_size, image_size, 3), dtype=np.uint8)]
        while len(frames) < clip_frames:
            frames.append(frames[-1].copy())
        clip = np.stack(frames[:clip_frames]).astype(np.float32) / 255.0
        clip = (clip - MEAN) / STD
        # (T, H, W, C) → (C, T, H, W) → (1, C, T, H, W)
        return clip.transpose(3, 0, 1, 2)[np.newaxis].astype(np.float32)

    # ── Try ONNX first ────────────────────────────────────────
    if onnx_path.exists():
        session = _onnx_session(onnx_path)
        if session is not None:
            input_name = session.get_inputs()[0].name

            def infer_video_onnx(video_path: str) -> float:
                clip = _extract_clip(video_path)
                output = session.run(None, {input_name: clip})[0][0]
                probs = _softmax_np(output)
                return clamp(float(probs[1]))

            logger.info('video_artifact_loaded', extra={'mode': 'onnx', 'architecture': architecture})
            return infer_video_onnx, architecture

    # ── Fallback: PyTorch ─────────────────────────────────────
    model = build_video_model(architecture, pretrained=False)
    state = torch.load(str(checkpoint_path), map_location='cpu', weights_only=True)
    model.load_state_dict(state, strict=False)
    model.eval()

    def infer_video_pt(video_path: str) -> float:
        clip = torch.from_numpy(_extract_clip(video_path))
        with torch.no_grad():
            logits = model(clip)
            probs = torch.softmax(logits, dim=1)[0]
        return clamp(float(probs[1]))

    logger.info('video_artifact_loaded', extra={'mode': 'pytorch', 'architecture': architecture})
    return infer_video_pt, architecture
