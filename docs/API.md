# KAVACH-AI API Reference

Base URL:

```text
http://127.0.0.1:8000
```

Interactive documentation:

```text
http://127.0.0.1:8000/docs
```

## Runtime Mode

The current college-demo configuration uses free local inference only.

```text
ENABLE_REMOTE_MODEL_DOWNLOADS=false
HF_INFERENCE_MODE=local_only
HF_WEEKLY_BUDGET_USD=0
BLOCK_HF_CREDIT_USAGE=true
```

This prevents accidental Hugging Face credit usage.

## GET /

Returns application metadata.

Example:

```powershell
curl.exe http://127.0.0.1:8000/
```

Response:

```json
{
  "name": "KAVACH-AI",
  "version": "2.0.0",
  "docs": "/docs"
}
```

## GET /health

Returns backend health and loaded model count.

Example:

```powershell
curl.exe http://127.0.0.1:8000/health
```

Response:

```json
{
  "status": "ok",
  "models_loaded": 5
}
```

## POST /analyse

Analyzes one uploaded image, video, or audio file.

Request:

```text
Content-Type: multipart/form-data
field: file
```

Supported formats:

| Media | Formats | Max Size |
|---|---|---|
| Image | JPEG, PNG, WEBP, GIF | 20 MB |
| Video | MP4, WEBM | 100 MB |
| Audio | WAV, MP3, OGG | 20 MB |

Example image request:

```powershell
curl.exe -X POST -F "file=@data/hard_examples/image/fake/00000_lowres.jpg" http://127.0.0.1:8000/analyse
```

Example response:

```json
{
  "type": "image",
  "prediction": "fake",
  "confidence": 57.21,
  "processing_time": "2328 ms",
  "file_type": "image",
  "verdict": "FAKE",
  "overall_confidence": 0.5721,
  "fake_probability": 0.5721,
  "model_scores": [
    {
      "model": "ViT",
      "fake_prob": 0.5721,
      "weight": 0.3,
      "mode": "fallback"
    }
  ],
  "video_frame_scores": [],
  "video_frame_previews": [],
  "audio_result": null,
  "processing_time_ms": 2328,
  "warnings": [
    "HF remote inference disabled; using free local forensic fallback scorers"
  ],
  "model_versions": {
    "ViT": "fallback:vit",
    "audio": "fallback:signal",
    "video": "fallback:frame-aggregation"
  }
}
```

## Response Field Meaning

| Field | Meaning |
|---|---|
| `verdict` | Final uppercase label: `REAL`, `FAKE`, or `UNCERTAIN` |
| `prediction` | Lowercase prediction for frontend compatibility |
| `fake_probability` | Probability that media is fake, from 0 to 1 |
| `overall_confidence` | Confidence in the final verdict, from 0 to 1 |
| `confidence` | Same idea as percentage |
| `model_scores` | Per-scorer or per-model fake probabilities |
| `warnings` | Runtime notes such as fallback mode or skipped audio extraction |
| `video_frame_scores` | Per-frame fake probability values for video |
| `video_frame_previews` | Base64 thumbnails of sampled video frames |
| `audio_result` | Audio-specific result object |

## Error Format

Errors use:

```json
{
  "error": "Human-readable message",
  "code": "ERROR_CODE"
}
```

Common errors:

| Status | Code | Meaning |
|---|---|---|
| 422 | `MISSING_FILE` | No uploaded file |
| 422 | `EMPTY_FILE` | Uploaded file is empty |
| 422 | `INVALID_FILE_TYPE` | Unsupported MIME type |
| 413 | `FILE_TOO_LARGE` | File exceeds size limit |
| 422 | `INVALID_IMAGE_FILE` | Image could not be decoded |
| 422 | `INVALID_AUDIO_FILE` | Audio could not be decoded |
| 422 | `INVALID_VIDEO_FILE` | Video could not be decoded |
| 500 | `INTERNAL_ERROR` | Unexpected backend error |
