"""repository.py için testler."""
from __future__ import annotations

import sqlite3

import pytest

from karotcam.db.repository import (
    AppStateRepository,
    BoxRepository,
    HoleRepository,
    PhotoRepository,
    ProjectRepository,
)
from karotcam.db.schema import apply_schema


@pytest.fixture
def db(memory_db: sqlite3.Connection) -> sqlite3.Connection:
    apply_schema(memory_db)
    return memory_db


def test_create_and_list_projects(db: sqlite3.Connection) -> None:
    repo = ProjectRepository(db)
    p_id = repo.create(ad="ESAN-Balya", sirket="ESAN", konum="Balya")
    assert p_id == 1
    projects = repo.list_all()
    assert len(projects) == 1
    assert projects[0].ad == "ESAN-Balya"


def test_create_hole_and_list_by_project(db: sqlite3.Connection) -> None:
    p_id = ProjectRepository(db).create(ad="P1", sirket=None, konum=None)
    hrepo = HoleRepository(db)
    h_id = hrepo.create(project_id=p_id, kuyu_adi="BLY-2024-156", tip="DDH")
    holes = hrepo.list_for_project(p_id)
    assert len(holes) == 1
    assert holes[0].id == h_id
    assert holes[0].kuyu_adi == "BLY-2024-156"


def test_box_unique_constraint_per_hole(db: sqlite3.Connection) -> None:
    p_id = ProjectRepository(db).create(ad="P", sirket=None, konum=None)
    h_id = HoleRepository(db).create(project_id=p_id, kuyu_adi="K1", tip=None)
    brepo = BoxRepository(db)
    brepo.create(hole_id=h_id, kutu_no=1, derinlik_baslangic=0.0, derinlik_bitis=3.0)
    with pytest.raises(sqlite3.IntegrityError):
        brepo.create(hole_id=h_id, kutu_no=1, derinlik_baslangic=3.0, derinlik_bitis=6.0)


def test_next_box_for_empty_hole_suggests_one(db: sqlite3.Connection) -> None:
    p_id = ProjectRepository(db).create(ad="P", sirket=None, konum=None)
    h_id = HoleRepository(db).create(project_id=p_id, kuyu_adi="K1", tip=None)
    brepo = BoxRepository(db)
    suggestion = brepo.next_box_for(h_id)
    assert suggestion == (1, 0.0)


def test_next_box_for_continues_from_last(db: sqlite3.Connection) -> None:
    p_id = ProjectRepository(db).create(ad="P", sirket=None, konum=None)
    h_id = HoleRepository(db).create(project_id=p_id, kuyu_adi="K1", tip=None)
    brepo = BoxRepository(db)
    brepo.create(hole_id=h_id, kutu_no=1, derinlik_baslangic=0.0, derinlik_bitis=3.0)
    brepo.create(hole_id=h_id, kutu_no=2, derinlik_baslangic=3.0, derinlik_bitis=6.5)
    assert brepo.next_box_for(h_id) == (3, 6.5)


def test_photo_insert_and_active_filter(db: sqlite3.Connection) -> None:
    p_id = ProjectRepository(db).create(ad="P", sirket=None, konum=None)
    h_id = HoleRepository(db).create(project_id=p_id, kuyu_adi="K1", tip=None)
    b_id = BoxRepository(db).create(
        hole_id=h_id, kutu_no=1, derinlik_baslangic=0.0, derinlik_bitis=3.0
    )
    prepo = PhotoRepository(db)
    p1 = prepo.create(box_id=b_id, dosya_yolu="/a.NEF", foto_tipi="KURU")
    p2 = prepo.create(box_id=b_id, dosya_yolu="/b.NEF", foto_tipi="KURU")
    prepo.soft_delete(p1, sebep="yeniden çekim")
    active = prepo.list_active_for_box(b_id)
    assert len(active) == 1
    assert active[0].id == p2


def test_recent_active_photos_across_boxes(db: sqlite3.Connection) -> None:
    p_id = ProjectRepository(db).create(ad="P", sirket=None, konum=None)
    h_id = HoleRepository(db).create(project_id=p_id, kuyu_adi="K1", tip=None)
    brepo = BoxRepository(db)
    prepo = PhotoRepository(db)
    for n in range(1, 4):
        b = brepo.create(
            hole_id=h_id,
            kutu_no=n,
            derinlik_baslangic=float(n - 1) * 3,
            derinlik_bitis=float(n) * 3,
        )
        prepo.create(box_id=b, dosya_yolu=f"/{n}.NEF", foto_tipi="KURU")
    recent = prepo.list_recent_for_hole(hole_id=h_id, limit=10)
    assert len(recent) == 3
    assert recent[0].dosya_yolu == "/3.NEF"  # newest first


def test_app_state_upsert(db: sqlite3.Connection) -> None:
    repo = AppStateRepository(db)
    assert repo.read() is None
    repo.write(last_project_id=None, last_hole_id=None, last_box_id=None)
    state = repo.read()
    assert state is not None
    assert state.last_project_id is None

    p_id = ProjectRepository(db).create(ad="P", sirket=None, konum=None)
    h_id = HoleRepository(db).create(project_id=p_id, kuyu_adi="K1", tip=None)
    b_id = BoxRepository(db).create(
        hole_id=h_id, kutu_no=1, derinlik_baslangic=0.0, derinlik_bitis=3.0
    )
    repo.write(last_project_id=p_id, last_hole_id=h_id, last_box_id=b_id)
    state = repo.read()
    assert state is not None
    assert (state.last_project_id, state.last_hole_id, state.last_box_id) == (p_id, h_id, b_id)
