"""
logging_config.py
=================
Centralised, structured logging setup for the trading bot.

Log levels:
  - DEBUG  : Detailed API payloads / raw responses (file only)
  - INFO   : Normal operational events
  - WARNING: Recoverable issues
  - ERROR  : Failures requiring attention
  - CRITICAL: System-level failures
"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path


# ── Constants ─────────────────────────────────────────────────────────────────
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_FILE = LOG_DIR / "trading_bot.log"
MAX_BYTES = 5 * 1024 * 1024   # 5 MB per log file
BACKUP_COUNT = 5               # keep last 5 rotated files

_LOG_FORMAT = (
    "[%(asctime)s] [%(levelname)-8s] [%(name)s] %(message)s"
)
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


# ── Internal helpers ───────────────────────────────────────────────────────────

def _build_file_handler() -> logging.Handler:
    """Rotating file handler that captures DEBUG and above."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    handler = logging.handlers.RotatingFileHandler(
        filename=LOG_FILE,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))
    return handler


def _build_console_handler() -> logging.Handler:
    """Stderr console handler — INFO and above."""
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(logging.WARNING)          # only warnings+ go to console
    handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))
    return handler


# ── Public API ─────────────────────────────────────────────────────────────────

def setup_logging(level: int = logging.DEBUG) -> None:
    """
    Configure root logger.  Call once at application startup.

    Parameters
    ----------
    level : int
        Minimum level for the root logger (default DEBUG so file captures all).
    """
    root = logging.getLogger()
    if root.handlers:
        return  # already configured – idempotent

    root.setLevel(level)
    root.addHandler(_build_file_handler())
    root.addHandler(_build_console_handler())

    # Suppress noisy third-party loggers
    for noisy_lib in ("urllib3", "requests", "httpx", "asyncio"):
        logging.getLogger(noisy_lib).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Return a module-scoped logger.

    Usage
    -----
    >>> from bot.logging_config import get_logger
    >>> log = get_logger(__name__)
    >>> log.info("Order placed successfully")
    """
    return logging.getLogger(name)
