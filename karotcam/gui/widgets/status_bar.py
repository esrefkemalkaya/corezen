"""Üst durum çubuğu — bağlantı noktası + bağlam etiketi."""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QWidget


class TopStatusBar(QWidget):
    """●  Bağlı/Yok    Proje: X    Kuyu: Y"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        self._dot = QLabel("●", self)
        self._dot.setObjectName("ConnectionDot")
        self._dot.setProperty("connected", "false")

        self._status_text = QLabel("Bağlantı yok", self)

        self._context = QLabel("Proje: — Kuyu: —", self)
        self._context.setObjectName("StatusContext")
        self._context.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        layout.addWidget(self._dot)
        layout.addWidget(self._status_text)
        layout.addStretch(1)
        layout.addWidget(self._context)

    @pyqtSlot(bool)
    def set_connection(self, connected: bool) -> None:
        self._dot.setProperty("connected", "true" if connected else "false")
        self._status_text.setText("Bağlı" if connected else "Bağlantı yok")
        # property değişince stil yenilensin
        self._dot.style().unpolish(self._dot)
        self._dot.style().polish(self._dot)

    def set_context(self, *, project: str | None, hole: str | None) -> None:
        p = project or "—"
        h = hole or "—"
        self._context.setText(f"Proje: {p}    Kuyu: {h}")
