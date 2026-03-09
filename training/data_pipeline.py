"""
KAVACH-AI Training Data Pipeline — Step 1: Face Extraction
===========================================================
Extracts aligned face crops from raw video/image datasets.
Uses MTCNN (facenet-pytorch) to match the backend detection stack.

Usage:
  python training/data_pipeline.py \
    --input_dir  data/raw/FaceForensics/manipulated_sequences \
    --output_dir data/processed/fake \
    --label      1 \
    --max_faces  5

  python training/data_pipeline.py \
    --input_dir  data/raw/FaceForensics/original_sequences \
    --output_dir data/processed/real \
    --label      0
"""
import argparse
import hashlib
import logging
import os
import sys
from pathlib import Path
from typing import Generator

import cv2
import numpy as np
from PIL import Image
from facenet_pytorch import MTCNN
import torch
from tqdm import tqdm

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout),
              logging.FileHandler('training/logs/data_pipeline.log')],
)
log = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────
FACE_SIZE        = 224          # output crop size (px)
MIN_CONFIDENCE   = 0.90         # reject detections below this
SUPPORTED_VIDEO  = {'.mp4', '.avi', '.mov', '.webm', '.mkv'}
SUPPORTED_IMAGE  = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
FRAME_INTERVAL   = 10           # extract every Nth frame from video


def _get_mtcnn(device: str) -> MTCNN:
    return MTCNN(
        image_size=FACE_SIZE,
        margin=20,
        min_face_size=60,
        thresholds=[0.6, 0.7, MIN_CONFIDENCE],
        factor=0.709,
        post_process=False,  # return raw pixels, not normalised tensor
        keep_all=True,       # detect all faces in frame
        device=device,
    )


def _file_hash(path: Path) -> str:
    """MD5 of first 64KB — fast duplicate detection."""
    h = hashlib.md5()
    with open(path, 'rb') as f:
        h.update(f.read(65536))
    return h.hexdigest()[:12]


def iter_frames(path: Path) -> Generator[np.ndarray, None, None]:
    """Yield BGR frames from a video file at FRAME_INTERVAL cadence."""
    cap = cv2.VideoCapture(str(path))
    frame_idx = 0
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if frame_idx % FRAME_INTERVAL == 0:
                yield frame
            frame_idx += 1
    finally:
        cap.release()


def extract_faces_from_image(
    img_bgr: np.ndarray,
    mtcnn: MTCNN,
) -> list[Image.Image]:
    """
    Detect and align faces in a single BGR image.
    Returns list of PIL FACE_SIZE×FACE_SIZE RGB crops.
    """
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(img_rgb)

    try:
        boxes, probs, landmarks = mtcnn.detect(pil_img, landmarks=True)
    except Exception as e:
        log.debug(f'MTCNN detect error: {e}')
        return []

    if boxes is None:
        return []

    faces = []
    for box, prob, lm in zip(boxes, probs, landmarks):
        if prob < MIN_CONFIDENCE:
            continue
        # Align using 5-point landmarks (eyes → horizontal)
        try:
            face = _align_face(img_rgb, lm)
            if face is not None:
                faces.append(face)
        except Exception:
            # Fall back to simple crop if alignment fails
            x1,y1,x2,y2 = [int(v) for v in box]
            crop = img_rgb[max(0,y1):y2, max(0,x1):x2]
            if crop.size > 0:
                pil_crop = Image.fromarray(crop).resize(
                    (FACE_SIZE, FACE_SIZE), Image.LANCZOS)
                faces.append(pil_crop)
    return faces


def _align_face(img_rgb: np.ndarray, landmarks: np.ndarray) -> Image.Image | None:
    """
    Affine-align face so both eyes are horizontal.
    landmarks shape: (5, 2) — [left_eye, right_eye, nose, mouth_l, mouth_r]
    """
    if landmarks is None or landmarks.shape != (5, 2):
        return None

    left_eye  = landmarks[0]
    right_eye = landmarks[1]

    dx = right_eye[0] - left_eye[0]
    dy = right_eye[1] - left_eye[1]
    angle = float(np.degrees(np.arctan2(dy, dx)))

    eye_center = ((left_eye[0] + right_eye[0]) / 2,
                  (left_eye[1] + right_eye[1]) / 2)

    M = cv2.getRotationMatrix2D(eye_center, angle, scale=1.0)
    rotated = cv2.warpAffine(
        img_rgb, M, (img_rgb.shape[1], img_rgb.shape[0]),
        flags=cv2.INTER_LINEAR,
    )

    # Redetect face in aligned image for clean crop
    h, w = rotated.shape[:2]
    cx, cy = int(eye_center[0]), int(eye_center[1])
    half = FACE_SIZE // 2 + 20
    x1 = max(0, cx - half)
    y1 = max(0, cy - half + 10)  # shift down slightly to include chin
    x2 = min(w, cx + half)
    y2 = min(h, cy + half + 30)

    crop = rotated[y1:y2, x1:x2]
    if crop.size == 0:
        return None
    return Image.fromarray(crop).resize((FACE_SIZE, FACE_SIZE), Image.LANCZOS)


def process_directory(
    input_dir: Path,
    output_dir: Path,
    label: int,
    max_faces_per_source: int,
    device: str,
) -> dict:
    """
    Walk input_dir recursively, extract faces from every video/image.
    Save as PNG to output_dir/label_{0|1}/.
    Returns extraction stats dict.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    mtcnn   = _get_mtcnn(device)
    seen_hashes: set[str] = set()

    stats = {'processed':0, 'faces_saved':0, 'duplicates':0,
             'low_conf':0, 'errors':0, 'skipped':0}

    all_files = sorted([
        p for p in input_dir.rglob('*')
        if p.suffix.lower() in SUPPORTED_VIDEO | SUPPORTED_IMAGE
    ])

    log.info(f'Found {len(all_files)} source files in {input_dir}')

    for src_path in tqdm(all_files, desc=f'Extracting (label={label})'):
        face_count = 0
        try:
            if src_path.suffix.lower() in SUPPORTED_VIDEO:
                frames = iter_frames(src_path)
            else:
                img = cv2.imread(str(src_path))
                if img is None:
                    stats['errors'] += 1; continue
                frames = [img]

            for frame in frames:
                if face_count >= max_faces_per_source:
                    break
                faces = extract_faces_from_image(frame, mtcnn)
                for face_pil in faces:
                    if face_count >= max_faces_per_source:
                        break
                    # Duplicate check
                    face_arr = np.array(face_pil)
                    fhash = hashlib.md5(face_arr.tobytes()).hexdigest()[:12]
                    if fhash in seen_hashes:
                        stats['duplicates'] += 1; continue
                    seen_hashes.add(fhash)

                    out_name = f'{src_path.stem}_{fhash}.png'
                    face_pil.save(output_dir / out_name, 'PNG', optimize=False)
                    face_count += 1
                    stats['faces_saved'] += 1

            stats['processed'] += 1

        except Exception as e:
            log.warning(f'Error processing {src_path.name}: {e}')
            stats['errors'] += 1

    log.info(f'Extraction complete: {stats}')
    return stats


def main():
    parser = argparse.ArgumentParser(description='KAVACH-AI Face Extractor')
    parser.add_argument('--input_dir',  required=True, type=Path)
    parser.add_argument('--output_dir', required=True, type=Path)
    parser.add_argument('--label',      required=True, type=int, choices=[0,1])
    parser.add_argument('--max_faces',  default=10,    type=int,
                        help='Max face crops to save per source file')
    parser.add_argument('--device',     default='auto',
                        choices=['auto','cpu','cuda'],
                        help='Inference device for MTCNN')
    args = parser.parse_args()

    device = args.device
    if device == 'auto':
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
    log.info(f'Using device: {device}')

    os.makedirs('training/logs', exist_ok=True)
    stats = process_directory(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        label=args.label,
        max_faces_per_source=args.max_faces,
        device=device,
    )

    print('\n=== Extraction Summary ===')
    for k,v in stats.items():
        print(f'  {k:<20}: {v}')


if __name__ == '__main__':
    main()
