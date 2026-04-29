"""digiCamControl HTTP API istemcisi.

Komut formatı: `GET /?slc=<command>&param1=<p1>&param2=<p2>`
Live view: `GET /liveview.jpg` (tek frame)
"""
from __future__ import annotations

from typing import Protocol

import requests

from karotcam.utils.logger import get_logger

_log = get_logger(__name__)


class CameraConnectionError(RuntimeError):
    """digiCamControl ulaşılamıyor veya komut başarısız."""


class DigiCamClient(Protocol):
    def ping(self) -> bool: ...
    def capture(self) -> None: ...
    def set_session_folder(self, path: str) -> None: ...
    def get_liveview_jpeg(self) -> bytes | None: ...


class DigiCamHTTPClient:
    """Gerçek digiCamControl webserver istemcisi."""

    def __init__(self, *, base_url: str, timeout_s: int) -> None:
        self._base = base_url.rstrip("/")
        self._timeout = timeout_s
        self._session = requests.Session()

    def ping(self) -> bool:
        """Ucu kontrol et — `get lastfile` her zaman bir cevap döndürmeli."""
        try:
            r = self._session.get(
                self._base, params={"slc": "get", "param1": "lastfile"},
                timeout=self._timeout,
            )
            return r.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def capture(self) -> None:
        """Tek bir çekimi tetikle. Cevap kuyruğa alma onayıdır, dosya disk'e
        ayrı olarak inecektir."""
        try:
            r = self._session.get(
                self._base,
                params={"slc": "capture", "param1": "", "param2": ""},
                timeout=self._timeout,
            )
        except requests.exceptions.RequestException as e:
            raise CameraConnectionError(f"capture başarısız: {e}") from e
        if r.status_code != 200:
            raise CameraConnectionError(
                f"capture HTTP {r.status_code}: {r.text[:200]}"
            )

    def set_session_folder(self, path: str) -> None:
        """digiCamControl'un yazacağı klasörü ayarla."""
        try:
            r = self._session.get(
                self._base,
                params={"slc": "set", "param1": "session.folder", "param2": path},
                timeout=self._timeout,
            )
        except requests.exceptions.RequestException as e:
            raise CameraConnectionError(f"set session.folder başarısız: {e}") from e
        if r.status_code != 200:
            raise CameraConnectionError(
                f"set session.folder HTTP {r.status_code}"
            )

    def get_liveview_jpeg(self) -> bytes | None:
        """Tek liveview frame'i döndür. Hata halinde None (sessiz)."""
        try:
            r = self._session.get(
                f"{self._base}/liveview.jpg", timeout=self._timeout
            )
            if r.status_code != 200:
                return None
            return r.content
        except requests.exceptions.RequestException:
            return None


class MockDigiCamClient:
    """Sadece testlerde kullanılır. Hep başarılı görünür."""

    def __init__(self) -> None:
        self.captures: int = 0
        self.session_folder: str | None = None

    def ping(self) -> bool:
        return True

    def capture(self) -> None:
        self.captures += 1

    def set_session_folder(self, path: str) -> None:
        self.session_folder = path

    def get_liveview_jpeg(self) -> bytes | None:
        return b""
