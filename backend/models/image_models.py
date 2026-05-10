"""
Internal trace:
- Wrong before: this module had cwd-sensitive imports and a latent `torch` NameError in the timm inference path.
- Fixed now: image model loading works in both execution modes and the timm classifier path has a proper torch import during inference.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Callable

import cv2
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

try:
    from ..config import settings
    from ..utils.file_utils import clamp
except ImportError:
    from config import settings
    from utils.file_utils import clamp


def _sigmoid(value: float) -> float:
    return 1.0 / (1.0 + np.exp(-value))


LabelOrder = str
_CALIBRATOR_CACHE: dict[str, object] | None = None


def _image_stats(image: Image.Image) -> dict[str, float]:
    rgb_u8 = np.asarray(image.convert('RGB'), dtype=np.uint8)
    rgb = rgb_u8.astype(np.float32) / 255.0
    gray = cv2.cvtColor(rgb_u8, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
    hsv = cv2.cvtColor(rgb_u8, cv2.COLOR_RGB2HSV).astype(np.float32) / 255.0
    laplacian = cv2.Laplacian(gray, cv2.CV_32F)
    edges = cv2.Canny(rgb_u8, 80, 160)
    blurred = cv2.GaussianBlur(gray, (0, 0), 1.2)
    residual = np.abs(gray - blurred)
    quantized = (rgb_u8 // 16).reshape(-1, 3)
    unique_ratio = len(np.unique(quantized, axis=0)) / max(len(quantized), 1)
    saturation = float(hsv[..., 1].mean())
    saturation_var = float(hsv[..., 1].var())
    edge_density = float((edges > 0).mean())
    texture = float(np.std(laplacian))
    noise = float(residual.mean())
    flatness = float(np.mean(np.abs(laplacian) < 0.012))
    color_gap = float(np.mean(np.abs(rgb[..., 0] - rgb[..., 2])))
    return {
        'unique_ratio': unique_ratio,
        'saturation': saturation,
        'saturation_var': saturation_var,
        'edge_density': edge_density,
        'texture': texture,
        'noise': noise,
        'flatness': flatness,
        'color_gap': color_gap,
        'width': float(rgb_u8.shape[1]),
        'height': float(rgb_u8.shape[0]),
    }


def _synthetic_artifact_score(image: Image.Image) -> float:
    stats = _image_stats(image)
    cartoon_flat = _sigmoid((stats['flatness'] - 0.70) * 8.0)
    palette_signal = _sigmoid((0.065 - stats['unique_ratio']) * 28.0)
    saturation_signal = _sigmoid((stats['saturation'] - 0.30) * 7.0)
    outline_signal = _sigmoid((stats['edge_density'] - 0.045) * 20.0)
    low_camera_noise = _sigmoid((0.018 - stats['noise']) * 90.0)
    nonphoto = (
        0.28 * cartoon_flat
        + 0.22 * palette_signal
        + 0.20 * saturation_signal
        + 0.16 * outline_signal
        + 0.14 * low_camera_noise
    )
    return clamp(nonphoto)


def _low_quality_synthetic_score(image: Image.Image) -> float:
    stats = _image_stats(image)
    small_source = min(stats['width'], stats['height']) <= 320
    low_texture = _sigmoid((0.055 - stats['texture']) * 26.0)
    low_noise = _sigmoid((0.020 - stats['noise']) * 80.0)
    flat_signal = _sigmoid((stats['flatness'] - 0.72) * 7.0)
    color_signal = _sigmoid((stats['color_gap'] - 0.10) * 7.0)
    score = 0.34 * low_texture + 0.26 * low_noise + 0.24 * flat_signal + 0.16 * color_signal
    if small_source:
        score = max(score, 0.62)
    return clamp(score)


def _blend_fallback(base_score: float, image: Image.Image, bias: float = 0.0) -> float:
    synthetic = _synthetic_artifact_score(image)
    low_quality = _low_quality_synthetic_score(image)
    strong_signal = max(base_score, synthetic, low_quality)
    blended = (0.45 * base_score) + (0.35 * synthetic) + (0.20 * low_quality) + bias
    return clamp(max(blended, 0.92 * strong_signal))


def extract_local_forensic_features(image: Image.Image) -> list[float]:
    """Stable local feature vector used by the free calibrator and runtime scorer."""
    stats = _image_stats(image)
    jpeg = _jpeg_artifact_score(image)
    frequency = _frequency_score(image)
    color = _color_consistency_score(image)
    patch = _patch_consistency_score(image)
    synthetic = _synthetic_artifact_score(image)
    low_quality = _low_quality_synthetic_score(image)
    return [
        jpeg,
        frequency,
        color,
        patch,
        synthetic,
        low_quality,
        stats['unique_ratio'],
        stats['saturation'],
        stats['saturation_var'],
        stats['edge_density'],
        stats['texture'],
        stats['noise'],
        stats['flatness'],
        stats['color_gap'],
        min(stats['width'], stats['height']) / 1024.0,
        max(stats['width'], stats['height']) / 1024.0,
    ]


def _load_local_calibrator() -> dict[str, object] | None:
    global _CALIBRATOR_CACHE
    if _CALIBRATOR_CACHE is not None:
        return _CALIBRATOR_CACHE
    raw_path = settings.local_image_calibrator_path
    if not raw_path:
        _CALIBRATOR_CACHE = {}
        return None
    path = Path(raw_path)
    if not path.is_absolute():
        path = Path(__file__).resolve().parents[1] / raw_path
    if not path.exists():
        _CALIBRATOR_CACHE = {}
        return None
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        _CALIBRATOR_CACHE = {}
        return None
    _CALIBRATOR_CACHE = payload
    return payload


def _calibrated_local_probability(image: Image.Image) -> float | None:
    payload = _load_local_calibrator()
    if not payload:
        return None
    weights = payload.get('weights')
    bias = payload.get('bias')
    means = payload.get('feature_means')
    scales = payload.get('feature_scales')
    if not isinstance(weights, list) or not isinstance(means, list) or not isinstance(scales, list):
        return None
    features = extract_local_forensic_features(image)
    if len(features) != len(weights):
        return None
    z = float(bias or 0.0)
    for value, weight, mean, scale in zip(features, weights, means, scales):
        z += ((float(value) - float(mean)) / max(float(scale), 1e-6)) * float(weight)
    return clamp(_sigmoid(z))


def _fake_probability_from_binary_probs(probs: np.ndarray, label_order: LabelOrder, model_name: str) -> float:
    if label_order not in {'fake_first', 'real_first'}:
        raise ValueError(
            f'{model_name} has invalid label_order={label_order!r}; expected "fake_first" or "real_first".'
        )
    if len(probs) != 2:
        raise ValueError(
            f'{model_name} returned {len(probs)} classes, but binary fake/real output is required '
            f'when label_order={label_order!r}. Check the configured HF repo.'
        )
    fake_index = 0 if label_order == 'fake_first' else 1
    return clamp(float(probs[fake_index]))


def _jpeg_artifact_score(image: Image.Image) -> float:
    rgb = np.asarray(image.convert('RGB'), dtype=np.float32)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    laplacian = cv2.Laplacian(gray, cv2.CV_32F)
    block_rows = np.abs(gray[:, 8:] - gray[:, :-8]).mean() / 255.0
    edge_noise = np.abs(laplacian).mean() / 64.0
    return clamp((0.65 * block_rows) + (0.35 * edge_noise))


def _frequency_score(image: Image.Image) -> float:
    gray = np.asarray(image.convert('L'), dtype=np.float32) / 255.0
    spectrum = np.abs(np.fft.fftshift(np.fft.fft2(gray)))
    h, w = spectrum.shape
    center = spectrum[h // 4 : 3 * h // 4, w // 4 : 3 * w // 4]
    high_freq = spectrum.sum() - center.sum()
    ratio = high_freq / max(spectrum.sum(), 1e-6)
    return clamp(_sigmoid((ratio - 0.62) * 10.0))


def _color_consistency_score(image: Image.Image) -> float:
    rgb = np.asarray(image.convert('RGB'), dtype=np.float32) / 255.0
    ycrcb = cv2.cvtColor((rgb * 255).astype(np.uint8), cv2.COLOR_RGB2YCrCb).astype(np.float32) / 255.0
    channel_gap = np.abs(rgb[..., 0] - rgb[..., 2]).mean()
    chroma_var = float(np.var(ycrcb[..., 1:]))
    return clamp(_sigmoid((channel_gap * 2.4 + chroma_var * 1.8) - 0.9))


def _patch_consistency_score(image: Image.Image) -> float:
    gray = np.asarray(image.convert('L'), dtype=np.float32) / 255.0
    patches = []
    step = max(gray.shape[0] // 8, 16)
    for y in range(0, gray.shape[0] - step + 1, step):
        for x in range(0, gray.shape[1] - step + 1, step):
            patches.append(float(np.var(gray[y : y + step, x : x + step])))
    if not patches:
        return 0.5
    spread = np.std(patches)
    symmetry = np.abs(gray[:, : gray.shape[1] // 2].mean() - gray[:, gray.shape[1] // 2 :].mean())
    return clamp(_sigmoid((spread * 4.0 + symmetry * 2.0) - 0.8))


def _detect_primary_face(image: Image.Image) -> Image.Image:
    rgb = np.asarray(image.convert('RGB'))
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(48, 48))
    if len(faces) == 0:
        return image.convert('RGB')
    x, y, w, h = max(faces, key=lambda face: face[2] * face[3])
    margin = int(min(w, h) * 0.25)
    x0 = max(0, x - margin)
    y0 = max(0, y - margin)
    x1 = min(rgb.shape[1], x + w + margin)
    y1 = min(rgb.shape[0], y + h + margin)
    return Image.fromarray(rgb[y0:y1, x0:x1]).convert('RGB')


@dataclass
class ImageModelSlot:
    key: str
    label: str
    weight: float
    repo_id: str
    label_order: LabelOrder
    loader: Callable[[], tuple[Callable[[Image.Image], float], str]]


class ImageModelFactory:
    def __init__(self) -> None:
        import torch

        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'

    def build_transformers_classifier(
        self,
        repo_id: str,
        label_order: LabelOrder,
        model_name: str,
        local_files_only: bool = False,
    ) -> tuple[Callable[[Image.Image], float], str]:
        import torch
        from transformers import AutoImageProcessor, AutoModelForImageClassification

        processor = AutoImageProcessor.from_pretrained(repo_id, local_files_only=local_files_only)
        model = AutoModelForImageClassification.from_pretrained(repo_id, local_files_only=local_files_only)
        model.eval().to(self.device)

        def infer(image: Image.Image) -> float:
            inputs = processor(images=image, return_tensors='pt')
            inputs = {key: value.to(self.device) for key, value in inputs.items()}
            with torch.no_grad():
                logits = model(**inputs).logits
                probs = torch.softmax(logits, dim=-1)[0].detach().cpu().numpy()
            id2label = {int(key): value.lower() for key, value in model.config.id2label.items()}
            fake_indices = [index for index, label in id2label.items() if 'fake' in label or 'deepfake' in label]
            real_indices = [index for index, label in id2label.items() if 'real' in label or 'auth' in label]
            if fake_indices:
                return clamp(float(sum(probs[index] for index in fake_indices)))
            if real_indices:
                return clamp(1.0 - float(sum(probs[index] for index in real_indices)))
            return _fake_probability_from_binary_probs(probs, label_order, model_name)

        return infer, 'local-hf' if local_files_only else 'primary'

    def build_timm_classifier(
        self,
        repo_id: str,
        model_name: str,
        label_order: LabelOrder,
    ) -> tuple[Callable[[Image.Image], float], str]:
        import torch
        import timm

        model = timm.create_model(f'hf_hub:{repo_id}', pretrained=True)
        model.eval().to(self.device)
        data_config = timm.data.resolve_model_data_config(model)
        transform = timm.data.create_transform(**data_config, is_training=False)

        def infer(image: Image.Image) -> float:
            tensor = transform(image).unsqueeze(0).to(self.device)
            with torch.no_grad():
                logits = model(tensor)
                probs = torch.softmax(logits, dim=-1)[0].detach().cpu().numpy()
            if len(probs) >= 2:
                return _fake_probability_from_binary_probs(probs, label_order, model_name)
            return clamp(float(_sigmoid(float(probs[0]))))

        return infer, 'primary'


def create_image_slots() -> list[ImageModelSlot]:
    factory = ImageModelFactory()
    return [
        ImageModelSlot(
            key='vit',
            label='ViT',
            weight=0.30,
            repo_id=settings.model_vit_repo,
            label_order=settings.model_vit_label_order,
            loader=lambda: factory.build_transformers_classifier(
                settings.model_vit_repo,
                settings.model_vit_label_order,
                'ViT',
            ),
        ),
        ImageModelSlot(
            key='efficientnet',
            label='EfficientNet-B4',
            weight=0.25,
            repo_id=settings.model_efficientnet_repo,
            label_order=settings.model_efficientnet_label_order,
            loader=lambda: factory.build_timm_classifier(
                settings.model_efficientnet_repo,
                'EfficientNet-B4',
                settings.model_efficientnet_label_order,
            ),
        ),
        ImageModelSlot(
            key='xception',
            label='Xception',
            weight=0.25,
            repo_id=settings.model_xception_repo,
            label_order=settings.model_xception_label_order,
            loader=lambda: factory.build_timm_classifier(
                settings.model_xception_repo,
                'Xception',
                settings.model_xception_label_order,
            ),
        ),
        ImageModelSlot(
            key='convnext',
            label='ConvNeXt',
            weight=0.20,
            repo_id=settings.model_convnext_repo,
            label_order=settings.model_convnext_label_order,
            loader=lambda: factory.build_timm_classifier(
                settings.model_convnext_repo,
                'ConvNeXt',
                settings.model_convnext_label_order,
            ),
        ),
    ]


def create_local_ai_image_detector_slot() -> ImageModelSlot | None:
    raw_path = settings.model_ai_image_detector_path
    if not raw_path:
        return None
    path = Path(raw_path)
    if not path.is_absolute():
        path = Path(__file__).resolve().parents[1] / raw_path
    if not (path / 'config.json').exists():
        return None

    factory = ImageModelFactory()
    return ImageModelSlot(
        key='ai_image_detector',
        label='AI Image Detector',
        weight=settings.model_ai_image_detector_weight,
        repo_id=str(path),
        label_order='real_first',
        loader=lambda: factory.build_transformers_classifier(
            str(path),
            'real_first',
            'AI Image Detector',
            local_files_only=True,
        ),
    )


def model_label_order_check(known_fake_image_path: str | Path | None = None) -> dict[str, float]:
    image_path = Path(known_fake_image_path or settings.model_label_order_check_image or '')
    if not image_path.is_file():
        raise FileNotFoundError(
            'model_label_order_check requires a known fake image path. '
            'Pass known_fake_image_path or set MODEL_LABEL_ORDER_CHECK_IMAGE.'
        )

    image = ImageOps.exif_transpose(Image.open(image_path)).convert('RGB')
    results: dict[str, float] = {}
    for slot in create_image_slots():
        infer, _mode = slot.loader()
        fake_probability = clamp(float(infer(image)))
        results[slot.label] = fake_probability
        if fake_probability <= 0.5:
            raise AssertionError(
                f'{slot.label} label order check failed: known fake image scored '
                f'{fake_probability:.4f} fake_probability using label_order={slot.label_order!r}. '
                f'Flip the {slot.key} label_order config or replace repo {slot.repo_id}.'
            )
    return results


def create_fallback_scorer(slot_key: str) -> Callable[[Image.Image], float]:
    def with_calibrator(base_fn: Callable[[Image.Image], float], bias: float = 0.0) -> Callable[[Image.Image], float]:
        def infer(image: Image.Image) -> float:
            heuristic = _blend_fallback(base_fn(image), image, bias=bias)
            calibrated = _calibrated_local_probability(image)
            if calibrated is None:
                return heuristic
            if settings.detection_profile.strip().lower() == 'review':
                blended = (0.65 * heuristic) + (0.35 * calibrated)
                if max(heuristic, calibrated) >= 0.78:
                    blended = max(blended, 0.92 * max(heuristic, calibrated))
                return clamp(blended)
            return clamp(max(heuristic, calibrated))
        return infer

    mapping = {
        'vit': with_calibrator(_jpeg_artifact_score, bias=0.02),
        'efficientnet': with_calibrator(_frequency_score),
        'xception': with_calibrator(_color_consistency_score, bias=0.01),
        'convnext': with_calibrator(_patch_consistency_score, bias=0.02),
    }
    return mapping[slot_key]


def prepare_image(image_bytes: bytes) -> Image.Image:
    try:
        image = ImageOps.exif_transpose(Image.open(BytesIO(image_bytes))).convert('RGB')
    except UnidentifiedImageError as exc:
        raise ValueError('Unsupported or corrupt image file') from exc

    width, height = image.size
    max_side = max(width, height)
    if max_side > 0:
        max_allowed_side = int(np.sqrt(settings.max_image_pixels))
        if width * height > settings.max_image_pixels or max_side > max_allowed_side:
            image.thumbnail((max_allowed_side, max_allowed_side), Image.Resampling.LANCZOS)

    return _detect_primary_face(image)
