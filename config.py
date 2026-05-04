"""KarotCam yapılandırma sabitleri.

Tüm tunable değerler burada toplanır. Değişiklik için yeniden derleme gerekir
(v1'de runtime config dosyası yok — kasıtlı bir basitleştirme).
"""
from __future__ import annotations

import sys
from pathlib import Path


def _resolve_base_dir() -> Path:
    """Exe yanında (PyInstaller) veya repo kökünde (dev) çalış."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


APP_NAME = "KarotCam"
APP_VERSION = "0.1.0"

BASE_DIR: Path = _resolve_base_dir()
DATA_DIR: Path = BASE_DIR / "data"
PHOTOS_RAW_DIR: Path = DATA_DIR / "photos" / "raw"
BACKUPS_DIR: Path = DATA_DIR / "backups"
LOGS_DIR: Path = DATA_DIR / "logs"
DB_PATH: Path = BASE_DIR / "karotcam.db"

# digiCamControl
DIGICAM_BASE_URL: str = "http://localhost:5513"
DIGICAM_LIVEVIEW_URL: str = "http://localhost:5513/liveview.jpg"
DIGICAM_HEARTBEAT_MS: int = 5000
DIGICAM_LIVEVIEW_POLL_MS: int = 100  # ~10 fps — less aggressive
DIGICAM_CAPTURE_TIMEOUT_S: int = 10  # NEF disk'e bu sürede inmezse iptal
DIGICAM_HTTP_TIMEOUT_S: int = 3
DIGICAM_HEARTBEAT_TIMEOUT_S: int = 1  # fast-fail when disconnected

# Storage
BACKUP_RETENTION_DAYS: int = 14
MIN_FREE_DISK_MB: int = 500

# Logging
LOG_LEVEL_FILE: str = "DEBUG"
LOG_LEVEL_CONSOLE: str = "INFO"

# UI
UI_FONT_SIZE_PT: int = 16
UI_LANGUAGE: str = "tr"

# Recent shots strip
RECENT_SHOTS_COUNT: int = 8
