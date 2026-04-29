"""Entity başına Repository sınıfları.

Her metod kısa ömürlü işlem yürütür ve kendi commit'ini yapar. Sınıflar tek bir
sqlite3.Connection paylaşır (main thread üzerinde).
"""
from __future__ import annotations

import sqlite3
from typing import Any

from karotcam.db.models import AppState, Box, Hole, Photo, Project


class ProjectRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._c = conn

    def create(self, *, ad: str, sirket: str | None, konum: str | None) -> int:
        cur = self._c.execute(
            "INSERT INTO projects (ad, sirket, konum) VALUES (?, ?, ?)",
            (ad, sirket, konum),
        )
        self._c.commit()
        return int(cur.lastrowid)

    def list_all(self) -> list[Project]:
        rows = self._c.execute(
            "SELECT * FROM projects ORDER BY olusturma DESC"
        ).fetchall()
        return [Project.from_row(r) for r in rows]

    def get(self, project_id: int) -> Project | None:
        row = self._c.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
        return Project.from_row(row) if row else None


class HoleRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._c = conn

    def create(self, *, project_id: int, kuyu_adi: str, tip: str | None) -> int:
        cur = self._c.execute(
            "INSERT INTO holes (project_id, kuyu_adi, tip) VALUES (?, ?, ?)",
            (project_id, kuyu_adi, tip),
        )
        self._c.commit()
        return int(cur.lastrowid)

    def list_for_project(self, project_id: int) -> list[Hole]:
        rows = self._c.execute(
            "SELECT * FROM holes WHERE project_id = ? ORDER BY olusturma DESC",
            (project_id,),
        ).fetchall()
        return [Hole.from_row(r) for r in rows]

    def get(self, hole_id: int) -> Hole | None:
        row = self._c.execute(
            "SELECT * FROM holes WHERE id = ?", (hole_id,)
        ).fetchone()
        return Hole.from_row(row) if row else None


class BoxRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._c = conn

    def create(
        self,
        *,
        hole_id: int,
        kutu_no: int,
        derinlik_baslangic: float,
        derinlik_bitis: float,
    ) -> int:
        cur = self._c.execute(
            "INSERT INTO boxes (hole_id, kutu_no, derinlik_baslangic, derinlik_bitis) "
            "VALUES (?, ?, ?, ?)",
            (hole_id, kutu_no, derinlik_baslangic, derinlik_bitis),
        )
        self._c.commit()
        return int(cur.lastrowid)

    def get(self, box_id: int) -> Box | None:
        row = self._c.execute(
            "SELECT * FROM boxes WHERE id = ?", (box_id,)
        ).fetchone()
        return Box.from_row(row) if row else None

    def list_for_hole(self, hole_id: int) -> list[Box]:
        rows = self._c.execute(
            "SELECT * FROM boxes WHERE hole_id = ? ORDER BY kutu_no",
            (hole_id,),
        ).fetchall()
        return [Box.from_row(r) for r in rows]

    def next_box_for(self, hole_id: int) -> tuple[int, float]:
        """Sıradaki (kutu_no, derinlik_baslangic) önerisi.

        Boş kuyu için (1, 0.0). Aksi halde (max_kutu_no + 1, son derinlik_bitis).
        """
        row = self._c.execute(
            "SELECT kutu_no, derinlik_bitis FROM boxes "
            "WHERE hole_id = ? ORDER BY kutu_no DESC LIMIT 1",
            (hole_id,),
        ).fetchone()
        if row is None:
            return (1, 0.0)
        return (int(row["kutu_no"]) + 1, float(row["derinlik_bitis"]))


class PhotoRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._c = conn

    def create(self, *, box_id: int, dosya_yolu: str, foto_tipi: str) -> int:
        cur = self._c.execute(
            "INSERT INTO photos (box_id, dosya_yolu, foto_tipi) VALUES (?, ?, ?)",
            (box_id, dosya_yolu, foto_tipi),
        )
        self._c.commit()
        return int(cur.lastrowid)

    def soft_delete(self, photo_id: int, *, sebep: str) -> None:
        self._c.execute(
            "UPDATE photos SET iptal = 1, iptal_sebep = ? WHERE id = ?",
            (sebep, photo_id),
        )
        self._c.commit()

    def list_active_for_box(self, box_id: int) -> list[Photo]:
        rows = self._c.execute(
            "SELECT * FROM photos WHERE box_id = ? AND iptal = 0 "
            "ORDER BY cekim_tarihi DESC, id DESC",
            (box_id,),
        ).fetchall()
        return [Photo.from_row(r) for r in rows]

    def list_recent_for_hole(self, *, hole_id: int, limit: int) -> list[Photo]:
        rows = self._c.execute(
            "SELECT photos.* FROM photos "
            "JOIN boxes ON photos.box_id = boxes.id "
            "WHERE boxes.hole_id = ? AND photos.iptal = 0 "
            "ORDER BY photos.cekim_tarihi DESC, photos.id DESC LIMIT ?",
            (hole_id, limit),
        ).fetchall()
        return [Photo.from_row(r) for r in rows]

    def latest_active_for_box(self, box_id: int) -> Photo | None:
        rows = self.list_active_for_box(box_id)
        return rows[0] if rows else None


class AppStateRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._c = conn

    def read(self) -> AppState | None:
        row = self._c.execute("SELECT * FROM app_state WHERE id = 1").fetchone()
        return AppState.from_row(row) if row else None

    def write(
        self,
        *,
        last_project_id: int | None,
        last_hole_id: int | None,
        last_box_id: int | None,
    ) -> None:
        self._c.execute(
            "INSERT INTO app_state (id, last_project_id, last_hole_id, last_box_id, updated) "
            "VALUES (1, ?, ?, ?, CURRENT_TIMESTAMP) "
            "ON CONFLICT(id) DO UPDATE SET "
            "last_project_id = excluded.last_project_id, "
            "last_hole_id = excluded.last_hole_id, "
            "last_box_id = excluded.last_box_id, "
            "updated = CURRENT_TIMESTAMP",
            (last_project_id, last_hole_id, last_box_id),
        )
        self._c.commit()
