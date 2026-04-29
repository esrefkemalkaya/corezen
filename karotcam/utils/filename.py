"""Çekim dosyası ad üreteci.

Şablon: `{KUYU_ADI}_K{NNNN}_{DER_BAS}-{DER_BIT}_{TIP}_{YYYYMMDD-HHMM}.NEF`
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime

_VALID_CHARS = re.compile(r"[^A-Za-z0-9-]")
_ALLOWED_TIPS = frozenset({"KURU", "ISLAK", "PANO"})
_DEFAULT_MAX_LEN = 240  # Windows MAX_PATH (260) - güvenlik payı


@dataclass(frozen=True, slots=True)
class PhotoNameInputs:
    kuyu_adi: str
    kutu_no: int
    derinlik_baslangic: float
    derinlik_bitis: float
    tip: str
    when: datetime


def sanitize_kuyu_adi(raw: str) -> str:
    """A-Z, a-z, 0-9 ve '-' dışındaki karakterleri '_' ile değiştir."""
    return _VALID_CHARS.sub("_", raw)


def build_photo_filename(
    inp: PhotoNameInputs, *, max_total_len: int = _DEFAULT_MAX_LEN
) -> str:
    """İsim üret. Çok uzunsa kuyu_adi'yi kısalt + hash suffix ekle."""
    if inp.tip not in _ALLOWED_TIPS:
        raise ValueError(f"geçersiz tip: {inp.tip!r}")
    if inp.kutu_no < 1:
        raise ValueError(f"kutu_no >= 1 olmalı, alındı: {inp.kutu_no}")

    base = sanitize_kuyu_adi(inp.kuyu_adi)
    ts = inp.when.strftime("%Y%m%d-%H%M")
    suffix = (
        f"_K{inp.kutu_no:04d}"
        f"_{inp.derinlik_baslangic:.2f}-{inp.derinlik_bitis:.2f}"
        f"_{inp.tip}_{ts}.NEF"
    )
    full = base + suffix
    if len(full) <= max_total_len:
        return full

    # Kısalt: hash 8 karakter, '_' ayraç
    digest = hashlib.sha1(base.encode("utf-8")).hexdigest()[:8]
    overflow = len(full) - max_total_len + len("_") + len(digest)
    keep = max(1, len(base) - overflow)
    return f"{base[:keep]}_{digest}{suffix}"
