"""
KAVACH-AI — Synthetic Dataset Generator
========================================
Generates a fully-labelled synthetic dataset with the exact directory structure
expected by training/multimodal_config.yaml.

Usage (from project root):
    python training/datasets/generate_synthetic.py

Directory structure created:
    data/
      image/
        faceforensics_pp/{real,fake}/subject{0-9}_frame{0-7}.png
        celeb_df/{real,fake}/subject{0-9}_frame{0-7}.png
        dfdc/{real,fake}/subject{0-9}_frame{0-7}.png
      audio/
        asvspoof/{real,fake}/subject{0-9}_utt{0-3}.wav
        fakeavceleb/{real,fake}/subject{0-9}_utt{0-3}.wav
      video/
        faceforensics_pp/{real,fake}/subject{0-7}_clip{0-2}.avi
        dfdc/{real,fake}/subject{0-7}_clip{0-2}.avi

Labels are determined purely by directory name (real/ vs fake/) as expected
by training/multimodal_pipeline.py:infer_label_from_path().

Group IDs are inferred from the filename stem prefix before the first '_',
so each subjectN_ prefix forms a distinct group enabling GroupShuffleSplit.
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

import cv2
import numpy as np

# Allow running as a script from project root
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


# ─── Constants ────────────────────────────────────────────────────────────────

NUM_SUBJECTS = 10       # distinct identity groups per class per dataset
FRAMES_PER_SUBJECT = 8  # image samples per subject
UTTS_PER_SUBJECT = 4    # audio files per subject
CLIPS_PER_SUBJECT = 3   # video files per subject

IMAGE_SIZE = 64    # px — small for fast I/O; pipeline resizes anyway
AUDIO_SR = 16000   # Hz
AUDIO_SECONDS = 4  # seconds per utterance
VIDEO_FRAMES = 60  # frames per clip  (at 10fps ≈ 6s)
VIDEO_FPS = 10
VIDEO_H = 64
VIDEO_W = 64

RANDOM_SEED = 42
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)


# ─── Image generation ────────────────────────────────────────────────────────

def _make_face_image(subject_id: int, is_fake: bool) -> np.ndarray:
    """Generate a plausible synthetic face-like image (H×W×3, uint8)."""
    rng = np.random.default_rng(subject_id * 100 + int(is_fake) * 50)
    img = np.zeros((IMAGE_SIZE, IMAGE_SIZE, 3), dtype=np.uint8)

    # Skin-tone background (slightly different per subject)
    r_base = 180 + (subject_id * 5) % 60
    g_base = 120 + (subject_id * 7) % 60
    b_base = 80 + (subject_id * 11) % 50
    img[:, :] = [b_base, g_base, r_base]

    # Oval 'face' region
    cx, cy = IMAGE_SIZE // 2, IMAGE_SIZE // 2
    for y in range(IMAGE_SIZE):
        for x in range(IMAGE_SIZE):
            if ((x - cx) ** 2) / (cx * 0.7) ** 2 + ((y - cy) ** 2) / (cy * 0.85) ** 2 <= 1:
                img[y, x] = [b_base + 20, g_base + 15, r_base + 10]

    # Add noise that differs between real and fake
    if is_fake:
        # Fake images: add structured GAN-like grid artefact
        for i in range(0, IMAGE_SIZE, 8):
            img[i, :] = np.clip(img[i, :].astype(int) - 15, 0, 255).astype(np.uint8)
        noise = rng.integers(0, 20, size=(IMAGE_SIZE, IMAGE_SIZE, 3), dtype=np.uint8)
    else:
        noise = rng.integers(0, 8, size=(IMAGE_SIZE, IMAGE_SIZE, 3), dtype=np.uint8)

    img = np.clip(img.astype(int) + noise.astype(int), 0, 255).astype(np.uint8)
    return img


def generate_image_dataset(base_path: Path, dataset_name: str) -> int:
    """Write PNG images to base_path/real/ and base_path/fake/."""
    total = 0
    for label, is_fake in [('real', False), ('fake', True)]:
        out_dir = base_path / label
        out_dir.mkdir(parents=True, exist_ok=True)
        for subject_id in range(NUM_SUBJECTS):
            for frame_idx in range(FRAMES_PER_SUBJECT):
                img = _make_face_image(subject_id, is_fake)
                # Add per-frame jitter so images aren't identical
                jitter = np.random.randint(-5, 5, img.shape, dtype=np.int16)
                img = np.clip(img.astype(np.int16) + jitter, 0, 255).astype(np.uint8)
                filename = f'subject{subject_id}_frame{frame_idx:03d}.png'
                cv2.imwrite(str(out_dir / filename), img)
                total += 1
    print(f'  [image/{dataset_name}] {total} images written')
    return total


# ─── Audio generation ────────────────────────────────────────────────────────

def _make_speech_waveform(subject_id: int, is_fake: bool, utt_idx: int) -> np.ndarray:
    """Generate a plausible speech-like waveform (float32 mono)."""
    rng = np.random.default_rng(subject_id * 200 + utt_idx * 10 + int(is_fake) * 100)
    t = np.linspace(0, AUDIO_SECONDS, AUDIO_SR * AUDIO_SECONDS, dtype=np.float32)

    # Each subject has a unique fundamental frequency
    f0 = 90 + subject_id * 18  # Hz — simulates different voices
    harmonics = [f0 * k for k in range(1, 6)]

    wave = np.zeros_like(t)
    for k, freq in enumerate(harmonics):
        amp = 1.0 / (k + 1)
        phase = rng.uniform(0, 2 * np.pi)
        wave += amp * np.sin(2 * np.pi * freq * t + phase)

    # Fake voices: add a subtle synthetic artefact (slight phase discontinuity)
    if is_fake:
        wave += 0.05 * np.sin(2 * np.pi * 4000 * t)  # high-freq GAN hiss
        noise_scale = 0.02
    else:
        noise_scale = 0.005

    noise = rng.normal(0, noise_scale, size=t.shape).astype(np.float32)
    wave = wave + noise

    # Normalize to [-0.95, 0.95]
    peak = np.max(np.abs(wave))
    if peak > 1e-6:
        wave = wave / peak * 0.95

    return wave.astype(np.float32)


def generate_audio_dataset(base_path: Path, dataset_name: str) -> int:
    """Write WAV files to base_path/real/ and base_path/fake/."""
    import soundfile as sf

    total = 0
    for label, is_fake in [('real', False), ('fake', True)]:
        out_dir = base_path / label
        out_dir.mkdir(parents=True, exist_ok=True)
        for subject_id in range(NUM_SUBJECTS):
            for utt_idx in range(UTTS_PER_SUBJECT):
                wave = _make_speech_waveform(subject_id, is_fake, utt_idx)
                filename = f'subject{subject_id}_utt{utt_idx:02d}.wav'
                sf.write(str(out_dir / filename), wave, AUDIO_SR, subtype='PCM_16')
                total += 1
    print(f'  [audio/{dataset_name}] {total} WAV files written')
    return total


# ─── Video generation ────────────────────────────────────────────────────────

def _write_video(path: Path, subject_id: int, is_fake: bool, clip_idx: int) -> None:
    """Write an AVI video file with synthetic face-like frames."""
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    writer = cv2.VideoWriter(str(path), fourcc, VIDEO_FPS, (VIDEO_W, VIDEO_H))
    rng = np.random.default_rng(subject_id * 300 + clip_idx * 10 + int(is_fake) * 150)

    for frame_idx in range(VIDEO_FRAMES):
        img = _make_face_image(subject_id, is_fake)
        img = cv2.resize(img, (VIDEO_W, VIDEO_H))
        # Add subtle temporal variation (motion)
        shift_x = int(rng.integers(-2, 3))
        shift_y = int(rng.integers(-2, 3))
        M = np.float32([[1, 0, shift_x], [0, 1, shift_y]])
        img = cv2.warpAffine(img, M, (VIDEO_W, VIDEO_H))
        writer.write(img)

    writer.release()


def generate_video_dataset(base_path: Path, dataset_name: str) -> int:
    """Write AVI videos to base_path/real/ and base_path/fake/."""
    total = 0
    num_video_subjects = 8  # fewer subjects for faster video generation
    for label, is_fake in [('real', False), ('fake', True)]:
        out_dir = base_path / label
        out_dir.mkdir(parents=True, exist_ok=True)
        for subject_id in range(num_video_subjects):
            for clip_idx in range(CLIPS_PER_SUBJECT):
                filename = f'subject{subject_id}_clip{clip_idx:02d}.avi'
                _write_video(out_dir / filename, subject_id, is_fake, clip_idx)
                total += 1
    print(f'  [video/{dataset_name}] {total} videos written')
    return total


# ─── Main orchestration ──────────────────────────────────────────────────────

def generate_all(data_root: Path | None = None, force: bool = False) -> dict[str, int]:
    """Generate all synthetic datasets under `data_root` (default: project root / data).

    Args:
        data_root: Override the data root directory.
        force: If True, regenerate even if files already exist.

    Returns:
        Dictionary mapping dataset name to number of files generated.
    """
    if data_root is None:
        data_root = ROOT / 'data'

    print('=' * 60)
    print('KAVACH-AI Synthetic Dataset Generator')
    print('=' * 60)

    totals: dict[str, int] = {}

    # ── Image datasets ────────────────────────────────────────
    print('\n[IMAGE DATASETS]')
    for ds_name in ('faceforensics_pp', 'celeb_df', 'dfdc'):
        ds_path = data_root / 'image' / ds_name
        existing = list(ds_path.rglob('*.png')) if ds_path.exists() else []
        if existing and not force:
            print(f'  [image/{ds_name}] Skipping — {len(existing)} files already exist')
            totals[f'image/{ds_name}'] = len(existing)
        else:
            totals[f'image/{ds_name}'] = generate_image_dataset(ds_path, ds_name)

    # ── Audio datasets ────────────────────────────────────────
    print('\n[AUDIO DATASETS]')
    for ds_name in ('asvspoof', 'fakeavceleb'):
        ds_path = data_root / 'audio' / ds_name
        existing = list(ds_path.rglob('*.wav')) if ds_path.exists() else []
        if existing and not force:
            print(f'  [audio/{ds_name}] Skipping — {len(existing)} files already exist')
            totals[f'audio/{ds_name}'] = len(existing)
        else:
            totals[f'audio/{ds_name}'] = generate_audio_dataset(ds_path, ds_name)

    # ── Video datasets ────────────────────────────────────────
    print('\n[VIDEO DATASETS]')
    for ds_name in ('faceforensics_pp', 'dfdc'):
        ds_path = data_root / 'video' / ds_name
        existing = list(ds_path.rglob('*.avi')) if ds_path.exists() else []
        if existing and not force:
            print(f'  [video/{ds_name}] Skipping — {len(existing)} files already exist')
            totals[f'video/{ds_name}'] = len(existing)
        else:
            totals[f'video/{ds_name}'] = generate_video_dataset(ds_path, ds_name)

    # ── Summary ───────────────────────────────────────────────
    print('\n' + '=' * 60)
    print('GENERATION SUMMARY')
    print('=' * 60)
    grand_total = 0
    for name, count in sorted(totals.items()):
        print(f'  {name:<40} {count:>6} files')
        grand_total += count
    print(f'  {"TOTAL":<40} {grand_total:>6} files')
    print('=' * 60)
    print(f'\nData root: {data_root}')
    print('Ready for training. Run: python training/train_all.py\n')

    return totals


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Generate synthetic KAVACH-AI datasets')
    parser.add_argument('--data-root', type=Path, default=None, help='Override data root directory')
    parser.add_argument('--force', action='store_true', help='Regenerate existing files')
    args = parser.parse_args()

    generate_all(data_root=args.data_root, force=args.force)
