"""
KAVACH-AI — Full Training Orchestration
========================================
Runs the complete training pipeline:
  1. Generates synthetic datasets (skips if already exist)
  2. Trains image model (EfficientNet-B4)
  3. Trains audio model (EfficientNet-B0 on mel-spectrograms)
  4. Trains video model (R3D-18 3D-CNN)
  5. Writes training/artifacts/manifest.json with all artifact paths
  6. Prints next-step instructions for backend configuration

Usage (from project root, with .venv activated):
    python training/train_all.py

Requirements:
    pip install -r requirements.txt

Output:
    training/artifacts/
      manifest.json                 ← paths for .env configuration
      image/efficientnet_b4_{ts}/
        model.pt, model.onnx, metadata.json, report.json, ...
      audio/audio_spectrogram_efficientnet_b0_{ts}/
        model.pt, model.onnx, metadata.json, report.json, ...
      video/r3d_18_{ts}/
        model.pt, model.onnx, metadata.json, report.json, ...
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

# ── Ensure project root is importable ────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from training.datasets.generate_synthetic import generate_all
from training.multimodal_pipeline import RunConfig, load_config, set_seed, train_modality

CONFIG_PATH = ROOT / 'training' / 'multimodal_config.yaml'
MANIFEST_PATH = ROOT / 'training' / 'artifacts' / 'manifest.json'
ENV_PATH = ROOT / '.env'


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _divider(char: str = '═', width: int = 64) -> None:
    print(char * width)


def _fmt_time(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f'{m}m {s:02d}s' if m else f'{s}s'


def _print_report(report: dict, elapsed: float) -> None:
    test = report.get('test_metrics', {})
    print(f"  Architecture : {report['architecture']}")
    print(f"  Best epoch   : {report['best_epoch']}")
    print(f"  Val AUC      : {report['best_val_auc']:.4f}")
    print(f"  Test accuracy: {test.get('accuracy', 0):.4f}")
    print(f"  Test AUC     : {test.get('auc', 0):.4f}")
    print(f"  Test F1      : {test.get('f1', 0):.4f}")
    print(f"  Elapsed      : {_fmt_time(elapsed)}")
    print(f"  Artifact dir : {report['artifact_dir']}")
    print(f"  Manifest     : {report['metadata_path']}")


def _update_env_file(image_path: str, audio_path: str, video_path: str) -> None:
    """Write or update MODEL_*_ARTIFACT_MANIFEST lines in .env."""
    env_path = ENV_PATH

    # Read existing .env (if present)
    if env_path.exists():
        lines = env_path.read_text(encoding='utf-8').splitlines()
    else:
        lines = []

    keys_to_set = {
        'MODEL_IMAGE_ARTIFACT_MANIFEST': image_path,
        'MODEL_AUDIO_ARTIFACT_MANIFEST': audio_path,
        'MODEL_VIDEO_ARTIFACT_MANIFEST': video_path,
        'ALLOW_FALLBACK_MODELS': 'false',
        'ENABLE_REMOTE_MODEL_DOWNLOADS': 'false',
    }

    updated_keys: set[str] = set()
    new_lines = []
    for line in lines:
        stripped = line.strip()
        matched = False
        for key in keys_to_set:
            if stripped.startswith(f'{key}=') or stripped.startswith(f'{key} ='):
                new_lines.append(f'{key}={keys_to_set[key]}')
                updated_keys.add(key)
                matched = True
                break
        if not matched:
            new_lines.append(line)

    # Append any keys not already present
    for key, value in keys_to_set.items():
        if key not in updated_keys:
            new_lines.append(f'{key}={value}')

    env_path.write_text('\n'.join(new_lines) + '\n', encoding='utf-8')


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    overall_start = time.time()

    _divider()
    print('KAVACH-AI — Full Training Pipeline')
    _divider()
    print(f'Config  : {CONFIG_PATH}')
    print(f'PyTorch :')
    import torch
    print(f'  version : {torch.__version__}')
    cuda_available = torch.cuda.is_available()
    device = 'cuda' if cuda_available else 'cpu'
    print(f'  device  : {device}', end='')
    if cuda_available:
        print(f' ({torch.cuda.get_device_name(0)})')
    else:
        print()
    _divider()

    # ── Step 1: Generate synthetic datasets ───────────────────
    print('\n[STEP 1/4] Generating synthetic datasets...')
    print('  (uses existing files if already generated)\n')
    generate_all()

    # ── Step 2: Load config ───────────────────────────────────
    config: RunConfig = load_config(CONFIG_PATH)
    set_seed(config.seed)

    reports: dict[str, dict] = {}
    metadata_paths: dict[str, str] = {}

    # ── Step 3: Train each modality ───────────────────────────
    modalities = ['image', 'audio', 'video']
    for step_num, modality in enumerate(modalities, start=2):
        _divider()
        print(f'\n[STEP {step_num}/4] Training {modality.upper()} model...')
        _divider()
        t0 = time.time()
        try:
            report = train_modality(config, modality)
            elapsed = time.time() - t0
            reports[modality] = report
            metadata_paths[modality] = report['metadata_path']
            print(f'\n  ✓ {modality.upper()} training complete')
            _print_report(report, elapsed)
        except Exception as exc:
            elapsed = time.time() - t0
            print(f'\n  ✗ {modality.upper()} training FAILED after {_fmt_time(elapsed)}:')
            print(f'  {type(exc).__name__}: {exc}')
            import traceback
            traceback.print_exc()
            sys.exit(1)

    # ── Step 4: Write master manifest ─────────────────────────
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(metadata_paths, indent=2), encoding='utf-8')

    # ── Update .env automatically ─────────────────────────────
    _update_env_file(
        image_path=metadata_paths.get('image', ''),
        audio_path=metadata_paths.get('audio', ''),
        video_path=metadata_paths.get('video', ''),
    )

    # ── Final summary ─────────────────────────────────────────
    total_elapsed = time.time() - overall_start
    _divider('═')
    print('\nTRAINING COMPLETE')
    _divider('═')
    print(f'  Total time  : {_fmt_time(total_elapsed)}')
    print(f'  Master manifest : {MANIFEST_PATH}')
    print()
    print('  Artifact manifest paths (also written to .env):')
    for modality, path in metadata_paths.items():
        key = f'MODEL_{modality.upper()}_ARTIFACT_MANIFEST'
        print(f'    {key}={path}')

    print()
    print('  Next steps:')
    print('  1. Start backend:')
    print('       cd backend && uvicorn main:app --reload')
    print('  2. Start frontend:')
    print('       cd frontend && npm run dev')
    print('  3. Validate end-to-end:')
    print('       python scripts/validate_e2e.py')
    _divider('═')


if __name__ == '__main__':
    main()
