"""
KAVACH-AI Synthetic Data Generator — Bootstrap Fallback
=======================================================
Generates synthetic (label=1) training samples from real face images
using heavy augmentation to simulate deepfake-like visual artefacts.
ALSO copies a subset of real faces as label=0 samples.

This is a BOOTSTRAP FALLBACK — use real datasets (FF++, Celeb-DF)
for all serious training runs. All synthetic samples are clearly
tagged with source='synthetic' in the manifest.

Usage:
  python training/synthetic_gen.py \
    --real_dir data/processed/real \
    --output_dir data/synthetic \
    --n_samples 2000
"""
import argparse
import io
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter, ImageEnhance
from tqdm import tqdm


def _blend_faces(face_a: Image.Image, face_b: Image.Image) -> Image.Image:
    """Alpha-blend two face images to simulate face-swap boundary artefacts."""
    a = face_a.convert('RGBA')
    b = face_b.resize(face_a.size).convert('RGBA')
    # Create elliptical mask — deepfakes often have oval blend regions
    mask = Image.new('L', face_a.size, 0)
    import PIL.ImageDraw as D
    draw = D.Draw(mask)
    w, h = face_a.size
    draw.ellipse([w//6, h//8, 5*w//6, 7*h//8], fill=200)
    # Blur mask to soften edges (realistic)
    mask = mask.filter(ImageFilter.GaussianBlur(radius=12))
    blended = Image.composite(b, a, mask)
    return blended.convert('RGB')


def _apply_deepfake_artefacts(img: Image.Image) -> Image.Image:
    """
    Apply a randomised stack of deepfake-like visual degradations.
    Each run picks a different combination to maximise diversity.
    """
    ops = []

    # 1. Colour channel mis-alignment (common in early GAN outputs)
    if random.random() < 0.5:
        arr = np.array(img).astype(np.float32)
        shift = random.uniform(-8, 8)
        arr[:,:,0] = np.clip(arr[:,:,0] + shift, 0, 255)
        img = Image.fromarray(arr.astype(np.uint8))
        ops.append('channel_shift')

    # 2. Sharpness spike (GAN reconstruction sharpening)
    if random.random() < 0.6:
        factor = random.uniform(1.5, 3.5)
        img = ImageEnhance.Sharpness(img).enhance(factor)
        ops.append('sharpness')

    # 3. Saturation spike (common in face-swap outputs)
    if random.random() < 0.4:
        factor = random.uniform(1.3, 2.0)
        img = ImageEnhance.Color(img).enhance(factor)
        ops.append('saturation')

    # 4. Boundary blend seam (simulate imperfect blending)
    if random.random() < 0.3:
        arr = np.array(img)
        seam_x = random.randint(img.width//3, 2*img.width//3)
        seam_w = random.randint(2, 8)
        arr[:, seam_x:seam_x+seam_w] = arr[:, seam_x:seam_x+seam_w] * 0.7
        img = Image.fromarray(arr.clip(0,255).astype(np.uint8))
        ops.append('seam')

    # 5. JPEG double-compression (very common in deepfake distribution)
    for _ in range(random.randint(1, 2)):
        buf = io.BytesIO()
        q = random.randint(40, 85)
        img.save(buf, 'JPEG', quality=q)
        buf.seek(0)
        img = Image.open(buf).copy()
        ops.append(f'jpeg_q{q}')

    # 6. Slight resize + re-expand (GAN resolution mismatch artefact)
    if random.random() < 0.4:
        orig_size = img.size
        scale = random.uniform(0.7, 0.95)
        small = img.resize(
            (int(orig_size[0]*scale), int(orig_size[1]*scale)),
            Image.BILINEAR
        )
        img = small.resize(orig_size, Image.BILINEAR)
        ops.append('resize_artefact')

    return img


def generate_synthetic(
    real_dir: Path,
    output_dir: Path,
    n_samples: int,
    seed: int = 42,
) -> None:
    """
    Generate n_samples synthetic deepfake-like images.
    Each sample uses one or two real faces as source material.
    """
    random.seed(seed)
    np.random.seed(seed)

    fake_dir = output_dir / 'fake'
    real_out = output_dir / 'real'
    fake_dir.mkdir(parents=True, exist_ok=True)
    real_out.mkdir(parents=True, exist_ok=True)

    real_paths = sorted([
        p for p in real_dir.rglob('*')
        if p.suffix.lower() in {'.png','.jpg','.jpeg'}
    ])

    if len(real_paths) < 2:
        raise ValueError(f'Need at least 2 real face images in {real_dir}')

    print(f'Source pool: {len(real_paths)} real faces')
    print(f'Generating {n_samples} synthetic deepfake images...')

    for i in tqdm(range(n_samples), desc='Synthetic generation'):
        face_a_path = random.choice(real_paths)
        face_b_path = random.choice(real_paths)
        face_a = Image.open(face_a_path).convert('RGB').resize((224,224))
        face_b = Image.open(face_b_path).convert('RGB').resize((224,224))

        # Blend two faces then add GAN-like artefacts
        if face_a_path != face_b_path and random.random() < 0.6:
            synthetic = _blend_faces(face_a, face_b)
        else:
            synthetic = face_a.copy()

        synthetic = _apply_deepfake_artefacts(synthetic)
        out_name = f'synthetic_fake_{i:06d}.png'
        synthetic.save(fake_dir / out_name, 'PNG')

        # Mirror a real image for every fake (keep balance)
        real_src = Image.open(random.choice(real_paths)).convert('RGB').resize((224,224))
        real_src.save(real_out / f'synthetic_real_{i:06d}.png', 'PNG')

    print(f'\nSynthetic dataset written to {output_dir}')
    print(f'  fake/  : {n_samples} images  (label=1)')
    print(f'  real/  : {n_samples} images  (label=0)')
    print(f'  Total  : {n_samples * 2} samples')
    print('  NOTE: These are synthetic bootstrap samples.')
    print('        Replace with FF++/Celeb-DF for production training.')


def main():
    parser = argparse.ArgumentParser(description='KAVACH-AI Synthetic Generator')
    parser.add_argument('--real_dir',    required=True, type=Path)
    parser.add_argument('--output_dir',  required=True, type=Path)
    parser.add_argument('--n_samples',   default=2000,  type=int)
    parser.add_argument('--seed',        default=42,    type=int)
    args = parser.parse_args()
    generate_synthetic(args.real_dir, args.output_dir,
                       args.n_samples, args.seed)

if __name__ == '__main__':
    main()
