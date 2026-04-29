"""NEF dosyalarının gömülü JPEG önizlemesini çıkar.

Her Nikon NEF içinde tam çözünürlüklü bir JPEG preview vardır. rawpy.imread
ile açıp .extract_thumb() ile çıkarmak, tam RAW decode'dan ~100x daha hızlı.
"""
from __future__ import annotations

from pathlib import Path

import rawpy

from karotcam.utils.logger import get_logger

_log = get_logger(__name__)


def extract_embedded_jpeg(nef_path: Path) -> bytes | None:
    """NEF içinden JPEG byte'larını döndür. Başarısızlık halinde None + log."""
    try:
        with rawpy.imread(str(nef_path)) as raw:
            thumb = raw.extract_thumb()
            if thumb.format == rawpy.ThumbFormat.JPEG:
                return bytes(thumb.data)
            _log.warning("NEF thumb JPEG değil: %s (format=%s)", nef_path, thumb.format)
            return None
    except Exception:
        _log.exception("NEF preview çıkarılamadı: %s", nef_path)
        return None
