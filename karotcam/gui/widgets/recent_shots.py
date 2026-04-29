"""Son N çekimi gösteren yatay küçük resim şeridi."""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QWidget

from karotcam.utils.logger import get_logger
from karotcam.utils.nef_preview import extract_embedded_jpeg

_log = get_logger(__name__)
_THUMB_HEIGHT = 96


class RecentShots(QWidget):
    def __init__(self, *, max_count: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._max = max_count
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(8, 4, 8, 4)
        self._layout.setSpacing(8)
        self._layout.addStretch(1)

    def clear(self) -> None:
        while self._layout.count() > 1:  # stretch'i bırak
            item = self._layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def set_thumbnails(self, nef_paths: list[Path]) -> None:
        """Verilen NEF yollarından thumb yap, en yenisi solda olacak şekilde göster.

        Liste zaten yeni→eski sıralı varsayılır.
        """
        self.clear()
        for path in nef_paths[: self._max]:
            label = QLabel(self)
            label.setFixedHeight(_THUMB_HEIGHT)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            data = extract_embedded_jpeg(path)
            if data is None:
                label.setText(path.name[:12])
                label.setStyleSheet("background-color: #444444; padding: 4px;")
            else:
                pix = QPixmap()
                if pix.loadFromData(data, "JPG"):
                    pix = pix.scaledToHeight(
                        _THUMB_HEIGHT, Qt.TransformationMode.SmoothTransformation
                    )
                    label.setPixmap(pix)
                else:
                    label.setText("?")
            self._layout.insertWidget(0, label)
