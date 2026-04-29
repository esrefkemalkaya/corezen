"""Paylaşılan pytest fixture'ları."""
from __future__ import annotations

import sqlite3
from collections.abc import Iterator

import pytest


@pytest.fixture
def memory_db() -> Iterator[sqlite3.Connection]:
    """Test başına temiz in-memory SQLite bağlantısı."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    yield conn
    conn.close()
