<<<<<<< HEAD
# KAVACH-AI REST API Reference
=======
# Multimodal Deepfake Detection System Using Advanced Machine Learning Techniques REST API Reference
>>>>>>> 7df14d1 (UI enhanced)

**Base URL**: `http://localhost:8000`  
**Version**: 2.0.0  
**No authentication required** for local deployment.

---

## Endpoints

### `GET /`

Returns basic application info.

**Response**
```json
{
<<<<<<< HEAD
  "name": "KAVACH-AI",
=======
  "name": "Multimodal Deepfake Detection System Using Advanced Machine Learning Techniques",
>>>>>>> 7df14d1 (UI enhanced)
  "version": "2.0.0",
  "docs": "/docs"
}
```

---

### `GET /health`

System health check. Returns model loading status and warnings.

**Response**
```json
{
  "status": "ok",
  "model_versions": {
    "Trained-efficientnet_b4": "efficientnet_b4",
    "audio": "audio_spectrogram_efficientnet_b0",
    "video": "r3d_18"
  },
  "warnings": []
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | `"ok"` or `"degraded"` |
| `model_versions` | object | Map of model name → architecture/version |
| `warnings` | array | List of model loading warnings (empty when all trained models loaded) |

---

### `POST /analyse`

Upload a file for deepfake detection. Accepts image, audio, or video.

**Request**

`Content-Type: multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | file | ✓ | The media file to analyse |

**Supported formats**

| Type | Formats | Max Size |
|------|---------|---------|
| Image | JPEG, PNG, WEBP | 20 MB |
| Audio | WAV, MP3, OGG, FLAC, M4A | 20 MB |
| Video | MP4, WEBM, AVI, MOV, MKV | 100 MB |

**Response**

```json
{
  "type": "image",
  "prediction": "fake",
  "verdict": "FAKE",
  "fake_probability": 0.8732,
  "confidence": 87.32,
  "overall_confidence": 0.8732,
  "processing_time": "142 ms",
  "processing_time_ms": 142,
  "model_scores": [
    {
      "model": "Trained-efficientnet_b4",
      "fake_prob": 0.8732,
      "weight": 1.0,
      "mode": "trained-local"
    }
  ],
  "model_versions": {
    "Trained-efficientnet_b4": "efficientnet_b4"
  },
  "warnings": [],
  "audio_result": null,
  "video_frame_scores": null,
  "video_frame_previews": null
}
```

**For audio files**, `audio_result` is populated:

```json
{
  "audio_result": {
    "verdict": "REAL",
    "fake_probability": 0.1234,
    "waveform": [0.021, 0.018, 0.025, ...],
    "mode": "trained-local",
    "model": "audio_spectrogram_efficientnet_b0"
  }
}
```

**For video files**, `video_frame_scores` and `video_frame_previews` are populated:

```json
{
  "video_frame_scores": [0.42, 0.51, 0.38, 0.79, 0.65],
  "video_frame_previews": [
    {
      "index": 0,
      "fake_probability": 0.42,
      "image_base64": "data:image/jpeg;base64,..."
    }
  ]
}
```

**Response fields**

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | `"image"`, `"audio"`, or `"video"` |
| `prediction` | string | `"real"`, `"fake"`, or `"uncertain"` (lowercase) |
| `verdict` | string | `"REAL"`, `"FAKE"`, or `"UNCERTAIN"` (uppercase) |
| `fake_probability` | float | Probability in [0, 1] that the file is fake |
| `confidence` | float | Confidence score as a percentage (0–100) |
| `overall_confidence` | float | Confidence score in [0, 1] |
| `processing_time` | string | Human-readable processing time |
| `processing_time_ms` | int | Processing time in milliseconds |
| `model_scores` | array | Per-model scores (see ModelScore) |
| `model_versions` | object | Map of model name → version/architecture |
| `warnings` | array | Non-fatal warnings (e.g., audio extraction note) |
| `audio_result` | object\|null | Audio analysis details (for audio/video) |
| `video_frame_scores` | array\|null | Per-frame fake probability scores (for video) |
| `video_frame_previews` | array\|null | Frame preview thumbnails as base64 (for video) |

---

## Error Responses

All errors return JSON with `error` and `code` fields:

```json
{
  "error": "Human-readable error description",
  "code": "ERROR_CODE"
}
```

| HTTP Status | Code | Description |
|-------------|------|-------------|
| 422 | `UNSUPPORTED_FILE_TYPE` | File type not supported |
| 422 | `FILE_TOO_LARGE` | File exceeds size limit |
| 422 | `INVALID_IMAGE_FILE` | Image could not be decoded |
| 422 | `INVALID_AUDIO_FILE` | Audio could not be decoded |
| 422 | `INVALID_VIDEO_FILE` | Video could not be decoded |
| 422 | `VIDEO_ANALYSIS_FAILED` | No frames could be analysed |
| 408 | `TIMEOUT` | Analysis exceeded time limit |
| 500 | `INTERNAL_ERROR` | Unexpected server error |

---

## cURL Examples

**Analyse an image:**
```bash
curl -X POST http://localhost:8000/analyse \
  -F "file=@/path/to/photo.jpg"
```

**Analyse audio:**
```bash
curl -X POST http://localhost:8000/analyse \
  -F "file=@/path/to/recording.wav"
```

**Analyse video:**
```bash
curl -X POST http://localhost:8000/analyse \
  -F "file=@/path/to/video.mp4"
```

**Health check:**
```bash
curl http://localhost:8000/health
```

---

## Python Example

```python
import httpx

with httpx.Client(base_url="http://localhost:8000") as client:
    with open("photo.jpg", "rb") as f:
        response = client.post("/analyse", files={"file": ("photo.jpg", f, "image/jpeg")})
    result = response.json()
    print(f"Verdict: {result['verdict']}")
    print(f"Fake probability: {result['fake_probability']:.2%}")
    print(f"Confidence: {result['confidence']:.1f}%")
```

---

## Interactive Docs

When the backend is running, browse to:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
