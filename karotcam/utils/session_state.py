"""Açılış anında 'kaldığım yerden devam et' mantığı.

`SessionContext` UI'in app_state tablosundan tekrar kurması için yeterli olan
project/hole/box id üçlüsüdür. Eskimiş kayıtlar (silinmiş entity'ler) sessizce
düşürülür ve daha az dolu bir bağlam döner.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from karotcam.db.repository import (
    AppStateRepository,
    BoxRepository,
    HoleRepository,
    ProjectRepository,
)


@dataclass(frozen=True, slots=True)
class SessionContext:
    project_id: int
    hole_id: int | None
    box_id: int | None


def save_session(conn: sqlite3.Connection, ctx: SessionContext) -> None:
    AppStateRepository(conn).write(
        last_project_id=ctx.project_id,
        last_hole_id=ctx.hole_id,
        last_box_id=ctx.box_id,
    )


def load_session(conn: sqlite3.Connection) -> SessionContext | None:
    """Geçerli (var olan) entity referanslarına sahip bağlam döndür.

    Kayıt yoksa veya project_id artık var olmuyorsa None döner. Hole/box yoksa
    o alanlar None'a düşürülür.
    """
    state = AppStateRepository(conn).read()
    if state is None or state.last_project_id is None:
        return None
    if ProjectRepository(conn).get(state.last_project_id) is None:
        return None
    hole_id = state.last_hole_id
    box_id = state.last_box_id
    if hole_id is not None and HoleRepository(conn).get(hole_id) is None:
        hole_id = None
        box_id = None
    if box_id is not None and BoxRepository(conn).get(box_id) is None:
        box_id = None
    return SessionContext(
        project_id=state.last_project_id, hole_id=hole_id, box_id=box_id
    )
