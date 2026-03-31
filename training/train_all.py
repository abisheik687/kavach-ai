from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from training.multimodal_pipeline import audit_dataset_quality, load_config, set_seed, train_modality


def _latest_misclassified_path(output_root: Path, modality: str) -> Path | None:
    modality_root = output_root / modality
    if not modality_root.exists():
        return None
    candidates = sorted(modality_root.rglob('misclassified.json'), key=lambda path: path.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def _score_run(result: dict) -> tuple[float, float]:
    metrics = result.get('test_metrics', {})
    return (float(metrics.get('f1', 0.0)), float(metrics.get('auc', 0.0)))


def _write_best_env(best_runs: dict[str, dict], root_dir: Path) -> None:
    env_path = root_dir / '.env'
    existing_lines = env_path.read_text(encoding='utf-8').splitlines() if env_path.exists() else []
    replacements = {
        'MODEL_IMAGE_ARTIFACT_MANIFEST': str(best_runs.get('image', {}).get('metadata_path', '')),
        'MODEL_AUDIO_ARTIFACT_MANIFEST': str(best_runs.get('audio', {}).get('metadata_path', '')),
        'MODEL_VIDEO_ARTIFACT_MANIFEST': str(best_runs.get('video', {}).get('metadata_path', '')),
    }

    written_keys: set[str] = set()
    updated_lines: list[str] = []
    for line in existing_lines:
        stripped = line.strip()
        replaced = False
        for key, value in replacements.items():
            if stripped.startswith(f'{key}=') or stripped.startswith(f'{key} ='):
                updated_lines.append(f'{key}={value}')
                written_keys.add(key)
                replaced = True
                break
        if not replaced:
            updated_lines.append(line)

    for key, value in replacements.items():
        if key not in written_keys:
            updated_lines.append(f'{key}={value}')

    env_path.write_text('\n'.join(updated_lines).rstrip() + '\n', encoding='utf-8')


def main() -> None:
    parser = argparse.ArgumentParser(description='Run multimodal training across modalities and seeds')
    parser.add_argument('--config', default=str(Path(__file__).resolve().with_name('multimodal_config.yaml')))
    parser.add_argument('--modality', choices=['image', 'audio', 'video', 'all'], default='all')
    parser.add_argument('--seeds', nargs='+', type=int, default=[42, 1337, 2024])
    parser.add_argument('--cycles', type=int, default=1, help='Repeat full training cycles for harder retraining loops')
    args = parser.parse_args()

    config = load_config(args.config)
    modalities = ['image', 'audio', 'video'] if args.modality == 'all' else [args.modality]
    output_root = Path(config.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    audits = {modality: audit_dataset_quality(config, modality) for modality in modalities}
    runs: dict[str, list[dict]] = {modality: [] for modality in modalities}

    for cycle in range(1, args.cycles + 1):
        for seed in args.seeds:
            config.seed = seed
            set_seed(seed)
            for modality in modalities:
                result = train_modality(config, modality)
                result['seed'] = seed
                result['cycle'] = cycle
                result['latest_misclassified'] = str(_latest_misclassified_path(output_root, modality) or '')
                runs[modality].append(result)

    best_runs = {}
    for modality, results in runs.items():
        if results:
            best_runs[modality] = max(results, key=_score_run)

    payload = {
        'audits': audits,
        'runs': runs,
        'best_runs': best_runs,
    }
    output_path = output_root / 'train_all_summary.json'
    output_path.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    _write_best_env(best_runs, ROOT_DIR)
    print(json.dumps(payload, indent=2))


if __name__ == '__main__':
    main()
