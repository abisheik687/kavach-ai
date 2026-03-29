# KAVACH-AI Multimodal Training Guide

The new local training pipeline lives in:

- `training/multimodal_pipeline.py`
- `training/train_multimodal.py`
- `training/runtime_models.py`
- `training/multimodal_config.yaml`

It supports:

- Image datasets: FaceForensics++, Celeb-DF, DFDC
- Video datasets: FaceForensics++, Celeb-DF, DFDC, FakeAVCeleb
- Audio datasets: ASVspoof, FakeAVCeleb

## Install

```bash
pip install -r training/requirements.txt
```

## Configure local dataset paths

Update `training/multimodal_config.yaml` so each dataset points at your local copy.

## Run

```bash
python training/train_multimodal.py --modality image
python training/train_multimodal.py --modality audio
python training/train_multimodal.py --modality video
python training/train_multimodal.py --modality all
```

## Artifact format

Each run writes a self-describing artifact folder:

```text
training/artifacts/<modality>/<run>/
  model.pt
  metadata.json
  model.onnx
  manifest.csv
  history.json
  misclassified.json
  report.json
```

`metadata.json` is what the backend consumes for local trained-model inference.

## Backend integration

Set one or more of these environment variables:

```bash
MODEL_IMAGE_ARTIFACT_MANIFEST=training/artifacts/image/<run>/metadata.json
MODEL_AUDIO_ARTIFACT_MANIFEST=training/artifacts/audio/<run>/metadata.json
MODEL_VIDEO_ARTIFACT_MANIFEST=training/artifacts/video/<run>/metadata.json
```

The backend will prefer those local trained artifacts over the default open-source model path.

## Training strategy

- Strict group-based splitting to reduce leakage
- Balanced train sampling
- Compression, blur, color, noise, and resolution perturbation
- Cross-dataset reporting on held-out test rows
- Misclassification export for periodic retraining
