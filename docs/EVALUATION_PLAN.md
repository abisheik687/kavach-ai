# Evaluation Plan

## Goal

The goal is to measure how well KAVACH-AI separates real and fake media using transparent metrics. The system should be evaluated as a probabilistic forensic platform, not as a perfect binary detector.

## Test Sets

Recommended evaluation groups:

| Split | Purpose |
|---|---|
| Validation set | Tune thresholds and check overfitting |
| Test set | Report final metrics |
| Hard fake set | Measure obvious low-quality fake recall |
| Hard real set | Measure false alarms on degraded real media |
| Cross-dataset set | Test generalization across sources |

Current useful local folders:

```text
data/hard_examples/image/fake
data/hard_examples/image/real
training/manifests/image_manifest.csv
```

## Metrics to Report

| Metric | Meaning |
|---|---|
| Accuracy | Overall correct predictions |
| Precision | Of predicted fake files, how many were actually fake |
| Recall | Of actual fake files, how many were caught |
| F1-score | Balance of precision and recall |
| Confusion matrix | Counts of real/fake mistakes |
| Fake false negative rate | Fake files incorrectly predicted real |
| Real false positive rate | Real files incorrectly predicted fake |
| Average precision | Probability-ranking quality |

## Confusion Matrix Format

```text
                 Predicted Real    Predicted Fake
Actual Real           TN                FP
Actual Fake           FN                TP
```

For this project, the most important error is:

```text
FN = fake media classified as real
```

That is why the current threshold is fake-recall biased.

## Recommended Review Metrics

During the review, present metrics in this order:

1. Fake recall
2. F1-score
3. Confusion matrix
4. Accuracy
5. Real false positive rate

This prevents the discussion from focusing only on accuracy, which can be misleading when classes are imbalanced.

## Baseline to Explain

Initial issue:

```text
train: 615 real / 69 fake
val:    85 real / 570 fake
```

This caused the model to learn a "real by default" decision bias.

Correction strategy:

```text
balanced manifest
hard fake examples
lower threshold
max fake signal ensemble
local forensic fallback scoring
```

## Manual API Evaluation Command

Run the backend:

```powershell
cd backend
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Check health:

```powershell
curl.exe http://127.0.0.1:8000/health
```

Analyze one known fake:

```powershell
curl.exe -X POST -F "file=@data/hard_examples/image/fake/00000_lowres.jpg" http://127.0.0.1:8000/analyse
```

Expected behavior for the hard fake example:

```json
{
  "verdict": "FAKE",
  "prediction": "fake",
  "fake_probability": 0.5721
}
```

## Suggested Batch Evaluation Script

Create a simple script that:

1. Reads real and fake test folders.
2. Sends files to `/analyse`.
3. Stores `label`, `prediction`, and `fake_probability`.
4. Computes confusion matrix and metrics.
5. Saves `evaluation_results.json`.

Pseudo-code:

```python
for path in fake_files:
    response = post_analyse(path)
    y_true.append(1)
    y_score.append(response["fake_probability"])
    y_pred.append(1 if response["verdict"] == "FAKE" else 0)

for path in real_files:
    response = post_analyse(path)
    y_true.append(0)
    y_score.append(response["fake_probability"])
    y_pred.append(1 if response["verdict"] == "FAKE" else 0)
```

## Review Explanation

Use this wording:

> We evaluate the system using standard classification metrics, but we prioritize fake recall because the most dangerous failure is allowing fake media to pass as real. The current local-only configuration is intentionally recall-biased while the trained model artifact is being improved.

## Expected Improvement Path

1. Use local-only forensic fallback for stable demo behavior.
2. Train the image classifier on the balanced manifest.
3. Calibrate threshold on the validation set.
4. Evaluate hard fake recall independently.
5. Load the trained artifact into `MODEL_IMAGE_ARTIFACT_MANIFEST`.
6. Re-run the same metrics and compare against the fallback baseline.
