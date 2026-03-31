# KAVACH-AI Deadline Runbook

## Goal

Ship a stable submission by keeping the app demoable at all times while moving from empty dataset folders to one real local training run.

## Tonight

### 1. Prepare dataset folders

```powershell
python training\datasets\acquire_datasets.py --status
```

Official sources:

- FaceForensics++: <https://github.com/ondyari/FaceForensics>
- Celeb-DF: <https://github.com/yuezunli/celeb-deepfakeforensics>
- DFDC: <https://www.kaggle.com/c/deepfake-detection-challenge/data>
- ASVspoof: <https://www.asvspoof.org/>
- FakeAVCeleb: <https://github.com/DASH-Lab/FakeAVCeleb>

Place labeled subsets here:

- `data/image/faceforensics_pp/{real,fake}`
- `data/image/celeb_df/{real,fake}`
- `data/image/dfdc/{real,fake}`
- `data/video/faceforensics_pp/{real,fake}`
- `data/video/dfdc/{real,fake}`
- `data/audio/asvspoof/{real,fake}`
- `data/audio/fakeavceleb/{real,fake}`

### 2. Validate

```powershell
python training\datasets\validate_dataset.py
```

Target:

- no empty folders
- no corrupted files
- class ratio not worse than about `1.5:1`

### 3. First real training run

```powershell
python training\run_production.py --seeds 42 --cycles 1
```

### 4. If time remains

```powershell
python training\run_production.py --seeds 42 1337 --cycles 1
```

## Demo Day

### Start backend

```powershell
cd backend
uvicorn main:app --reload
```

### Start frontend

```powershell
cd frontend
npm run dev
```

### Active tests

```powershell
$env:TEST_MODE='true'
python -m pytest
```

## Submission evidence to collect

- `/health` success screenshot
- upload page screenshot
- result page screenshot for image, video, and audio
- one table of real-world sample predictions
- `training/artifacts/train_all_summary.json`
- selected `report.json` files for the best runs

## Honest positioning

Use this wording:

- fully local multimodal deepfake detection system
- supports image, video, and audio
- trained on curated public dataset subsets for deadline/compute limits
- includes validation, training, selection, and deployment loop

Do not claim full-dataset benchmark parity or unrestricted real-world generalization.
