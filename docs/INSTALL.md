# Installation and Local Run Guide

This guide describes the current active KAVACH-AI web application.

## Requirements

- Python 3.10+
- Node.js 20+
- npm
- ffmpeg optional, used for video audio extraction

## Local Backend

From the project root:

```powershell
cd backend
python -m pip install -r requirements.txt
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Backend URL:

```text
http://127.0.0.1:8000
```

Swagger API docs:

```text
http://127.0.0.1:8000/docs
```

Health check:

```powershell
curl.exe http://127.0.0.1:8000/health
```

Expected response:

```json
{
  "status": "ok",
  "models_loaded": 5
}
```

## Local Frontend

Open a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Frontend URL:

```text
http://127.0.0.1:5173
```

## Environment

The backend reads settings from:

```text
backend/.env
```

Current free local-only inference settings:

```text
ENABLE_REMOTE_MODEL_DOWNLOADS=false
HF_INFERENCE_MODE=local_only
HF_WEEKLY_BUDGET_USD=0
BLOCK_HF_CREDIT_USAGE=true
DEFAULT_IMAGE_THRESHOLD=0.35
```

These settings prevent paid Hugging Face credit usage.

## Docker Compose

From the project root:

```powershell
docker compose up --build
```

Docker URLs:

```text
Frontend: http://localhost:4173
Backend:  http://localhost:8000
Docs:     http://localhost:8000/docs
```

## Supported Uploads

| Media | Formats | Limit |
|---|---|---|
| Image | JPEG, PNG, WEBP, GIF | 20 MB |
| Video | MP4, WEBM | 100 MB |
| Audio | WAV, MP3, OGG | 20 MB |

## Troubleshooting

### Backend does not start

Check missing Python packages:

```powershell
python -m pip install -r backend/requirements.txt
```

### Frontend cannot reach backend

Check `frontend/.env`:

```text
VITE_API_URL=http://localhost:8000
```

### Video audio extraction does not work

Install ffmpeg and make sure it is on PATH, or set:

```text
FFMPEG_BINARY=C:\path\to\ffmpeg.exe
```

### All outputs look too fake-biased

The current threshold is intentionally tuned to reduce fake-as-real mistakes for demonstration. Raise `DEFAULT_IMAGE_THRESHOLD` from `0.35` to `0.45` or `0.50` if you want fewer false positives.
