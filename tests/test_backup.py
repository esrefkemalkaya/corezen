"""backup.py için testler."""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from pathlib import Path

from karotcam.db.backup import backup_if_needed, prune_old_backups


def _seed_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE x (a INTEGER)")
    conn.execute("INSERT INTO x VALUES (1)")
    conn.commit()
    conn.close()


def test_backup_if_needed_creates_today_file(tmp_path: Path) -> None:
    db = tmp_path / "k.db"
    backups = tmp_path / "backups"
    _seed_db(db)
    result = backup_if_needed(db_path=db, backups_dir=backups)
    assert result is not None
    assert result.exists()
    assert date.today().isoformat() in result.name


def test_backup_if_needed_skips_when_today_exists(tmp_path: Path) -> None:
    db = tmp_path / "k.db"
    backups = tmp_path / "backups"
    _seed_db(db)
    first = backup_if_needed(db_path=db, backups_dir=backups)
    assert first is not None
    second = backup_if_needed(db_path=db, backups_dir=backups)
    assert second is None  # already done today


def test_prune_old_backups_keeps_recent(tmp_path: Path) -> None:
    backups = tmp_path / "backups"
    backups.mkdir()
    today = date.today()
    keep = backups / f"karotcam-{today.isoformat()}.db"
    old = backups / f"karotcam-{(today - timedelta(days=20)).isoformat()}.db"
    keep.write_bytes(b"x")
    old.write_bytes(b"x")
    deleted = prune_old_backups(backups_dir=backups, retention_days=14)
    assert keep.exists()
    assert not old.exists()
    assert deleted == [old]
