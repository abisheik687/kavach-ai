from __future__ import annotations

import json
from pathlib import Path


def _score_run(result: dict) -> tuple[float, float]:
    metrics = result.get('test_metrics', {})
    return (float(metrics.get('f1', 0.0)), float(metrics.get('auc', 0.0)))


def main() -> None:
    summary_path = Path('training/artifacts/train_all_summary.json')
    if not summary_path.exists():
        raise SystemExit('Summary file not found: training/artifacts/train_all_summary.json')

    with summary_path.open('r', encoding='utf-8') as handle:
        data = json.load(handle)

    all_runs: list[dict] = []
    for modality_runs in data.get('runs', {}).values():
        all_runs.extend(modality_runs)
    if not all_runs:
        raise SystemExit('No runs found in train_all_summary.json')

    best = max(all_runs, key=_score_run)
    metrics = best.get('test_metrics', {})

    print('\nBEST MODEL:')
    print('Modality:', best.get('modality'))
    print('F1:', metrics.get('f1', 0.0))
    print('AUC:', metrics.get('auc', 0.0))
    print('Path:', best.get('metadata_path', ''))


if __name__ == '__main__':
    main()
