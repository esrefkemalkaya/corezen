"""Live view — digiCamControl'dan periyodik JPEG çek, QLabel'da göster.

HTTP isteği ayrı bir QThread'de yapılır; GUI thread'i asla bloklanmaz.
Thread stop/start döngüsünü desteklemek için her start() çağrısında yeni
bir QThread oluşturulur — Qt bir kez quit() edilen thread'i restart edemez.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, QObject, QThread, QTimer, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QLabel, QWidget

from karotcam.camera.digicam_client import DigiCamClient
from karotcam.utils.logger import get_logger

_log = get_logger(__name__)


class _FetchWorker(QObject):
    """Yalnızca fetch thread'inde yaşar; JPEG baytlarını alır ve iletir."""

    frame_ready = pyqtSignal(bytes)

    def __init__(self, client: DigiCamClient) -> None:
        super().__init__()
        self._client = client

    @pyqtSlot()
    def fetch(self) -> None:
        data = self._client.get_liveview_jpeg()
        if data:
            self.frame_ready.emit(data)


class LiveView(QLabel):
    """Live view görüntüsünü tutan QLabel. start()/stop() ile kontrol edilir."""

    _trigger_fetch = pyqtSignal()

    def __init__(
        self,
        *,
        client: DigiCamClient,
        poll_ms: int,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._client = client
        self._poll_ms = poll_ms
        self.setMinimumSize(800, 450)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background-color: #000000;")
        self.setText("Live view bekleniyor...")

        self._thread: QThread | None = None
        self._worker: _FetchWorker | None = None

        self._timer = QTimer(self)
        self._timer.setInterval(poll_ms)
        self._timer.timeout.connect(self._trigger_fetch)

    def start(self) -> None:
        if self._timer.isActive():
            return  # zaten çalışıyor
        self._start_thread()
        self._timer.start()

    def stop(self) -> None:
        if not self._timer.isActive():
            return
        self._timer.stop()
        self._stop_thread()

    def _start_thread(self) -> None:
        self._thread = QThread(self)
        self._worker = _FetchWorker(self._client)
        self._worker.moveToThread(self._thread)
        self._trigger_fetch.connect(self._worker.fetch)
        self._worker.frame_ready.connect(self._on_frame)
        self._thread.start()

    def _stop_thread(self) -> None:
        if self._thread is None:
            return
        try:
            self._trigger_fetch.disconnect(self._worker.fetch)  # type: ignore[union-attr]
        except RuntimeError:
            pass
        self._thread.quit()
        self._thread.wait(2000)
        self._thread = None
        self._worker = None

    @pyqtSlot(bytes)
    def _on_frame(self, data: bytes) -> None:
        pix = QPixmap()
        if not pix.loadFromData(data, "JPG"):
            return
        scaled = pix.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.setPixmap(scaled)
