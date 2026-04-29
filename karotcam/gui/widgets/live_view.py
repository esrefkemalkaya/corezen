"""Live view — digiCamControl'dan periyodik JPEG çek, QLabel'da göster.

Polling QTimer main thread'de yaşar. HTTP isteği `requests` ile blokludur ama
3 sn timeout ile sınırlıdır; tipik durumda <30 ms döner.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QLabel, QWidget

from karotcam.camera.digicam_client import DigiCamClient
from karotcam.utils.logger import get_logger

_log = get_logger(__name__)


class LiveView(QLabel):
    """Live view görüntüsünü tutan QLabel. start()/stop() ile kontrol edilir."""

    def __init__(
        self,
        *,
        client: DigiCamClient,
        poll_ms: int,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._client = client
        self.setMinimumSize(800, 450)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background-color: #000000;")
        self.setText("Live view bekleniyor...")
        self._timer = QTimer(self)
        self._timer.setInterval(poll_ms)
        self._timer.timeout.connect(self._poll)

    def start(self) -> None:
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()

    def _poll(self) -> None:
        data = self._client.get_liveview_jpeg()
        if not data:
            return
        pix = QPixmap()
        if not pix.loadFromData(data, "JPG"):
            return
        scaled = pix.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.setPixmap(scaled)
