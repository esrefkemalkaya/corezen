"""Veritabanı yedekleme yardımcıları."""
from __future__ import annotations

import shutil
from datetime import date, datetime, timedelta
from pathlib import Path

from karotcam.utils.logger import get_logger

_log = get_logger(__name__)


def _backup_path_for(backups_dir: Path, day: date) -> Path:
    return backups_dir / f"karotcam-{day.isoformat()}.db"


def backup_if_needed(*, db_path: Path, backups_dir: Path) -> Path | None:
    """Bugün için yedek yoksa kopya oluştur. Var olan dosya döndürmez (None)."""
    backups_dir.mkdir(parents=True, exist_ok=True)
    target = _backup_path_for(backups_dir, date.today())
    if target.exists():
        return None
    if not db_path.exists():
        _log.info("backup atlandı: kaynak DB yok (%s)", db_path)
        return None
    shutil.copy2(db_path, target)
    _log.info("DB yedeği oluşturuldu: %s", target)
    return target


def prune_old_backups(*, backups_dir: Path, retention_days: int) -> list[Path]:
    """retention_days'den eski yedekleri sil. Silinenleri döndür."""
    if not backups_dir.exists():
        return []
    cutoff = date.today() - timedelta(days=retention_days)
    deleted: list[Path] = []
    for f in backups_dir.glob("karotcam-*.db"):
        try:
            day_str = f.stem.removeprefix("karotcam-")
            d = datetime.strptime(day_str, "%Y-%m-%d").date()
        except ValueError:
            continue
        if d < cutoff:
            f.unlink()
            deleted.append(f)
            _log.info("eski yedek silindi: %s", f)
    return deleted
