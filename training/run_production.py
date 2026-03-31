from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


def _run(command: list[str]) -> int:
    print(f'\n> {" ".join(command)}\n')
    completed = subprocess.run(command, cwd=ROOT_DIR)
    return completed.returncode


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Deadline-safe production training orchestrator')
    parser.add_argument('--seeds', nargs='+', type=int, default=[42], help='Seeds to run in priority order')
    parser.add_argument('--cycles', type=int, default=1, help='Full training cycles to run')
    parser.add_argument('--skip-validate', action='store_true', help='Skip dataset validation step')
    parser.add_argument('--skip-select', action='store_true', help='Skip final best-model selection printout')
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not args.skip_validate:
        code = _run([PYTHON, 'training/datasets/validate_dataset.py'])
        if code != 0:
            raise SystemExit(code)

    train_cmd = [PYTHON, 'training/train_all.py', '--modality', 'all', '--cycles', str(args.cycles), '--seeds']
    train_cmd.extend(str(seed) for seed in args.seeds)
    code = _run(train_cmd)
    if code != 0:
        raise SystemExit(code)

    if not args.skip_select:
        code = _run([PYTHON, 'training/select_best_model.py'])
        if code != 0:
            raise SystemExit(code)

    print('\nDeadline training flow complete.')
    print('Next steps:')
    print('  1. cd backend && uvicorn main:app --reload')
    print('  2. cd frontend && npm run dev')
    print("  3. Set TEST_MODE=true only when running pytest")


if __name__ == '__main__':
    main()
