"""
Internal trace:
- Wrong before: runtime helpers only imported from one cwd layout, so package-mode startup failed before timeouts and thread offloading could be used.
- Fixed now: concurrency/timeouts behave the same, but the module imports safely from both repo-root and backend-local execution.
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from collections.abc import Awaitable, Callable
from functools import partial
from typing import TypeVar

try:
    from ..config import settings
    from .file_utils import AppError
    from .logger import get_logger
except ImportError:
    from config import settings
    from utils.file_utils import AppError
    from utils.logger import get_logger


logger = get_logger(__name__)
T = TypeVar('T')
TEMP_DIR = os.getenv('TEMP_DIR', os.path.abspath('temp'))
os.makedirs(TEMP_DIR, exist_ok=True)
tempfile.tempdir = TEMP_DIR
_analysis_semaphore = asyncio.Semaphore(settings.max_concurrent_analyses)


async def run_inference(func: Callable[..., T], *args, timeout_seconds: int, stage: str) -> T:
    try:
        return await asyncio.wait_for(asyncio.to_thread(partial(func, *args)), timeout=timeout_seconds)
    except TimeoutError as exc:
        logger.warning('analysis_stage_timeout', extra={'stage': stage, 'timeout_seconds': timeout_seconds})
        raise AppError(504, f'{stage} timed out before analysis could finish.', 'ANALYSIS_TIMEOUT') from exc
    except AppError:
        raise
    except Exception as exc:
        logger.exception('analysis_stage_failed', extra={'stage': stage, 'error': str(exc)})
        raise AppError(422, f'{stage} failed while processing the uploaded media.', 'ANALYSIS_STAGE_FAILED') from exc


async def run_analysis(coro: Awaitable[T], *, timeout_seconds: int, stage: str) -> T:
    async with _analysis_semaphore:
        try:
            return await asyncio.wait_for(coro, timeout=timeout_seconds)
        except TimeoutError as exc:
            logger.warning('analysis_timeout', extra={'stage': stage, 'timeout_seconds': timeout_seconds})
            raise AppError(504, f'{stage} timed out before analysis could finish.', 'ANALYSIS_TIMEOUT') from exc
