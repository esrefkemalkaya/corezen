"""Bağlantı sağlığı zamanlayıcısı.

Main thread'de yaşar. `interval_ms` aralıklarla `client.ping()` çağırır,
durum değiştiğinde `connection_changed(bool)` sinyali yayar.
"""
from __future__ import annotations

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from karotcam.camera.digicam_client import DigiCamClient
from karotcam.utils.logger import get_logger

_log = get_logger(__name__)


class Heartbeat(QObject):
    connection_changed = pyqtSignal(bool)

    def __init__(
        self, *, client: DigiCamClient, interval_ms: int, parent: QObject | None = None
    ) -> None:
        super().__init__(parent)
        self._client = client
        self._timer = QTimer(self)
        self._timer.setInterval(interval_ms)
        self._timer.timeout.connect(self._tick)
        self._last_state: bool | None = None

    def start(self) -> None:
        self._tick()  # ilk değerlendirmeyi hemen yap
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()

    def _tick(self) -> None:
        ok = self._client.ping()
        if ok != self._last_state:
            _log.info("kamera bağlantısı: %s", "BAĞLI" if ok else "YOK")
            self._last_state = ok
            self.connection_changed.emit(ok)
