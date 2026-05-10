# KAVACH-AI Project Report

## Title

KAVACH-AI: An AI-Powered Forensic Platform for Deepfake Detection and Media Authenticity Analysis

## Abstract

KAVACH-AI is a web-based AI forensic platform that performs probabilistic authenticity analysis on image, video, and audio media. The system combines upload validation, local forensic scoring, media-specific preprocessing, ensemble confidence logic, and explainable result presentation. Instead of claiming perfect deepfake detection, the platform reports a fake probability, confidence score, verdict, model breakdown, and media evidence such as video frame scores and audio waveforms.

The project is designed as an end-to-end full-stack system with a React frontend, FastAPI backend, multimodal analysis pipelines, local-only inference mode, and deployment-ready Docker structure. This makes it stronger academically than a standalone classifier because it demonstrates software architecture, AI integration, cybersecurity relevance, and user-facing product design.

## Problem Statement

AI-generated and manipulated media can be used for misinformation, identity spoofing, fraud, and reputational attacks. Manual verification is slow and difficult because synthetic artifacts may appear in visual texture, compression patterns, audio spectra, frame consistency, or metadata. The goal of this project is to build a practical web platform that helps users analyze suspicious media and receive a clear authenticity risk score.

## Objectives

- Detect suspicious signals in images, videos, and audio files.
- Provide a fake probability instead of a binary-only answer.
- Present model-level explanations and warnings.
- Support a polished upload-to-result workflow.
- Run locally without paid Hugging Face credit usage.
- Provide architecture diagrams and evaluation methodology for academic review.

## Scope

Current implemented scope:

- Image upload: JPEG, PNG, WEBP, GIF.
- Video upload: MP4 and WEBM.
- Audio upload: WAV, MP3, OGG.
- Local inference fallback mode.
- Fake probability, verdict, confidence, warnings.
- Video frame sampling and frame-level scoring.
- Audio waveform display and spectral fallback scoring.
- Frontend result page with model breakdown.
- FastAPI backend with OpenAPI documentation.

Future scope:

- User authentication.
- Batch scan history.
- PDF report generation.
- URL scanning.
- Real-time webcam analysis.
- PostgreSQL and Redis-backed async jobs.
- Trained model artifact deployment.

## Existing Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React, Vite, Tailwind, Framer Motion |
| Backend | Python, FastAPI, Pydantic |
| Image Processing | Pillow, OpenCV, NumPy |
| Audio Processing | librosa, soundfile, SciPy |
| ML Runtime | PyTorch, torchvision, timm |
| API Docs | FastAPI Swagger UI |
| Deployment | Docker Compose |

## System Architecture Summary

KAVACH-AI uses a web client and API server architecture.

1. The user uploads media through the frontend.
2. The backend validates file type and size.
3. The file is routed to image, audio, or video pipelines.
4. The model registry loads local scorers or trained artifacts.
5. The ensemble scorer combines fake probability signals.
6. The frontend displays verdict, confidence, warnings, and evidence.

## Detection Methodology

### Image Analysis

The current local image path uses lightweight forensic indicators:

- JPEG/block artifact signal.
- Frequency-domain score.
- Color consistency score.
- Patch consistency score.
- Synthetic/non-photographic signal.
- Low-quality synthetic signal.

These scores are combined with a fake-recall-biased threshold because the project priority is to avoid calling obvious fake media real.

### Video Analysis

Video files are analyzed by:

- Sampling frames from the uploaded video.
- Running image analysis on sampled frames.
- Aggregating frame fake probabilities.
- Returning frame preview thumbnails and per-frame scores.
- Optionally extracting audio when FFmpeg is available.

### Audio Analysis

Audio files are analyzed by:

- Loading or resampling audio to 16 kHz.
- Building waveform evidence.
- Computing signal fallback features such as spectral flatness, zero crossing, and spectral contrast.
- Returning audio fake probability and waveform data.

## Confidence Scoring

The image ensemble uses:

```text
final_score = 0.6 * weighted_mean + 0.4 * max_fake_signal
```

This prevents one strong fake signal from being averaged away.

Verdict logic:

```text
FAKE       if fake_probability >= threshold
UNCERTAIN  if model spread is high
REAL       otherwise
```

Current local-only image threshold:

```text
DEFAULT_IMAGE_THRESHOLD = 0.35
```

This is intentionally fake-recall biased for demonstration stability.

## Evaluation Metrics

The project should report:

- Accuracy
- Precision
- Recall
- F1-score
- Confusion matrix
- Fake false negative rate
- Real false positive rate
- Average precision where probability scores are available

For a college review, recall is especially important because the main failure case is fake images being classified as real.

## Demo Positioning

Do not say:

> Our model detects deepfakes perfectly.

Say:

> Our platform performs probabilistic forensic analysis using multiple AI and signal-processing indicators. It reports fake probability, confidence, and supporting evidence.

## Current Limitations

- The local fallback detector is heuristic and not a replacement for a properly trained model.
- The current threshold favors fake recall and may increase false positives on low-quality real images.
- No production database or user authentication is active yet.
- No trained artifact is currently configured in the backend.
- Real-time webcam and URL scanning are future extensions.

## Conclusion

KAVACH-AI demonstrates a complete AI cybersecurity application rather than only a classifier. The academic strength of the project comes from its full-stack implementation, multimodal processing, confidence scoring, architecture design, and explainable forensic workflow.
