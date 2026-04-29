"""Günlük dönen log dosyası ayarı.

Kullanım:
    from karotcam.utils.logger import setup_logging, get_logger

    setup_logging()
    log = get_logger(__name__)
    log.info("hazır")
"""
from __future__ import annotations

import logging
import sys
from datetime import date
from logging.handlers import RotatingFileHandler
from pathlib import Path

import config

_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_initialized = False


def setup_logging() -> None:
    """Kök logger'a dosya + konsol handler bağla. İdempotent."""
    global _initialized
    if _initialized:
        return

    config.LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_path: Path = config.LOGS_DIR / f"{date.today().isoformat()}.log"

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(getattr(logging, config.LOG_LEVEL_FILE))
    file_handler.setFormatter(logging.Formatter(_LOG_FORMAT))

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, config.LOG_LEVEL_CONSOLE))
    console_handler.setFormatter(logging.Formatter(_LOG_FORMAT))

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(file_handler)
    root.addHandler(console_handler)

    _initialized = True


def get_logger(name: str) -> logging.Logger:
    """Modül adıyla logger döndür."""
    return logging.getLogger(name)
