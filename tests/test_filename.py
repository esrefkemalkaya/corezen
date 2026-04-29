"""filename.py için testler."""
from __future__ import annotations

from datetime import datetime

import pytest

from karotcam.utils.filename import (
    PhotoNameInputs,
    build_photo_filename,
    sanitize_kuyu_adi,
)


def test_sanitize_keeps_alnum_and_dash() -> None:
    assert sanitize_kuyu_adi("BLY-2024-156") == "BLY-2024-156"


def test_sanitize_replaces_invalid_chars() -> None:
    assert sanitize_kuyu_adi("BLY 2024/156") == "BLY_2024_156"


def test_sanitize_strips_unicode() -> None:
    assert sanitize_kuyu_adi("KÜYÜ-1") == "K_Y_-1"


def test_build_basic_filename() -> None:
    inp = PhotoNameInputs(
        kuyu_adi="BLY-2024-156",
        kutu_no=23,
        derinlik_baslangic=145.20,
        derinlik_bitis=148.50,
        tip="KURU",
        when=datetime(2026, 4, 29, 14, 30),
    )
    assert build_photo_filename(inp) == (
        "BLY-2024-156_K0023_145.20-148.50_KURU_20260429-1430.NEF"
    )


def test_build_zero_pads_box_number() -> None:
    inp = PhotoNameInputs(
        kuyu_adi="X",
        kutu_no=1,
        derinlik_baslangic=0.0,
        derinlik_bitis=3.0,
        tip="KURU",
        when=datetime(2026, 1, 2, 3, 4),
    )
    assert build_photo_filename(inp) == "X_K0001_0.00-3.00_KURU_20260102-0304.NEF"


def test_build_two_decimal_depths() -> None:
    inp = PhotoNameInputs(
        kuyu_adi="X",
        kutu_no=1,
        derinlik_baslangic=12.345,
        derinlik_bitis=15.678,
        tip="KURU",
        when=datetime(2026, 1, 2, 3, 4),
    )
    name = build_photo_filename(inp)
    assert "_12.34-15.68_" in name or "_12.35-15.68_" in name  # banker rounding ok


def test_build_truncates_when_path_too_long() -> None:
    inp = PhotoNameInputs(
        kuyu_adi="A" * 300,
        kutu_no=1,
        derinlik_baslangic=0.0,
        derinlik_bitis=3.0,
        tip="KURU",
        when=datetime(2026, 1, 2, 3, 4),
    )
    name = build_photo_filename(inp, max_total_len=100)
    assert len(name) <= 100
    assert name.endswith(".NEF")
    assert "_K0001_" in name


def test_build_rejects_bad_tip() -> None:
    inp = PhotoNameInputs(
        kuyu_adi="X",
        kutu_no=1,
        derinlik_baslangic=0.0,
        derinlik_bitis=3.0,
        tip="HATALI",
        when=datetime(2026, 1, 2, 3, 4),
    )
    with pytest.raises(ValueError):
        build_photo_filename(inp)


def test_build_rejects_negative_box() -> None:
    inp = PhotoNameInputs(
        kuyu_adi="X",
        kutu_no=0,
        derinlik_baslangic=0.0,
        derinlik_bitis=3.0,
        tip="KURU",
        when=datetime(2026, 1, 2, 3, 4),
    )
    with pytest.raises(ValueError):
        build_photo_filename(inp)
