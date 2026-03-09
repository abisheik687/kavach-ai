# training/README_TRAINING.md
# KAVACH-AI Model Training Guide

## Prerequisites

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| Python      | 3.10    | 3.11        |
| PyTorch     | 2.1.0   | 2.3.0       |
| CUDA        | 11.8    | 12.1        |
| GPU VRAM    | 8 GB    | 16 GB       |
| RAM         | 16 GB   | 32 GB       |
| Disk        | 50 GB   | 200 GB      |

> CPU-only training is supported but very slow (10-20x slower than GPU).
> Reduce batch_size to 8 and expect 20–40 hours per model on CPU.

## 1. Install Dependencies

```bash
# Use Python 3.11 (avoids numpy wheel issues on 3.14)
# Windows: install from python.org/downloads/release/python-3119/
# Linux/macOS: pyenv install 3.11.9

pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
pip install transformers timm scikit-learn tensorboard pyyaml onnx onnxruntime-gpu
pip install facenet-pytorch opencv-python-headless tqdm Pillow

# Optional: WandB for experiment tracking
pip install wandb
```

## 2. Prepare Dataset

```bash
# Extract faces from raw data
python training/data_pipeline.py \
  --input_dir  data/raw/CelebDF_v2/fake --output_dir data/processed/fake --label 1
python training/data_pipeline.py \
  --input_dir  data/raw/CelebDF_v2/real --output_dir data/processed/real --label 0

# Build manifest
python training/build_manifest.py \
  --real_dir data/processed/real \
  --fake_dir data/processed/fake \
  --output   training/dataset_manifest.csv

# Verify dataset
python training/dataset.py training/dataset_manifest.csv
```

## 3. Run Training

```bash
# Single model
./training/train.sh --model vit_primary

# With overrides
./training/train.sh --model efficientnet --epochs 20 --batch_size 16

# All models sequentially (takes 12–24 hours on a single GPU)
./training/train.sh --model all

# Direct Python (Windows)
python training/train.py --model vit_primary
```

## 4. Monitor Training

```bash
# TensorBoard
tensorboard --logdir training/logs
# Open: http://localhost:6006

# WandB (optional — set API key first)
export WANDB_API_KEY=your_key_here
# Set wandb_enabled: true in model_config.yaml
```

## 5. Evaluate a Checkpoint

```bash
# Results are auto-saved to:
#   training/checkpoints/<model_name>/<model_name>_test_results.json

cat training/checkpoints/vit_primary/vit_primary_test_results.json

# Expected output format:
# {
#   "test": {"loss": 0.08, "accuracy": 0.963, "auc": 0.987, "f1": 0.962},
#   "best_val_auc": 0.985,
#   "model": "vit_primary"
# }
```

## 6. ONNX Export

ONNX is exported automatically at the end of each training run.
Find it at: `training/checkpoints/<model_name>/<model_name>.onnx`

To export manually from a checkpoint:
```bash
python - <<'EOF'
import torch, yaml
from training.train import load_model, export_onnx
from pathlib import Path

with open('training/model_config.yaml') as f:
    cfg = {**yaml.safe_load(f)['shared'], **yaml.safe_load(f)['vit_primary']}

model = load_model(cfg, num_classes=2, device='cpu')
ckpt  = torch.load('training/checkpoints/vit_primary/vit_primary_best_auc0.9870.pt',
                   map_location='cpu')
model.load_state_dict(ckpt['model_state'])
export_onnx(model, cfg, Path('training/checkpoints/vit_primary/vit_primary.onnx'), 'cpu')
EOF
```

## 7. Load Trained Weights into KAVACH-AI

After training, point the backend to your local checkpoints via `.env`:

```bash
# .env
KAVACH_MODEL_PRIMARY_PATH=training/checkpoints/vit_primary/vit_primary.onnx
KAVACH_MODEL_SECONDARY_PATH=training/checkpoints/vit_secondary/vit_secondary.onnx
KAVACH_MODEL_EFFICIENTNET_PATH=training/checkpoints/efficientnet_b4/efficientnet_b4.onnx
KAVACH_MODEL_XCEPTION_PATH=training/checkpoints/xception/xception.onnx
```

Then restart the backend: `uvicorn backend.main:app --reload`
The /health endpoint will confirm models are loaded: `GET /health`

## 8. Expected Training Results

| Model | Val AUC Target | Test AUC Target | Train Time (RTX 3090) |
|-------|---------------|-----------------|----------------------|
| vit_primary    | 0.97–0.99 | 0.97–0.99 | 2–4 hrs |
| vit_secondary  | 0.95–0.97 | 0.95–0.97 | 2–3 hrs |
| efficientnet_b4| 0.93–0.96 | 0.93–0.96 | 3–5 hrs |
| xception       | 0.92–0.95 | 0.92–0.95 | 3–6 hrs |
| convnext_base  | 0.95–0.97 | 0.95–0.97 | 4–6 hrs |
| **Ensemble**   | —         | **0.985+**| — |

## 9. Troubleshooting

| Issue | Fix |
|-------|-----|
| CUDA OOM | Reduce batch_size to 8 or 16 in model_config.yaml |
| numpy build error (Windows/Python 3.14) | Use Python 3.11 |
| facenet-pytorch install fails | pip install facenet-pytorch --no-build-isolation |
| AUC stuck at ~0.5 | Check class balance in manifest — run build_manifest.py |
| ONNX export fails | pip install onnx onnxruntime; retry export manually |
| HF model 403 error | Model may require auth: huggingface-cli login |
