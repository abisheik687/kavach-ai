from __future__ import annotations

import argparse
import json
import logging
from collections import defaultdict
from pathlib import Path

import cv2
import soundfile as sf
from PIL import Image

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
VIDEO_EXTS = {'.mp4', '.avi', '.mov', '.mkv', '.webm'}
AUDIO_EXTS = {'.wav', '.mp3', '.ogg', '.flac', '.m4a'}
EXPECTED_DATASETS = {
    'image': ['faceforensics_pp', 'celeb_df', 'dfdc'],
    'video': ['faceforensics_pp', 'celeb_df', 'dfdc'],
    'audio': ['asvspoof', 'fakeavceleb'],
}

def is_valid_image(path: Path) -> bool:
    try:
        with Image.open(path) as img:
            img.verify()
        return True
    except Exception:
        return False

def is_valid_video(path: Path) -> bool:
    try:
        cap = cv2.VideoCapture(str(path))
        if not cap.isOpened():
            return False
        ret, _ = cap.read()
        cap.release()
        return ret
    except Exception:
        return False

def is_valid_audio(path: Path) -> bool:
    try:
        # Note: soundfile might not support mp3 in some environments, but assuming typical setup
        info = sf.info(str(path))
        if info.frames > 0:
            return True
        return False
    except Exception:
        return False

def _expected_extensions(modality: str) -> set[str]:
    if modality == 'image':
        return IMAGE_EXTS
    if modality == 'video':
        return VIDEO_EXTS
    return AUDIO_EXTS


def _scan_label_dir(modality: str, label_dir: Path) -> tuple[int, int, list[str], list[str]]:
    valid_count = 0
    corrupted_count = 0
    corrupted_files: list[str] = []
    invalid_format_files: list[str] = []
    for fp in label_dir.rglob('*'):
        if not fp.is_file():
            continue
        ext = fp.suffix.lower()
        if ext not in _expected_extensions(modality):
            invalid_format_files.append(str(fp))
            continue

        is_valid = False
        if modality == 'image':
            is_valid = is_valid_image(fp)
        elif modality == 'video':
            is_valid = is_valid_video(fp)
        else:
            is_valid = is_valid_audio(fp)

        if is_valid:
            valid_count += 1
        else:
            corrupted_count += 1
            corrupted_files.append(str(fp))
    return valid_count, corrupted_count, corrupted_files, invalid_format_files


def main():
    parser = argparse.ArgumentParser(description='Validate and audit training datasets')
    parser.add_argument('--data-dir', default='data', help='Root path containing image, audio, video subdirs')
    parser.add_argument('--dry-run', action='store_true', help='Do not delete corrupted files, just report them')
    parser.add_argument('--output', default='training/artifacts/dataset_validation_report.json', help='JSON report path')
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        logger.error(f'Directory {data_dir} does not exist.')
        return

    report: dict[str, object] = {
        'data_dir': str(data_dir.resolve()),
        'dry_run': args.dry_run,
        'modalities': defaultdict(dict),
        'warnings': [],
        'errors': [],
        'totals': {'valid_files': 0, 'corrupted_files': 0, 'invalid_format_files': 0},
    }

    for modality, datasets in EXPECTED_DATASETS.items():
        modality_root = data_dir / modality
        if not modality_root.exists():
            report['errors'].append(f'Missing modality folder: {modality_root}')
            continue

        for dataset_name in datasets:
            dataset_root = modality_root / dataset_name
            dataset_result = {
                'path': str(dataset_root),
                'real': 0,
                'fake': 0,
                'corrupted_files': [],
                'invalid_format_files': [],
                'status': 'ok',
            }
            if not dataset_root.exists():
                dataset_result['status'] = 'missing'
                report['errors'].append(f'Missing dataset folder: {dataset_root}')
                report['modalities'][modality][dataset_name] = dataset_result
                continue

            for label in ('real', 'fake'):
                label_dir = dataset_root / label
                if not label_dir.exists():
                    report['warnings'].append(f'Missing label folder: {label_dir}')
                    continue
                valid_count, corrupted_count, corrupted_files, invalid_format_files = _scan_label_dir(modality, label_dir)
                dataset_result[label] = valid_count
                dataset_result['corrupted_files'].extend(corrupted_files)
                dataset_result['invalid_format_files'].extend(invalid_format_files)
                report['totals']['valid_files'] += valid_count
                report['totals']['corrupted_files'] += corrupted_count
                report['totals']['invalid_format_files'] += len(invalid_format_files)
                if corrupted_files and not args.dry_run:
                    for file_path in corrupted_files:
                        try:
                            Path(file_path).unlink()
                        except OSError as exc:
                            report['warnings'].append(f'Failed to delete corrupted file {file_path}: {exc}')

            total = dataset_result['real'] + dataset_result['fake']
            dataset_result['total'] = total
            if total == 0:
                dataset_result['status'] = 'empty'
                report['warnings'].append(f'Empty dataset: {dataset_root}')
            elif min(dataset_result['real'], dataset_result['fake']) == 0:
                dataset_result['status'] = 'one_class_missing'
                report['warnings'].append(f'Class missing in {dataset_root}')
            else:
                imbalance = max(dataset_result['real'], dataset_result['fake']) / max(min(dataset_result['real'], dataset_result['fake']), 1)
                dataset_result['imbalance_ratio'] = round(float(imbalance), 3)
                if imbalance > 1.5:
                    dataset_result['status'] = 'imbalanced'
                    report['warnings'].append(f'Class imbalance {imbalance:.2f}:1 in {dataset_root}')

            report['modalities'][modality][dataset_name] = dataset_result

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding='utf-8')

    logger.info('============== DATASET VALIDATION ==============')
    for modality, datasets in report['modalities'].items():
        logger.info(f'Modality: {str(modality).upper()}')
        for dataset_name, dataset_result in datasets.items():
            logger.info(
                '  - %s: total=%s real=%s fake=%s status=%s',
                dataset_name,
                dataset_result.get('total', 0),
                dataset_result.get('real', 0),
                dataset_result.get('fake', 0),
                dataset_result.get('status', 'unknown'),
            )
    logger.info('Warnings: %s', len(report['warnings']))
    logger.info('Errors: %s', len(report['errors']))
    logger.info('JSON report: %s', output_path)

if __name__ == '__main__':
    main()
