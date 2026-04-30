"""Bağlantı sağlığı zamanlayıcısı.

HTTP çağrısı ayrı bir QThread'de yapılır; GUI thread'i asla bloklanmaz.
Durum değiştiğinde `connection_changed(bool)` sinyali main thread'e yayılır.
"""
from __future__ import annotations

from PyQt6.QtCore import QObject, QThread, QTimer, pyqtSignal, pyqtSlot

from karotcam.camera.digicam_client import DigiCamClient
from karotcam.utils.logger import get_logger

_log = get_logger(__name__)


class _PingWorker(QObject):
    """Yalnızca heartbeat thread'inde yaşar; ping yapar ve sonucu iletir."""

    result = pyqtSignal(bool)

    def __init__(self, client: DigiCamClient) -> None:
        super().__init__()
        self._client = client

    @pyqtSlot()
    def do_ping(self) -> None:
        ok = self._client.ping()
        self.result.emit(ok)


class Heartbeat(QObject):
    connection_changed = pyqtSignal(bool)

    def __init__(
        self, *, client: DigiCamClient, interval_ms: int, parent: QObject | None = None
    ) -> None:
        super().__init__(parent)
        self._interval_ms = interval_ms
        self._last_state: bool | None = None

        self._thread = QThread(self)
        self._worker = _PingWorker(client)
        self._worker.moveToThread(self._thread)
        self._worker.result.connect(self._on_result)

        self._timer = QTimer(self)
        self._timer.setInterval(interval_ms)
        self._timer.timeout.connect(self._worker.do_ping)

        self._thread.start()

    def start(self) -> None:
        self._worker.do_ping()  # ilk değerlendirmeyi hemen yap
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()
        self._thread.quit()
        self._thread.wait(2000)

    @pyqtSlot(bool)
    def _on_result(self, ok: bool) -> None:
        if ok != self._last_state:
            _log.info("kamera bağlantısı: %s", "BAĞLI" if ok else "YOK")
            self._last_state = ok
            self.connection_changed.emit(ok)
