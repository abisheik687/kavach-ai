# KAVACH-AI Quick Start

This project is now centered around one active product path:

- Frontend: React + Vite upload/results app
- Backend: FastAPI service with `GET /`, `GET /health`, `POST /analyse`
- Training: local multimodal pipeline under `training/`

## 1. Install dependencies

Backend:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -r backend\requirements.txt
pip install -r training\requirements.txt
```

Frontend:

```powershell
cd frontend
npm install
cd ..
```

## 2. Prepare datasets

Create or verify the expected layout:

```powershell
python training\datasets\acquire_datasets.py --status
```

Put real public datasets under these folders:

- `data/image/faceforensics_pp/{real,fake}`
- `data/image/celeb_df/{real,fake}`
- `data/image/dfdc/{real,fake}`
- `data/video/faceforensics_pp/{real,fake}`
- `data/video/dfdc/{real,fake}`
- `data/audio/asvspoof/{real,fake}`
- `data/audio/fakeavceleb/{real,fake}`

If you already extracted a labeled local folder elsewhere, import it:

```powershell
python training\datasets\acquire_datasets.py --import-modality image --import-dataset celeb_df --from-path D:\datasets\celeb_df
```

Validate before training:

```powershell
python training\datasets\validate_dataset.py
```

## 3. Train the first real submission model

Start with one seed:

```powershell
python training\train_all.py --modality all --seeds 42 --cycles 1
python training\select_best_model.py
```

If that completes in time, add one more seed:

```powershell
python training\train_all.py --modality all --seeds 42 1337 --cycles 1
python training\select_best_model.py
```

`training\train_all.py` writes the best `metadata.json` paths into the project `.env`.

Recommended submission-safe backbones already supported by the training stack:

- image: `convnext_base`
- image alternative: `swinv2_small_window16_256`
- video: `r2plus1d_18`
- audio: `audio_spectrogram_resnet18`
- audio alternative: `audio_spectrogram_convnext_tiny`

## 4. Start the backend in strict trained-model mode

Normal runtime should use trained artifacts only.

```powershell
cd backend
uvicorn main:app --reload
```

Smoke checks:

```powershell
curl http://localhost:8000/
curl http://localhost:8000/health
```

FastAPI docs:

```text
http://localhost:8000/docs
```

## 5. Start the frontend

```powershell
cd frontend
npm run dev
```

Default frontend URL:

```text
http://localhost:5173
```

## 6. Run active tests

Active tests use fallback only in test mode:

```powershell
$env:TEST_MODE='true'
python -m pytest
```

## 7. Submission checklist

- Backend starts with trained manifest env vars set
- Frontend uploads image, video, and audio successfully
- `python training\datasets\validate_dataset.py` reports no empty class folders
- `python training\select_best_model.py` prints the selected best artifacts
- You have 6 to 9 demo samples with recorded predictions and screenshots

## Notes

- This repo is fully local and does not require inference APIs.
- Official datasets still need manual download or approved access from their source sites.
- If `ffmpeg` is not on `PATH`, set `FFMPEG_BINARY` in `.env` or place a binary under `tools/`.
