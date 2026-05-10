# Local Learning Curve and Calibration

KAVACH-AI is currently locked to free local inference only. To improve behavior without using Hugging Face credits, the project includes a lightweight local image calibrator:

```text
scripts/train_local_image_calibrator.py
```

## What It Does

The script learns from local dataset samples and hard examples. It extracts forensic image features and trains a small logistic calibrator that maps those features to fake probability.

It uses:

- JPEG artifact score
- frequency score
- color consistency score
- patch consistency score
- synthetic image score
- low-quality synthetic score
- saturation, texture, noise, edge density, and image-size features

The trained calibrator is saved to:

```text
models/local_image_calibrator.json
```

The backend loads this file automatically through:

```text
LOCAL_IMAGE_CALIBRATOR_PATH=../models/local_image_calibrator.json
```

## Important Runtime Rule

The calibrator can raise a fake probability, but it is not allowed to suppress a strong fake signal from the forensic fallback. This is deliberate because the main project problem is:

```text
fake media being classified as real
```

Current runtime behavior prioritizes fake recall over false-positive reduction.

## Run Command

```powershell
python scripts\train_local_image_calibrator.py --max-train-per-class 40 --max-val-per-class 20 --max-hard-per-class 20
```

For a larger run:

```powershell
python scripts\train_local_image_calibrator.py --max-train-per-class 180 --max-val-per-class 80 --max-hard-per-class 80
```

The larger run is slower on CPU-only systems.

## Output Report

The learning curve and metrics are written to:

```text
training/artifacts/local_image_calibrator_report.json
```

The report includes:

- validation accuracy
- precision
- recall
- F1-score
- fake false negative rate
- real false positive rate
- confusion matrix
- average precision
- learning-curve entries by epoch and sample count
- hard-example metrics

## Current Verified Behavior

After loading the calibrator and local fallback scoring, the live backend correctly flags a hard fake example:

```json
{
  "verdict": "FAKE",
  "prediction": "fake",
  "fake_probability": 1.0,
  "overall_confidence": 1.0
}
```

This is intentionally aggressive. It protects the demo from the worst failure case: obvious fake images appearing as real.
