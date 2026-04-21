#!/bin/bash
<<<<<<< HEAD
# KAVACH-AI Ensemble Training Orchestrator
=======
# Multimodal Deepfake Detection System Using Advanced Machine Learning Techniques Ensemble Training Orchestrator
>>>>>>> 7df14d1 (UI enhanced)
# Trains the 5-model ensemble sequentially and exports to ONNX.

set -e

<<<<<<< HEAD
echo "🚀 Starting KAVACH-AI World-Class v2.0 Ensemble Training..."
=======
echo "🚀 Starting Multimodal Deepfake Detection System Using Advanced Machine Learning Techniques World-Class v2.0 Ensemble Training..."
>>>>>>> 7df14d1 (UI enhanced)

MODELS=("vit_primary" "vit_secondary" "efficientnet" "xception" "convnext" "wav2vec2_audio")
EPOCHS=${1:-30}  # Allow overriding epochs for smoke tests

for MODEL in "${MODELS[@]}"; do
    echo "----------------------------------------------------"
    echo "🏗️ Training Modality: $MODEL"
    echo "----------------------------------------------------"
    
    python training/train.py \
        --model "$MODEL" \
        --epochs "$EPOCHS" \
        --config training/model_config.yaml
        
    echo "✅ $MODEL training and ONNX export complete."
done

echo "===================================================="
echo "🎉 Full Ensemble Training Cycle Finished Successfully!"
echo "Checkpoints exported to: training/checkpoints/"
echo "===================================================="
