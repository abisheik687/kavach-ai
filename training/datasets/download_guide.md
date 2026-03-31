# KAVACH-AI Real Dataset Download Guide

To achieve production-grade accuracy, you must replace synthetic datasets with real, large-scale deepfake datasets.

## Directory Structure
Place your extracted datasets here before running the validation/training scripts:

```text
data/
├── image/
│   ├── faceforensics_pp/
│   │   ├── real/
│   │   └── fake/
│   ├── celeb_df/
│   │   ├── real/
│   │   └── fake/
│   └── dfdc/
│       ├── real/
│       └── fake/
├── video/
│   ├── faceforensics_pp/
│   │   ├── real/
│   │   └── fake/
│   └── dfdc/
│       ├── real/
│       └── fake/
└── audio/
    ├── asvspoof/
    │   ├── real/
    │   └── fake/
    └── fakeavceleb/
        ├── real/
        └── fake/
```

## 1. FaceForensics++
- **Focus**: Face manipulation (Deepfakes, Face2Face, FaceSwap, NeuralTextures).
- **Format**: Video (MP4) and Image (extracted frames).
- **Download**: You must fill out the request form on their [official GitHub](https://github.com/ondyari/FaceForensics) to get the download script.
- **Tip**: Download both `c23` (high quality) and `c40` (low quality) compressions to ensure the model generalizes to blurry social media videos.

## 2. Celeb-DF (v2)
- **Focus**: High-quality face swaps of celebrities, fewer visual artifacts than FF++.
- **Format**: Video (MP4). Extract frames to `data/image/celeb_df` for image training.
- **Download**: Access via the [official repository](https://github.com/yuezunli/celeb-deepfakeforensics).

## 3. Deepfake Detection Challenge (DFDC)
- **Focus**: Extremely diverse real-world scenarios, heavy compression, varied lighting.
- **Format**: Video (MP4).
- **Download**: Originally hosted on Kaggle. You can find the dataset or a subset on [Kaggle](https://www.kaggle.com/c/deepfake-detection-challenge/data). Note: The full dataset is ~470 GB. A 10-20 GB subset is recommended for local training unless you have massive storage/compute.

## 4. ASVspoof (2019/2021)
- **Focus**: Audio spoofing (TTS, voice conversion).
- **Format**: Audio (WAV/FLAC).
- **Download**: Available via the [ASVspoof Challenge website](https://www.asvspoof.org/). Use the "Logical Access" (LA) partitions for deepfake voice detection.

## 5. FakeAVCeleb
- **Focus**: Multimodal (Audio-Visual) deepfakes. Contains real and fake combinations (e.g., Fake Video + Real Audio, Real Video + Fake Audio).
- **Format**: Video (MP4) with Audio track.
- **Download**: Available via academic request ([FakeAVCeleb repo](https://github.com/DASH-Lab/FakeAVCeleb)). Separate the audio tracks using FFmpeg into `data/audio/fakeavceleb`.
