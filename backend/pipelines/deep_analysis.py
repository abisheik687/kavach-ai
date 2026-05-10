"""
Paid Hugging Face deep-analysis orchestration.

This module is deliberately cache-first and budget-guarded. The free/local
pipeline remains the default; this path only runs when the user explicitly
chooses Paid Deep Analyse.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

import httpx

try:
    from ..config import settings
    from ..models.loader import ModelRegistry
    from ..schemas.request import UploadValidationInfo
    from ..schemas.response import AnalysisResult, ModelScore
    from ..utils.file_utils import clamp
except ImportError:
    from config import settings
    from models.loader import ModelRegistry
    from schemas.request import UploadValidationInfo
    from schemas.response import AnalysisResult, ModelScore
    from utils.file_utils import clamp


DEEP_CACHE_DIR = settings.temp_dir / "deep-analysis-cache"
DEEP_LEDGER_PATH = settings.temp_dir / "hf_deep_budget_ledger.json"


def _ensure_storage() -> None:
    DEEP_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    DEEP_LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)


def _file_sha256(file_path: Path) -> str:
    digest = hashlib.sha256()
    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _cache_path(file_hash: str) -> Path:
    return DEEP_CACHE_DIR / f"{file_hash}.json"


def _load_cached_result(file_hash: str) -> AnalysisResult | None:
    path = _cache_path(file_hash)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    created_at = float(payload.get("_cached_at", 0.0))
    if time.time() - created_at > settings.hf_deep_cache_ttl_seconds:
        return None
    result_payload = payload.get("result")
    if not isinstance(result_payload, dict):
        return None
    result = AnalysisResult(**result_payload)
    result.analysis_source = "paid-cache"
    if "Paid result served from 48-hour cache" not in result.warnings:
        result.warnings.append("Paid result served from 48-hour cache")
    return result


def _save_cached_result(file_hash: str, result: AnalysisResult) -> None:
    _ensure_storage()
    payload = {
        "_cached_at": time.time(),
        "result": result.model_dump(),
    }
    _cache_path(file_hash).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _load_ledger() -> dict[str, Any]:
    _ensure_storage()
    if not DEEP_LEDGER_PATH.exists():
        return {"spent_usd": 0.0, "calls": []}
    try:
        payload = json.loads(DEEP_LEDGER_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"spent_usd": 0.0, "calls": []}
    if not isinstance(payload, dict):
        return {"spent_usd": 0.0, "calls": []}
    payload.setdefault("spent_usd", 0.0)
    payload.setdefault("calls", [])
    return payload


def _budget_remaining() -> float:
    ledger = _load_ledger()
    return max(settings.hf_budget_limit_usd - float(ledger.get("spent_usd", 0.0)), 0.0)


def _record_paid_call(file_hash: str, file_type: str, source: str) -> None:
    ledger = _load_ledger()
    cost = max(float(settings.hf_cost_per_deep_scan_usd), 0.0)
    ledger["spent_usd"] = round(float(ledger.get("spent_usd", 0.0)) + cost, 4)
    ledger.setdefault("calls", []).append(
        {
            "time": int(time.time()),
            "file_hash": file_hash,
            "file_type": file_type,
            "source": source,
            "estimated_cost_usd": cost,
        }
    )
    DEEP_LEDGER_PATH.write_text(json.dumps(ledger, indent=2), encoding="utf-8")


def _disabled_result(validation: UploadValidationInfo, reason: str) -> AnalysisResult:
    return AnalysisResult(
        type=validation.file_type,
        prediction="uncertain",
        confidence=50.0,
        processing_time="0 ms",
        file_type=validation.file_type,
        verdict="UNCERTAIN",
        overall_confidence=0.5,
        fake_probability=0.5,
        model_scores=[
            ModelScore(model="HF Deep Scan", fake_prob=0.5, weight=1.0, mode="disabled"),
        ],
        warnings=[reason, "Use Free Analyse or configure HF_TOKEN and endpoint settings for paid deep scan."],
        model_versions={"deep": "disabled"},
        analysis_source="paid-disabled",
    )


def _score_from_hf_payload(payload: Any) -> float:
    if isinstance(payload, dict):
        if "fake_probability" in payload:
            return clamp(float(payload["fake_probability"]))
        if "score" in payload and "label" in payload:
            label = str(payload["label"]).lower()
            score = float(payload["score"])
            return clamp(score if "fake" in label or "spoof" in label or "synthetic" in label else 1.0 - score)
        if "predictions" in payload:
            return _score_from_hf_payload(payload["predictions"])
    if isinstance(payload, list) and payload:
        fake_scores = []
        real_scores = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label", "")).lower()
            score = float(item.get("score", 0.0))
            if "fake" in label or "spoof" in label or "synthetic" in label:
                fake_scores.append(score)
            if "real" in label or "authentic" in label or "bonafide" in label:
                real_scores.append(score)
        if fake_scores:
            return clamp(max(fake_scores))
        if real_scores:
            return clamp(1.0 - max(real_scores))
        if isinstance(payload[0], dict) and "score" in payload[0]:
            return clamp(float(payload[0]["score"]))
    return 0.5


def _verdict_from_probability(file_type: str, fake_probability: float) -> tuple[str, float]:
    if file_type == "audio":
        real_cutoff, fake_cutoff = 0.55, 0.70
    else:
        real_cutoff, fake_cutoff = 0.55, 0.72
    if fake_probability < real_cutoff:
        return "REAL", 1.0 - fake_probability
    if fake_probability >= fake_cutoff:
        return "FAKE", fake_probability
    return "UNCERTAIN", max(fake_probability, 1.0 - fake_probability)


def _endpoint_url_from_hub() -> str | None:
    if settings.hf_endpoint_url:
        return settings.hf_endpoint_url
    if not settings.hf_endpoint_name or not settings.hf_endpoint_namespace:
        return None
    try:
        from huggingface_hub import get_inference_endpoint

        endpoint = get_inference_endpoint(
            name=settings.hf_endpoint_name,
            namespace=settings.hf_endpoint_namespace,
            token=settings.hf_token,
        )
        if hasattr(endpoint, "resume"):
            endpoint.resume()
        if hasattr(endpoint, "wait"):
            endpoint.wait(timeout=600)
        return getattr(endpoint, "url", None)
    except Exception:
        return None


def _scale_endpoint_to_zero() -> None:
    if not settings.hf_auto_scale_to_zero or not settings.hf_endpoint_name or not settings.hf_endpoint_namespace:
        return
    try:
        from huggingface_hub import get_inference_endpoint

        endpoint = get_inference_endpoint(
            name=settings.hf_endpoint_name,
            namespace=settings.hf_endpoint_namespace,
            token=settings.hf_token,
        )
        if hasattr(endpoint, "scale_to_zero"):
            endpoint.scale_to_zero()
        elif hasattr(endpoint, "pause"):
            endpoint.pause()
    except Exception:
        return


async def _run_paid_hf_scan(file_path: Path, validation: UploadValidationInfo) -> tuple[float, str]:
    endpoint_url = _endpoint_url_from_hub()
    if not endpoint_url:
        raise RuntimeError("HF endpoint URL is not configured or could not be resolved")

    headers = {"Authorization": f"Bearer {settings.hf_token}"}
    with file_path.open("rb") as handle:
        content = handle.read()
    async with httpx.AsyncClient(timeout=180.0) as client:
        response = await client.post(
            endpoint_url,
            content=content,
            headers=headers,
        )
        response.raise_for_status()
        payload = response.json()
    if settings.hf_deep_mode.strip().lower() == "endpoint":
        _scale_endpoint_to_zero()
    return _score_from_hf_payload(payload), endpoint_url


async def analyse_deep_file(
    file_path: Path,
    registry: ModelRegistry,
    validation: UploadValidationInfo,
    free_result: AnalysisResult,
) -> AnalysisResult:
    _ensure_storage()
    file_hash = _file_sha256(file_path)
    cached = _load_cached_result(file_hash)
    if cached:
        return cached

    if not settings.hf_deep_analysis_enabled:
        result = _disabled_result(validation, "Paid Deep Analyse is disabled in backend configuration.")
        result.warnings.extend(free_result.warnings[:2])
        return result
    if not settings.hf_token:
        result = _disabled_result(validation, "Paid Deep Analyse is not configured because HF_TOKEN is missing.")
        result.warnings.extend(free_result.warnings[:2])
        return result
    if _budget_remaining() < settings.hf_cost_per_deep_scan_usd:
        return _disabled_result(validation, "HF paid deep-scan budget cap reached; remote scan was not started.")

    try:
        fake_probability, source = await _run_paid_hf_scan(file_path, validation)
        verdict, confidence = _verdict_from_probability(validation.file_type, fake_probability)
        result = AnalysisResult(
            type=validation.file_type,
            prediction=verdict.lower(),
            confidence=round(confidence * 100.0, 2),
            processing_time="0 ms",
            file_type=validation.file_type,
            verdict=verdict,
            overall_confidence=round(confidence, 4),
            fake_probability=round(fake_probability, 4),
            model_scores=[
                ModelScore(model="HF Deep Scan", fake_prob=round(fake_probability, 4), weight=1.0, mode="paid-hf"),
            ],
            warnings=["Paid HF deep scan completed and cached for 48 hours."],
            model_versions={**registry.model_versions, "deep": source},
            analysis_source="paid-hf",
        )
        _record_paid_call(file_hash, validation.file_type, source)
        _save_cached_result(file_hash, result)
        return result
    except Exception as exc:
        result = free_result
        result.analysis_source = "paid-fallback-free-local"
        result.warnings = list(dict.fromkeys([
            "Paid HF deep scan failed; returned free local result instead.",
            str(exc),
            *result.warnings,
        ]))
        result.model_versions = {**result.model_versions, "deep": "failed"}
        return result
