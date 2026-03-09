#!/usr/bin/env bash
# training/train.sh
# KAVACH-AI one-command training launcher
# Usage:
#   ./training/train.sh --model vit_primary
#   ./training/train.sh --model all
#   ./training/train.sh --model efficientnet --epochs 20 --batch_size 16

set -euo pipefail

# ── Defaults ──────────────────────────────────────────────────────
MODEL=""
EXTRA_ARGS=""
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# ── Parse arguments ───────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case $1 in
    --model) MODEL="$2"; shift 2 ;;
    *)       EXTRA_ARGS="$EXTRA_ARGS $1 $2"; shift 2 ;;
  esac
done

if [[ -z "$MODEL" ]]; then
  echo "ERROR: --model is required"
  echo "Usage: $0 --model <vit_primary|vit_secondary|efficientnet|xception|convnext|all>"
  exit 1
fi

# ── Environment setup ─────────────────────────────────────────────
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# Activate virtualenv if present
VENV_PATHS=("$PROJECT_ROOT/.venv" "$PROJECT_ROOT/venv" "$PROJECT_ROOT/env")
for venv in "${VENV_PATHS[@]}"; do
  if [[ -f "$venv/bin/activate" ]]; then
    echo "Activating virtualenv: $venv"
    source "$venv/bin/activate"
    break
  elif [[ -f "$venv/Scripts/activate" ]]; then  # Windows
    echo "Activating virtualenv (Windows): $venv"
    source "$venv/Scripts/activate"
    break
  fi
done

# ── GPU info ──────────────────────────────────────────────────────
echo ""
echo "=== KAVACH-AI Training Launcher ==="
echo "Model:   $MODEL"
python -c "import torch; print(f'PyTorch: {torch.__version__}  CUDA: {torch.cuda.is_available()}  Device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"CPU\"}')"
echo ""

# ── Training function ─────────────────────────────────────────────
run_model() {
  local m="$1"
  echo ">>> Starting training: $m"
  echo "    $(date)"
  python training/train.py --model "$m" $EXTRA_ARGS
  echo ">>> Completed: $m  $(date)"
  echo ""
}

# ── Execute ───────────────────────────────────────────────────────
if [[ "$MODEL" == "all" ]]; then
  echo "Running all models sequentially..."
  for m in vit_primary vit_secondary efficientnet xception convnext; do
    run_model "$m"
  done
  echo "All training runs complete."
else
  run_model "$MODEL"
fi
