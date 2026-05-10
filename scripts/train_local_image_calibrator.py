#!/usr/bin/env python
"""Train a free local image calibrator for KAVACH-AI fallback scoring.

This script does not call Hugging Face and does not require paid inference.
It learns a lightweight logistic calibrator from the existing image manifest
using stable forensic features from backend.models.image_models.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image
from sklearn.linear_model import SGDClassifier
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.models.image_models import extract_local_forensic_features


IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif'}


def load_rows(manifest: Path, split: str, max_per_class: int, seed: int) -> list[dict[str, str]]:
    by_label: dict[int, list[dict[str, str]]] = {0: [], 1: []}
    with manifest.open('r', newline='', encoding='utf-8') as handle:
        for row in csv.DictReader(handle):
            if row.get('split') != split:
                continue
            label = int(row['label'])
            path = Path(row['path'])
            if label in by_label and path.suffix.lower() in IMAGE_EXTS and path.exists():
                by_label[label].append(row)
    rng = random.Random(seed)
    sampled: list[dict[str, str]] = []
    for rows in by_label.values():
        rng.shuffle(rows)
        sampled.extend(rows[:max_per_class])
    rng.shuffle(sampled)
    return sampled


def hard_rows(root: Path, max_per_class: int, seed: int) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    rng = random.Random(seed)
    for label_name, label in [('real', 0), ('fake', 1)]:
        folder = root / label_name
        if not folder.exists():
            continue
        paths = [path for path in folder.iterdir() if path.is_file() and path.suffix.lower() in IMAGE_EXTS]
        rng.shuffle(paths)
        rows.extend(
            {
                'path': str(path),
                'label': str(label),
                'dataset': 'hard_examples_image',
                'split': 'hard',
            }
            for path in paths[:max_per_class]
        )
    rng.shuffle(rows)
    return rows


def extract_matrix(rows: list[dict[str, str]]) -> tuple[np.ndarray, np.ndarray, list[str]]:
    features: list[list[float]] = []
    labels: list[int] = []
    paths: list[str] = []
    for row in rows:
        path = Path(row['path'])
        try:
            image = Image.open(path).convert('RGB')
            features.append(extract_local_forensic_features(image))
            labels.append(int(row['label']))
            paths.append(str(path))
        except Exception:
            continue
    if not features:
        return np.empty((0, 0), dtype=np.float32), np.empty((0,), dtype=np.int64), []
    return np.asarray(features, dtype=np.float32), np.asarray(labels, dtype=np.int64), paths


def metrics_for(y_true: np.ndarray, y_prob: np.ndarray, threshold: float) -> dict[str, Any]:
    y_pred = (y_prob >= threshold).astype(np.int64)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    metrics: dict[str, Any] = {
        'threshold': float(threshold),
        'accuracy': float(accuracy_score(y_true, y_pred)),
        'precision': float(precision_score(y_true, y_pred, zero_division=0)),
        'recall': float(recall_score(y_true, y_pred, zero_division=0)),
        'f1': float(f1_score(y_true, y_pred, zero_division=0)),
        'fake_false_negative_rate': float(fn / max(fn + tp, 1)),
        'real_false_positive_rate': float(fp / max(fp + tn, 1)),
        'confusion_matrix': {'tn': int(tn), 'fp': int(fp), 'fn': int(fn), 'tp': int(tp)},
    }
    if len(set(y_true.tolist())) == 2:
        metrics['auc'] = float(roc_auc_score(y_true, y_prob))
        metrics['average_precision'] = float(average_precision_score(y_true, y_prob))
    else:
        metrics['auc'] = 0.0
        metrics['average_precision'] = 0.0
    return metrics


def choose_threshold(y_true: np.ndarray, y_prob: np.ndarray, min_fake_recall: float) -> float:
    best_threshold = 0.35
    best_f1 = -1.0
    for threshold in np.linspace(0.15, 0.75, 121):
        current = metrics_for(y_true, y_prob, float(threshold))
        if current['recall'] < min_fake_recall:
            continue
        if current['f1'] > best_f1:
            best_f1 = current['f1']
            best_threshold = float(threshold)
    return best_threshold


def train_learning_curve(
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_val: np.ndarray,
    y_val: np.ndarray,
    sizes: list[int],
    seed: int,
) -> tuple[SGDClassifier, list[dict[str, Any]]]:
    rng = np.random.default_rng(seed)
    classes = np.asarray([0, 1], dtype=np.int64)
    curve: list[dict[str, Any]] = []
    best_model: SGDClassifier | None = None
    best_f1 = -1.0

    for size in sizes:
        model = SGDClassifier(
            loss='log_loss',
            alpha=0.0005,
            penalty='l2',
            class_weight={0: 1.0, 1: 1.8},
            max_iter=1,
            tol=None,
            random_state=seed,
            learning_rate='optimal',
        )
        indices = np.arange(len(x_train))
        for epoch in range(1, 9):
            chosen = rng.choice(indices, size=min(size, len(indices)), replace=False)
            rng.shuffle(chosen)
            model.partial_fit(x_train[chosen], y_train[chosen], classes=classes)
            val_prob = model.predict_proba(x_val)[:, 1]
            threshold = choose_threshold(y_val, val_prob, min_fake_recall=0.90)
            val_metrics = metrics_for(y_val, val_prob, threshold)
            val_metrics.update({'train_samples': int(len(chosen)), 'epoch': epoch})
            curve.append(val_metrics)
            if val_metrics['f1'] > best_f1:
                best_f1 = val_metrics['f1']
                best_model = model

    if best_model is None:
        raise RuntimeError('Training failed to produce a calibrator.')
    return best_model, curve


def main() -> int:
    parser = argparse.ArgumentParser(description='Train free local image calibrator.')
    parser.add_argument('--manifest', default='training/manifests/image_manifest.csv')
    parser.add_argument('--hard-root', default='data/hard_examples/image')
    parser.add_argument('--output', default='models/local_image_calibrator.json')
    parser.add_argument('--report', default='training/artifacts/local_image_calibrator_report.json')
    parser.add_argument('--max-train-per-class', type=int, default=450)
    parser.add_argument('--max-val-per-class', type=int, default=180)
    parser.add_argument('--max-hard-per-class', type=int, default=150)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--min-fake-recall', type=float, default=0.90)
    args = parser.parse_args()

    train_rows = load_rows(Path(args.manifest), 'train', args.max_train_per_class, args.seed)
    val_rows = load_rows(Path(args.manifest), 'val', args.max_val_per_class, args.seed + 1)
    hard_eval_rows = hard_rows(Path(args.hard_root), args.max_hard_per_class, args.seed + 2)

    x_train_raw, y_train, _ = extract_matrix(train_rows)
    x_val_raw, y_val, _ = extract_matrix(val_rows)
    x_hard_raw, y_hard, hard_paths = extract_matrix(hard_eval_rows)
    if x_train_raw.size == 0 or x_val_raw.size == 0:
        raise RuntimeError('Not enough image samples to train/evaluate local calibrator.')

    scaler = StandardScaler()
    x_train = scaler.fit_transform(x_train_raw)
    x_val = scaler.transform(x_val_raw)
    x_hard = scaler.transform(x_hard_raw) if x_hard_raw.size else np.empty((0, x_train.shape[1]))

    sizes = [64, 128, 256, min(512, len(x_train)), len(x_train)]
    sizes = sorted(set(size for size in sizes if size > 1))
    model, curve = train_learning_curve(x_train, y_train, x_val, y_val, sizes, args.seed)

    val_prob = model.predict_proba(x_val)[:, 1]
    threshold = choose_threshold(y_val, val_prob, args.min_fake_recall)
    val_metrics = metrics_for(y_val, val_prob, threshold)

    hard_metrics: dict[str, Any] = {}
    hard_misclassified: list[dict[str, Any]] = []
    if x_hard.size:
        hard_prob = model.predict_proba(x_hard)[:, 1]
        hard_metrics = metrics_for(y_hard, hard_prob, threshold)
        hard_pred = (hard_prob >= threshold).astype(np.int64)
        for path, label, pred, prob in zip(hard_paths, y_hard.tolist(), hard_pred.tolist(), hard_prob.tolist()):
            if label != pred:
                hard_misclassified.append(
                    {
                        'path': path,
                        'label': int(label),
                        'predicted': int(pred),
                        'fake_probability': round(float(prob), 6),
                    }
                )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        'version': 1,
        'kind': 'local_image_forensic_logistic_calibrator',
        'threshold': threshold,
        'feature_means': scaler.mean_.astype(float).tolist(),
        'feature_scales': scaler.scale_.astype(float).tolist(),
        'weights': model.coef_[0].astype(float).tolist(),
        'bias': float(model.intercept_[0]),
        'train_counts': dict(Counter(y_train.tolist())),
        'val_counts': dict(Counter(y_val.tolist())),
    }
    output_path.write_text(json.dumps(payload, indent=2), encoding='utf-8')

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report = {
        'calibrator_path': str(output_path),
        'threshold': threshold,
        'val_metrics': val_metrics,
        'hard_metrics': hard_metrics,
        'learning_curve': curve,
        'hard_misclassified': hard_misclassified[:100],
        'sample_counts': {
            'train': int(len(y_train)),
            'val': int(len(y_val)),
            'hard': int(len(y_hard)),
        },
    }
    report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
