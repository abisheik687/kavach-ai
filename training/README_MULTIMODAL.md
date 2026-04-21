<<<<<<< HEAD
# KAVACH-AI Multimodal Training Guide
=======
# Multimodal Deepfake Detection System Using Advanced Machine Learning Techniques Multimodal Training Guide
>>>>>>> 7df14d1 (UI enhanced)

The new local training pipeline lives in:

- `training/multimodal_pipeline.py`
- `training/train_multimodal.py`
- `training/runtime_models.py`
- `training/multimodal_config.yaml`

It supports:

- Image datasets: FaceForensics++, Celeb-DF, DFDC
- Video datasets: FaceForensics++, Celeb-DF, DFDC, FakeAVCeleb
- Audio datasets: ASVspoof, FakeAVCeleb
- Submission-safe open-source backbones without importing third-party runtime repos
- Dataset auditing for corruption and class imbalance
- Multi-seed training orchestration through `training/train_all.py`

Recommended model choices for the deadline:

- Image: `convnext_base`
- Image alternative when compute allows: `swinv2_small_window16_256`
- Video: `r2plus1d_18`
- Audio: `audio_spectrogram_resnet18`
- Audio alternative: `audio_spectrogram_convnext_tiny`

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
python training/train_all.py --modality all --seeds 42 1337 2024
python training/select_best_model.py
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
  dataset_audit.json
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

## Runtime architecture policy

Keep the current app architecture intact:

- do use external datasets, pretrained initialization, and public model ideas
- do not embed full external repos like `DeepFake-Detect` into the live FastAPI backend
- keep `POST /analyse` and the current unified response contract unchanged

## Training strategy

- Strict group-based splitting to reduce leakage
- Balanced train sampling
- Compression, blur, color, noise, and resolution perturbation
- Cross-dataset reporting on held-out test rows
- Misclassification export for periodic retraining

## Recommended workflow

1. Populate the public datasets in `data/image`, `data/video`, and `data/audio`
2. Run `python training/train_all.py --modality all --seeds 42 1337 2024`
3. Review `training/artifacts/train_all_summary.json`
4. Promote the best `metadata.json` into the backend env vars
5. Re-run training for additional cycles after reviewing `misclassified.json`
