"""
<<<<<<< HEAD
KAVACH-AI Training Data Pipeline — Step 2: Manifest Builder
=======
Multimodal Deepfake Detection System Using Advanced Machine Learning Techniques Training Data Pipeline — Step 2: Manifest Builder
>>>>>>> 7df14d1 (UI enhanced)
============================================================
Scans data/processed/real/ and data/processed/fake/,
builds a stratified train/val/test split CSV manifest.

Usage:
  python training/build_manifest.py \
    --real_dir  data/processed/real \
    --fake_dir  data/processed/fake \
    --output    training/dataset_manifest.csv \
    --val_frac  0.10 \
    --test_frac 0.10
"""
import argparse
import csv
import hashlib
import logging
import os
import random
from pathlib import Path

import numpy as np
from PIL import Image
from tqdm import tqdm

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] %(message)s')

SUPPORTED = {'.png', '.jpg', '.jpeg', '.webp'}
MIN_RESOLUTION = 112  # reject faces smaller than this in either dimension


def scan_directory(directory: Path, label: int) -> list[dict]:
    """
    Walk directory, collect metadata for each valid image.
    Returns list of record dicts.
    """
    records = []
    for path in tqdm(sorted(directory.rglob('*')),
                     desc=f'Scanning label={label}'):
        if path.suffix.lower() not in SUPPORTED:
            continue
        try:
            img = Image.open(path)
            w, h = img.size
            if w < MIN_RESOLUTION or h < MIN_RESOLUTION:
                log.debug(f'Skipping low-res {path.name}: {w}x{h}')
                continue
            # Quick hash for duplicate detection
            img_arr = np.array(img.convert('RGB'))
            img_hash = hashlib.md5(img_arr.tobytes()).hexdigest()[:16]
            # Infer source dataset from parent directory name
            source = path.parent.name
            records.append({
                'filepath':  str(path),
                'label':     label,
                'source':    source,
                'width':     w,
                'height':    h,
                'img_hash':  img_hash,
            })
        except Exception as e:
            log.warning(f'Cannot open {path.name}: {e}')
    return records


def deduplicate(records: list[dict]) -> tuple[list[dict], int]:
    """Remove duplicate images by hash. Returns (clean_records, n_removed)."""
    seen: set[str] = set()
    clean, dupes = [], 0
    for r in records:
        if r['img_hash'] in seen:
            dupes += 1
        else:
            seen.add(r['img_hash'])
            clean.append(r)
    return clean, dupes


def stratified_split(
    records: list[dict],
    val_frac: float,
    test_frac: float,
    seed: int = 42,
) -> list[dict]:
    """
    Assign split='train'|'val'|'test' to each record.
    Stratified by (label, source) to balance class and dataset origin.
    """
    rng = random.Random(seed)
    # Group by (label, source)
    groups: dict[tuple, list] = {}
    for r in records:
        key = (r['label'], r['source'])
        groups.setdefault(key, []).append(r)

    for key, group in groups.items():
        rng.shuffle(group)
        n      = len(group)
        n_val  = max(1, int(n * val_frac))
        n_test = max(1, int(n * test_frac))
        for i, rec in enumerate(group):
            if i < n_val:
                rec['split'] = 'val'
            elif i < n_val + n_test:
                rec['split'] = 'test'
            else:
                rec['split'] = 'train'
    return records


def print_statistics(records: list[dict]) -> None:
    from collections import Counter
    splits   = Counter(r['split']  for r in records)
    labels   = Counter(r['label']  for r in records)
    sources  = Counter(r['source'] for r in records)
    print('\n=== Dataset Statistics ===')
    print(f'  Total samples : {len(records)}')
    print(f'  Real  (0)     : {labels[0]}')
    print(f'  Fake  (1)     : {labels[1]}')
    balance = labels[0] / max(1, labels[1])
    print(f'  Class balance : {balance:.3f}  (1.0 = perfectly balanced)')
    if balance < 0.8 or balance > 1.25:
        print('  ⚠  WARNING: Dataset is imbalanced. Consider oversampling minority class.')
    print('\n  Splits:')
    for split, count in sorted(splits.items()):
        pct = count / len(records) * 100
        print(f'    {split:<8}: {count:>6} ({pct:.1f}%)')
    print('\n  Sources:')
    for src, count in sources.most_common():
        print(f'    {src:<30}: {count:>6}')


def main():
<<<<<<< HEAD
    parser = argparse.ArgumentParser(description='KAVACH-AI Manifest Builder')
=======
    parser = argparse.ArgumentParser(description='Multimodal Deepfake Detection System Using Advanced Machine Learning Techniques Manifest Builder')
>>>>>>> 7df14d1 (UI enhanced)
    parser.add_argument('--real_dir',  required=True,  type=Path)
    parser.add_argument('--fake_dir',  required=True,  type=Path)
    parser.add_argument('--output',    default='training/dataset_manifest.csv', type=Path)
    parser.add_argument('--val_frac',  default=0.10,   type=float)
    parser.add_argument('--test_frac', default=0.10,   type=float)
    parser.add_argument('--seed',      default=42,     type=int)
    args = parser.parse_args()

    real_records = scan_directory(args.real_dir, label=0)
    fake_records = scan_directory(args.fake_dir, label=1)
    all_records  = real_records + fake_records

    log.info(f'Before dedup: {len(all_records)} records')
    all_records, n_dupes = deduplicate(all_records)
    log.info(f'After dedup:  {len(all_records)} records  ({n_dupes} duplicates removed)')

    all_records = stratified_split(all_records, args.val_frac, args.test_frac, args.seed)

    # Write CSV
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ['filepath','label','source','width','height','img_hash','split']
    with open(args.output, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_records)

    log.info(f'Manifest saved: {args.output}  ({len(all_records)} rows)')
    print_statistics(all_records)


if __name__ == '__main__':
    main()
