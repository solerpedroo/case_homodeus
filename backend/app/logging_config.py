"""Loguru-based structured logging.

We standardize on a single configured sink so every module imports `logger`
without any setup. JSON-friendly format keeps lines parseable in production.
"""
from __future__ import annotations

import sys

from loguru import logger as _logger

_logger.remove()
_logger.add(
    sys.stdout,
    level="INFO",
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> "
        "| <level>{level: <8}</level> "
        "| <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> "
        "- <level>{message}</level>"
    ),
    backtrace=True,
    diagnose=False,
)

logger = _logger
