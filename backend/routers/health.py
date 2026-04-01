"""
Internal trace:
- Wrong before: package-mode startup failed before the health route could import, which made diagnosis harder.
- Fixed now: the health route imports cleanly in both execution modes and reports the corrected loaded model count.
"""

from __future__ import annotations

from fastapi import APIRouter

try:
    from ..models.loader import get_model_registry
except ImportError:
    from models.loader import get_model_registry


router = APIRouter(tags=['health'])


@router.get('/health')
async def health() -> dict[str, int | str]:
    registry = get_model_registry()
    return {'status': 'ok', 'models_loaded': registry.loaded_count}
