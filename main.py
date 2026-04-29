"""KarotCam giriş noktası."""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

import config
from karotcam.db.backup import backup_if_needed, prune_old_backups
from karotcam.db.schema import apply_schema, enable_wal
from karotcam.gui.main_window import MainWindow
from karotcam.utils.logger import get_logger, setup_logging
from karotcam.utils.session_state import load_session


def _bootstrap_dirs() -> None:
    for d in (
        config.DATA_DIR,
        config.PHOTOS_RAW_DIR,
        config.BACKUPS_DIR,
        config.LOGS_DIR,
    ):
        d.mkdir(parents=True, exist_ok=True)


def _open_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(config.DB_PATH))
    conn.row_factory = sqlite3.Row
    enable_wal(conn)
    apply_schema(conn)
    return conn


def _load_qss() -> str:
    qss_path = Path(__file__).parent / "karotcam" / "gui" / "styles.qss"
    return qss_path.read_text(encoding="utf-8")


def main() -> int:
    _bootstrap_dirs()
    setup_logging()
    log = get_logger("main")
    log.info("KarotCam %s başlatılıyor", config.APP_VERSION)

    backup_if_needed(db_path=config.DB_PATH, backups_dir=config.BACKUPS_DIR)
    prune_old_backups(
        backups_dir=config.BACKUPS_DIR, retention_days=config.BACKUP_RETENTION_DAYS
    )

    conn = _open_db()
    restored = load_session(conn)

    app = QApplication(sys.argv)
    app.setApplicationName(config.APP_NAME)
    app.setStyleSheet(_load_qss())

    window = MainWindow(conn)
    window.show()
    window.start(restored)

    code = app.exec()
    conn.close()
    return code


if __name__ == "__main__":
    sys.exit(main())
