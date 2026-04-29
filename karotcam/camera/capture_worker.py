"""CaptureWorker — kamera çekim komutlarını işleyen QThread.

Main thread `request_capture()` slot'unu sinyalle çağırır. Worker thread
HTTP `capture` çağırır ve hata olursa `capture_failed(str)` sinyali yayar.
"""
from __future__ import annotations

from PyQt6.QtCore import QObject, QThread, pyqtSignal, pyqtSlot

from karotcam.camera.digicam_client import (
    CameraConnectionError,
    DigiCamClient,
)
from karotcam.utils.logger import get_logger

_log = get_logger(__name__)


class CaptureWorker(QObject):
    """QThread'e taşınacak worker."""

    capture_failed = pyqtSignal(str)
    capture_dispatched = pyqtSignal()  # HTTP çağrısı başarılı, NEF gelmesi bekleniyor

    def __init__(self, client: DigiCamClient) -> None:
        super().__init__()
        self._client = client

    @pyqtSlot()
    def request_capture(self) -> None:
        try:
            self._client.capture()
            self.capture_dispatched.emit()
        except CameraConnectionError as e:
            _log.warning("çekim başarısız: %s", e)
            self.capture_failed.emit(str(e))
        except Exception as e:
            _log.exception("çekim sırasında beklenmeyen hata")
            self.capture_failed.emit(str(e))


def make_capture_thread(client: DigiCamClient) -> tuple[QThread, CaptureWorker]:
    """Worker'ı yeni bir QThread'e bağla. Caller `thread.start()` çağırmalı."""
    thread = QThread()
    worker = CaptureWorker(client)
    worker.moveToThread(thread)
    return thread, worker
