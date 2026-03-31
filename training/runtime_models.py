from __future__ import annotations

from pathlib import Path

import timm
import torch
import torch.nn as nn
import torchvision


IMAGE_ARCHITECTURE_ALIASES = {
    'convnext_base': 'convnext_base',
    'swinv2_small_window16_256': 'swinv2_small_window16_256',
}

AUDIO_ARCHITECTURE_ALIASES = {
    'audio_spectrogram_efficientnet_b0': 'efficientnet_b0',
    'audio_spectrogram_resnet18': 'resnet18',
    'audio_spectrogram_convnext_tiny': 'convnext_tiny',
}

VIDEO_ARCHITECTURE_ALIASES = {
    'r3d_18': 'r3d_18',
    'mc3_18': 'mc3_18',
    'r2plus1d_18': 'r2plus1d_18',
}


def _resolve_image_architecture(architecture: str) -> str:
    resolved = IMAGE_ARCHITECTURE_ALIASES.get(architecture, architecture)
    if resolved not in timm.list_models(pretrained=False):
        raise ValueError(
            f'Unsupported image architecture: {architecture}. '
            f'Supported aliases: {", ".join(sorted(IMAGE_ARCHITECTURE_ALIASES))}'
        )
    return resolved


def build_image_model(architecture: str, num_classes: int = 2, pretrained: bool = True) -> nn.Module:
    resolved_architecture = _resolve_image_architecture(architecture)
    return timm.create_model(
        resolved_architecture,
        pretrained=pretrained,
        num_classes=num_classes,
        drop_rate=0.2,
    )


def build_audio_model(architecture: str, num_classes: int = 2, pretrained: bool = True) -> nn.Module:
    if architecture == 'audio_spectrogram_efficientnet_b0':
        model = timm.create_model('efficientnet_b0', pretrained=pretrained, num_classes=num_classes, in_chans=3)
        return model
    if architecture == 'audio_spectrogram_resnet18':
        model = torchvision.models.resnet18(weights='DEFAULT' if pretrained else None)
        model.fc = nn.Linear(model.fc.in_features, num_classes)
        return model
    if architecture == 'audio_spectrogram_convnext_tiny':
        model = timm.create_model('convnext_tiny', pretrained=pretrained, num_classes=num_classes, in_chans=3)
        return model
    raise ValueError(f'Unsupported audio architecture: {architecture}')


def build_video_model(architecture: str, num_classes: int = 2, pretrained: bool = True) -> nn.Module:
    weights = 'DEFAULT' if pretrained else None
    if architecture == 'r3d_18':
        model = torchvision.models.video.r3d_18(weights=weights)
    elif architecture == 'mc3_18':
        model = torchvision.models.video.mc3_18(weights=weights)
    elif architecture == 'r2plus1d_18':
        model = torchvision.models.video.r2plus1d_18(weights=weights)
    else:
        raise ValueError(
            f'Unsupported video architecture: {architecture}. '
            f'Supported aliases: {", ".join(sorted(VIDEO_ARCHITECTURE_ALIASES))}'
        )
    model.fc = nn.Linear(model.fc.in_features, num_classes)
    return model


def save_training_artifact(
    *,
    model: nn.Module,
    output_dir: Path,
    modality: str,
    architecture: str,
    metrics: dict,
    preprocessing: dict,
    datasets: list[str],
    label_map: dict[str, int] | None = None,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = output_dir / 'model.pt'
    manifest_path = output_dir / 'metadata.json'

    torch.save(model.state_dict(), checkpoint_path)
    metadata = {
        'modality': modality,
        'architecture': architecture,
        'checkpoint_path': str(checkpoint_path),
        'metrics': metrics,
        'preprocessing': preprocessing,
        'datasets': datasets,
        'label_map': label_map or {'real': 0, 'fake': 1},
    }
    manifest_path.write_text(__import__('json').dumps(metadata, indent=2), encoding='utf-8')
    return checkpoint_path, manifest_path
