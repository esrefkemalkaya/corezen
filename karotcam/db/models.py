"""DB satırları için dataclass'lar.

Her dataclass `from_row(sqlite3.Row)` classmethod'u ile satırdan üretilir.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from typing import Self


@dataclass(frozen=True, slots=True)
class Project:
    id: int
    ad: str
    sirket: str | None
    konum: str | None
    baslangic_tarihi: date | None
    olusturma: datetime | None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Self:
        return cls(
            id=row["id"],
            ad=row["ad"],
            sirket=row["sirket"],
            konum=row["konum"],
            baslangic_tarihi=_parse_date(row["baslangic_tarihi"]),
            olusturma=_parse_dt(row["olusturma"]),
        )


@dataclass(frozen=True, slots=True)
class Hole:
    id: int
    project_id: int
    kuyu_adi: str
    tip: str | None
    planlanan_uzunluk: float | None
    durum: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Self:
        return cls(
            id=row["id"],
            project_id=row["project_id"],
            kuyu_adi=row["kuyu_adi"],
            tip=row["tip"],
            planlanan_uzunluk=row["planlanan_uzunluk"],
            durum=row["durum"],
        )


@dataclass(frozen=True, slots=True)
class Box:
    id: int
    hole_id: int
    kutu_no: int
    derinlik_baslangic: float
    derinlik_bitis: float
    kutu_tipi: str | None
    foto_durumu: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Self:
        return cls(
            id=row["id"],
            hole_id=row["hole_id"],
            kutu_no=row["kutu_no"],
            derinlik_baslangic=row["derinlik_baslangic"],
            derinlik_bitis=row["derinlik_bitis"],
            kutu_tipi=row["kutu_tipi"],
            foto_durumu=row["foto_durumu"],
        )


@dataclass(frozen=True, slots=True)
class Photo:
    id: int
    box_id: int
    dosya_yolu: str
    foto_tipi: str
    cekim_tarihi: datetime | None
    iptal: int
    iptal_sebep: str | None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Self:
        return cls(
            id=row["id"],
            box_id=row["box_id"],
            dosya_yolu=row["dosya_yolu"],
            foto_tipi=row["foto_tipi"],
            cekim_tarihi=_parse_dt(row["cekim_tarihi"]),
            iptal=row["iptal"],
            iptal_sebep=row["iptal_sebep"],
        )


@dataclass(frozen=True, slots=True)
class AppState:
    last_project_id: int | None
    last_hole_id: int | None
    last_box_id: int | None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Self:
        return cls(
            last_project_id=row["last_project_id"],
            last_hole_id=row["last_hole_id"],
            last_box_id=row["last_box_id"],
        )


def _parse_dt(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value.replace(" ", "T"))


def _parse_date(value: str | None) -> date | None:
    if value is None:
        return None
    return date.fromisoformat(value)
