# Review Documentation Index

Use this document as the starting point for project review or viva preparation.

## Must-Show Documents

1. [Project Report](PROJECT_REPORT.md)
   - Problem statement
   - Objectives
   - Methodology
   - Limitations
   - Academic positioning

2. [System Diagrams](CODEBASE_DIAGRAM.md)
   - Architecture diagram
   - Data flow diagram
   - Use case diagram
   - Sequence diagram
   - Component diagram
   - Deployment diagram
   - Proposed ER diagram

3. [Evaluation Plan](EVALUATION_PLAN.md)
   - Accuracy
   - Precision
   - Recall
   - F1-score
   - Confusion matrix
   - Fake false negative rate

4. [Demo Script](DEMO_SCRIPT.md)
   - What to say during review
   - What not to claim
   - How to explain imperfect model behavior

5. [API Reference](API.md)
   - Backend endpoints
   - Request and response format
   - Local-only inference configuration

6. [Local Learning Curve](LOCAL_LEARNING_CURVE.md)
   - Free local calibrator
   - Learning-curve output
   - Fake-recall-biased runtime behavior

## One-Line Project Definition

KAVACH-AI is an end-to-end AI forensic platform that performs probabilistic authenticity analysis for image, video, and audio media.

## Best Review Statement

> Our system performs probabilistic forensic analysis using multiple local AI and signal-processing indicators. It reports fake probability, confidence, model breakdown, and supporting evidence instead of claiming perfect detection.

## Current Demo URLs

Backend:

```text
http://127.0.0.1:8000
```

Frontend:

```text
http://127.0.0.1:5173
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

## Current Technical Strengths

- Full-stack implementation.
- Multimodal image, video, and audio upload support.
- FastAPI backend with structured response schemas.
- Local-only inference mode with no paid Hugging Face credit usage.
- Ensemble confidence scoring.
- Explainable result UI with model breakdown and warnings.
- Review-ready architecture and evaluation documentation.

## Current Honest Limitation

The detector is intentionally fake-recall biased in local-only mode. This reduces the chance of fake media being classified as real, but it may increase false positives for low-quality real media. This is acceptable for the current review goal and should be improved later with calibrated trained artifacts.
