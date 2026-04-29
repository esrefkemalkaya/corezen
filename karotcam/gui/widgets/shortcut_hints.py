"""Alt kenardaki sürekli görünür kısayol göstergesi."""
from __future__ import annotations

from PyQt6.QtWidgets import QLabel, QWidget


class ShortcutHints(QLabel):
    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("ShortcutHints")
        self.setWordWrap(True)
