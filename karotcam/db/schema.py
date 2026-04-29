"""SQLite şema oluşturma ve sürüm yönetimi."""
from __future__ import annotations

import sqlite3

CURRENT_VERSION = 1

_SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY,
    ad TEXT NOT NULL,
    sirket TEXT,
    konum TEXT,
    baslangic_tarihi DATE,
    olusturma DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS holes (
    id INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL,
    kuyu_adi TEXT NOT NULL,
    tip TEXT,
    planlanan_uzunluk REAL,
    durum TEXT DEFAULT 'aktif',
    olusturma DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

CREATE TABLE IF NOT EXISTS boxes (
    id INTEGER PRIMARY KEY,
    hole_id INTEGER NOT NULL,
    kutu_no INTEGER NOT NULL,
    derinlik_baslangic REAL NOT NULL,
    derinlik_bitis REAL NOT NULL,
    kutu_tipi TEXT,
    foto_durumu TEXT DEFAULT 'beklemede',
    olusturma DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (hole_id) REFERENCES holes(id),
    UNIQUE(hole_id, kutu_no)
);

CREATE TABLE IF NOT EXISTS photos (
    id INTEGER PRIMARY KEY,
    box_id INTEGER NOT NULL,
    dosya_yolu TEXT NOT NULL,
    foto_tipi TEXT NOT NULL,
    cekim_tarihi DATETIME DEFAULT CURRENT_TIMESTAMP,
    kamera_ayarlari_json TEXT,
    duzeltme_uygulandi INTEGER DEFAULT 0,
    duzeltilmis_yol TEXT,
    olcek_mm_per_pixel REAL,
    iptal INTEGER DEFAULT 0,
    iptal_sebep TEXT,
    FOREIGN KEY (box_id) REFERENCES boxes(id)
);

CREATE TABLE IF NOT EXISTS calibrations (
    id INTEGER PRIMARY KEY,
    ad TEXT NOT NULL,
    kamera_modeli TEXT,
    lens_modeli TEXT,
    mesafe_cm REAL,
    perspektif_matrisi_json TEXT,
    distortion_coefs_json TEXT,
    camera_matrix_json TEXT,
    olcek_mm_per_pixel REAL,
    olusturma DATETIME DEFAULT CURRENT_TIMESTAMP,
    aktif INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS app_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    last_project_id INTEGER,
    last_hole_id INTEGER,
    last_box_id INTEGER,
    updated DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (last_project_id) REFERENCES projects(id) ON DELETE SET NULL,
    FOREIGN KEY (last_hole_id) REFERENCES holes(id) ON DELETE SET NULL,
    FOREIGN KEY (last_box_id) REFERENCES boxes(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""


def get_schema_version(conn: sqlite3.Connection) -> int:
    """En yüksek uygulanmış sürüm numarası, yoksa 0."""
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
    )
    if cur.fetchone() is None:
        return 0
    cur = conn.execute("SELECT MAX(version) AS v FROM schema_version")
    row = cur.fetchone()
    return int(row["v"] or 0) if row else 0


def apply_schema(conn: sqlite3.Connection) -> None:
    """Şemayı idempotent şekilde uygula. WAL etkinleştir."""
    conn.executescript(_SCHEMA_V1)
    if get_schema_version(conn) < CURRENT_VERSION:
        conn.execute(
            "INSERT OR IGNORE INTO schema_version (version) VALUES (?)",
            (CURRENT_VERSION,),
        )
    conn.commit()


def enable_wal(conn: sqlite3.Connection) -> None:
    """SQLite WAL modunu aç (file-backed bağlantılarda kullan)."""
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
