"""
Internal trace:
- Wrong before: the logger module only imported from one cwd layout, which could crash startup before logs were configured.
- Fixed now: logging stays stdlib-only and now works in both repo-root and backend-local execution.
"""

from __future__ import annotations

import logging

try:
    from ..config import settings
except ImportError:
    from config import settings


_configured = False


def _configure_logging() -> None:
    global _configured
    if _configured:
        return
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format='%(asctime)s %(levelname)s %(name)s %(message)s',
    )
    _configured = True


def get_logger(name: str) -> logging.Logger:
    _configure_logging()
    return logging.getLogger(name)
