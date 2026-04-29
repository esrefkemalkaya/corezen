"""session_state.py için testler."""
from __future__ import annotations

import sqlite3

from karotcam.db.repository import (
    BoxRepository,
    HoleRepository,
    ProjectRepository,
)
from karotcam.db.schema import apply_schema
from karotcam.utils.session_state import (
    SessionContext,
    load_session,
    save_session,
)


def _seed(conn: sqlite3.Connection) -> tuple[int, int, int]:
    apply_schema(conn)
    p = ProjectRepository(conn).create(ad="P", sirket=None, konum=None)
    h = HoleRepository(conn).create(project_id=p, kuyu_adi="K1", tip=None)
    b = BoxRepository(conn).create(
        hole_id=h, kutu_no=1, derinlik_baslangic=0.0, derinlik_bitis=3.0
    )
    return p, h, b


def test_load_session_returns_none_when_empty(memory_db: sqlite3.Connection) -> None:
    apply_schema(memory_db)
    assert load_session(memory_db) is None


def test_save_then_load_roundtrip(memory_db: sqlite3.Connection) -> None:
    p, h, b = _seed(memory_db)
    save_session(
        memory_db,
        SessionContext(project_id=p, hole_id=h, box_id=b),
    )
    ctx = load_session(memory_db)
    assert ctx == SessionContext(project_id=p, hole_id=h, box_id=b)


def test_load_session_drops_stale_box(memory_db: sqlite3.Connection) -> None:
    p, h, b = _seed(memory_db)
    save_session(
        memory_db,
        SessionContext(project_id=p, hole_id=h, box_id=b),
    )
    # Kutuyu sil → load_session yine project+hole vermeli, box_id = None
    memory_db.execute("DELETE FROM boxes WHERE id = ?", (b,))
    memory_db.commit()
    ctx = load_session(memory_db)
    assert ctx is not None
    assert ctx.project_id == p
    assert ctx.hole_id == h
    assert ctx.box_id is None


def test_load_session_drops_stale_hole(memory_db: sqlite3.Connection) -> None:
    p, h, b = _seed(memory_db)
    save_session(
        memory_db,
        SessionContext(project_id=p, hole_id=h, box_id=b),
    )
    memory_db.execute("DELETE FROM boxes WHERE id = ?", (b,))
    memory_db.execute("DELETE FROM holes WHERE id = ?", (h,))
    memory_db.commit()
    ctx = load_session(memory_db)
    assert ctx is not None
    assert ctx.project_id == p
    assert ctx.hole_id is None
    assert ctx.box_id is None


def test_load_session_drops_stale_project(memory_db: sqlite3.Connection) -> None:
    p, h, b = _seed(memory_db)
    save_session(
        memory_db,
        SessionContext(project_id=p, hole_id=h, box_id=b),
    )
    memory_db.execute("DELETE FROM boxes WHERE id = ?", (b,))
    memory_db.execute("DELETE FROM holes WHERE id = ?", (h,))
    memory_db.execute("DELETE FROM projects WHERE id = ?", (p,))
    memory_db.commit()
    assert load_session(memory_db) is None
