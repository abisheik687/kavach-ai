from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / 'data'

DATASET_LAYOUT = {
    'image': {
        'faceforensics_pp': DATA_DIR / 'image' / 'faceforensics_pp',
        'celeb_df': DATA_DIR / 'image' / 'celeb_df',
        'dfdc': DATA_DIR / 'image' / 'dfdc',
    },
    'video': {
        'faceforensics_pp': DATA_DIR / 'video' / 'faceforensics_pp',
        'dfdc': DATA_DIR / 'video' / 'dfdc',
    },
    'audio': {
        'asvspoof': DATA_DIR / 'audio' / 'asvspoof',
        'fakeavceleb': DATA_DIR / 'audio' / 'fakeavceleb',
    },
}

OFFICIAL_SOURCES = {
    'faceforensics_pp': 'https://github.com/ondyari/FaceForensics',
    'celeb_df': 'https://github.com/yuezunli/celeb-deepfakeforensics',
    'dfdc': 'https://www.kaggle.com/c/deepfake-detection-challenge/data',
    'asvspoof': 'https://www.asvspoof.org/',
    'fakeavceleb': 'https://github.com/DASH-Lab/FakeAVCeleb',
}


def ensure_layout() -> None:
    for groups in DATASET_LAYOUT.values():
        for target in groups.values():
            for label in ('real', 'fake'):
                (target / label).mkdir(parents=True, exist_ok=True)


def dataset_status() -> dict[str, dict]:
    summary: dict[str, dict] = {}
    for modality, groups in DATASET_LAYOUT.items():
        summary[modality] = {}
        for dataset_name, dataset_root in groups.items():
            real_count = sum(1 for path in (dataset_root / 'real').rglob('*') if path.is_file())
            fake_count = sum(1 for path in (dataset_root / 'fake').rglob('*') if path.is_file())
            summary[modality][dataset_name] = {
                'root': str(dataset_root),
                'real_count': real_count,
                'fake_count': fake_count,
                'ready': real_count > 0 and fake_count > 0,
                'official_source': OFFICIAL_SOURCES.get(dataset_name, ''),
            }
    return summary


def print_status() -> None:
    summary = dataset_status()
<<<<<<< HEAD
    print('\nKAVACH-AI dataset acquisition status\n')
=======
    print('\nMultimodal Deepfake Detection System Using Advanced Machine Learning Techniques dataset acquisition status\n')
>>>>>>> 7df14d1 (UI enhanced)
    for modality, groups in summary.items():
        print(f'[{modality}]')
        for dataset_name, info in groups.items():
            state = 'ready' if info['ready'] else 'missing'
            print(
                f"  - {dataset_name}: {state} | real={info['real_count']} | fake={info['fake_count']} | {info['root']}"
            )
            if not info['ready']:
                print(f"    source: {info['official_source']}")


def write_report() -> Path:
    report_path = ROOT_DIR / 'training' / 'artifacts' / 'dataset_acquisition_status.json'
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(dataset_status(), indent=2), encoding='utf-8')
    return report_path


def import_local_folder(source: Path, target: Path) -> None:
    if not source.exists():
        raise FileNotFoundError(f'Source path does not exist: {source}')

    copied = 0
    for label in ('real', 'fake'):
        source_dir = source / label
        if not source_dir.exists():
            continue
        target_dir = target / label
        target_dir.mkdir(parents=True, exist_ok=True)
        for item in source_dir.rglob('*'):
            if not item.is_file():
                continue
            destination = target_dir / item.name
            if destination.exists():
                destination = target_dir / f'{item.stem}_{copied}{item.suffix}'
            shutil.copy2(item, destination)
            copied += 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Prepare local dataset folders for the deadline training run')
    parser.add_argument('--status', action='store_true', help='Print current dataset readiness')
    parser.add_argument('--write-report', action='store_true', help='Write JSON status report under training/artifacts')
    parser.add_argument('--import-modality', choices=['image', 'video', 'audio'])
    parser.add_argument('--import-dataset')
    parser.add_argument('--from-path')
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ensure_layout()

    if args.import_modality or args.import_dataset or args.from_path:
        if not (args.import_modality and args.import_dataset and args.from_path):
            raise SystemExit('--import-modality, --import-dataset, and --from-path must be provided together')
        target = DATASET_LAYOUT.get(args.import_modality, {}).get(args.import_dataset)
        if target is None:
            raise SystemExit(f'Unknown dataset target: {args.import_modality}/{args.import_dataset}')
        import_local_folder(Path(args.from_path), target)

    if args.status or (not args.write_report and not args.import_modality):
        print_status()

    if args.write_report or args.import_modality:
        report_path = write_report()
        print(f'\nWrote status report: {report_path}')

    missing = [
        f'{modality}/{dataset_name}'
        for modality, groups in dataset_status().items()
        for dataset_name, info in groups.items()
        if not info['ready']
    ]
    if missing:
        print('\nDatasets still missing labels or files:')
        for item in missing:
            print(f'  - {item}')
        print('\nOfficial sources:')
        for name, url in OFFICIAL_SOURCES.items():
            print(f'  - {name}: {url}')
        sys.exit(1)


if __name__ == '__main__':
    main()
