from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from training.multimodal_pipeline import load_config, set_seed, train_modality


def main() -> None:
    parser = argparse.ArgumentParser(description='Train multimodal deepfake detectors locally')
    parser.add_argument('--config', default=str(Path(__file__).resolve().with_name('multimodal_config.yaml')))
    parser.add_argument('--modality', choices=['image', 'audio', 'video', 'all'], default='all')
    args = parser.parse_args()

    config = load_config(args.config)
    set_seed(config.seed)

    modalities = ['image', 'audio', 'video'] if args.modality == 'all' else [args.modality]
    results = {modality: train_modality(config, modality) for modality in modalities}

    output_path = Path(config.output_root) / 'latest_training_summary.json'
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(results, indent=2), encoding='utf-8')
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
