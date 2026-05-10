# Demo Script

## 1. Opening Statement

Good morning. Our project is KAVACH-AI, an AI-powered forensic platform for deepfake detection and media authenticity analysis.

The system does not claim perfect detection. It performs probabilistic forensic analysis using multiple local AI and signal-processing indicators, then reports a fake probability, confidence score, verdict, and supporting evidence.

## 2. Problem Explanation

Deepfakes and synthetic media can be used for:

- misinformation
- identity spoofing
- fraud
- fake evidence
- voice cloning
- social engineering

Manual detection is difficult because fake media can contain subtle artifacts in compression, frequency patterns, facial regions, audio spectra, or video frame consistency.

## 3. Project Objective

The objective is to build a complete web platform that can:

- accept image, video, and audio uploads
- run media-specific forensic analysis
- generate a fake probability
- show model-level confidence
- explain warnings and evidence
- provide a clean user workflow for reviewers

## 4. Architecture Explanation

KAVACH-AI has four main layers:

1. React frontend for upload, preview, and result display.
2. FastAPI backend for validation and routing.
3. Media pipelines for image, video, and audio processing.
4. Model registry and ensemble logic for fake probability scoring.

The backend is currently configured for free local inference only, so it does not consume paid Hugging Face credits.

## 5. Demo Workflow

### Step 1: Start the backend

```powershell
cd backend
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

### Step 2: Start the frontend

```powershell
cd frontend
npm run dev
```

### Step 3: Open the app

```text
http://127.0.0.1:5173
```

### Step 4: Upload a media file

Explain:

> The file is first validated by MIME type and size. Then it is routed to the correct analysis pipeline.

### Step 5: Show the result page

Point out:

- verdict
- fake probability
- confidence
- model breakdown
- warnings
- video frames or audio waveform when applicable

## 6. Technical Explanation for Image Analysis

For images, the system checks local forensic signals such as:

- JPEG/block artifacts
- frequency-domain irregularities
- color consistency
- patch consistency
- synthetic/non-photographic patterns
- low-quality generation indicators

These are combined into one fake probability.

## 7. Technical Explanation for Video Analysis

For videos, the system:

1. samples frames
2. analyzes each frame as an image
3. aggregates frame fake probabilities
4. shows suspicious frame previews
5. optionally extracts and analyzes audio

## 8. Technical Explanation for Audio Analysis

For audio, the system:

- loads and resamples audio
- builds waveform evidence
- checks spectral properties
- reports audio fake probability

## 9. Important Academic Statement

Say this during review:

> Our system is not just a CNN classifier. It is an end-to-end AI forensic platform with frontend, backend, APIs, multimodal pipelines, confidence scoring, and explainable results.

## 10. Handling Accuracy Questions

If asked whether it is perfect:

> No deepfake detector is perfect. Our system reports probabilistic risk. We evaluate using accuracy, precision, recall, F1-score, and confusion matrix. We especially prioritize fake recall because the most harmful error is classifying fake media as real.

If asked why some real files may be flagged:

> The current local-only mode is intentionally fake-recall biased. It reduces the chance of fake media being allowed as real, at the cost of possible false alarms. A trained calibrated artifact can later improve this balance.

## 11. Strong Closing

KAVACH-AI demonstrates a real-world AI cybersecurity workflow. It combines software engineering, machine learning, media processing, API design, and explainable analysis into one working platform.
