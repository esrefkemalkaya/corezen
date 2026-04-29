"""schema.py için testler."""
from __future__ import annotations

import sqlite3

from karotcam.db.schema import CURRENT_VERSION, apply_schema, get_schema_version


def test_apply_schema_creates_all_tables(memory_db: sqlite3.Connection) -> None:
    apply_schema(memory_db)
    cur = memory_db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    tables = {row["name"] for row in cur.fetchall()}
    assert {
        "projects",
        "holes",
        "boxes",
        "photos",
        "calibrations",
        "app_state",
        "schema_version",
    }.issubset(tables)


def test_apply_schema_is_idempotent(memory_db: sqlite3.Connection) -> None:
    apply_schema(memory_db)
    apply_schema(memory_db)  # ikinci kez patlamamalı
    assert get_schema_version(memory_db) == CURRENT_VERSION


def test_app_state_single_row_constraint(memory_db: sqlite3.Connection) -> None:
    apply_schema(memory_db)
    memory_db.execute("INSERT INTO app_state (id) VALUES (1)")
    with pytest.raises(sqlite3.IntegrityError):
        memory_db.execute("INSERT INTO app_state (id) VALUES (2)")


def test_photos_iptal_default_zero(memory_db: sqlite3.Connection) -> None:
    apply_schema(memory_db)
    memory_db.execute(
        "INSERT INTO projects (ad) VALUES ('p')"
    )
    memory_db.execute(
        "INSERT INTO holes (project_id, kuyu_adi) VALUES (1, 'h')"
    )
    memory_db.execute(
        "INSERT INTO boxes (hole_id, kutu_no, derinlik_baslangic, derinlik_bitis) "
        "VALUES (1, 1, 0.0, 3.0)"
    )
    memory_db.execute(
        "INSERT INTO photos (box_id, dosya_yolu, foto_tipi) VALUES (1, '/x.NEF', 'KURU')"
    )
    row = memory_db.execute("SELECT iptal FROM photos WHERE id=1").fetchone()
    assert row["iptal"] == 0


import pytest  # noqa: E402  (used in raises)
