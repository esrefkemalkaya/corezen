"""Kuyu seçim ekranı + inline 'Yeni Kuyu' formu."""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from karotcam.db.models import Hole
from karotcam.db.repository import HoleRepository


class HolePicker(QWidget):
    hole_chosen = pyqtSignal(int)  # hole_id
    back_requested = pyqtSignal()

    def __init__(self, repo: HoleRepository, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._repo = repo
        self._project_id: int | None = None
        self._stack = QStackedLayout(self)

        # --- liste modu ---
        list_widget = QWidget(self)
        list_layout = QVBoxLayout(list_widget)
        self._title = QLabel("Kuyu Seç", list_widget)
        list_layout.addWidget(self._title)
        self._list = QListWidget(list_widget)
        self._list.itemActivated.connect(self._activate_current)
        list_layout.addWidget(self._list, 1)
        bottom = QHBoxLayout()
        self._new_btn = QPushButton("Yeni Kuyu [N]", list_widget)
        self._new_btn.clicked.connect(self._show_new_form)
        bottom.addStretch(1)
        bottom.addWidget(self._new_btn)
        list_layout.addLayout(bottom)
        self._stack.addWidget(list_widget)

        # --- yeni kuyu formu ---
        form_widget = QWidget(self)
        form_outer = QVBoxLayout(form_widget)
        form_outer.addWidget(QLabel("Yeni Kuyu", form_widget))
        form = QFormLayout()
        self._name = QLineEdit(form_widget)
        self._tip = QLineEdit(form_widget)
        form.addRow("Kuyu Adı (örn: BLY-2024-156)", self._name)
        form.addRow("Tip (DDH/RC/Sonic)", self._tip)
        form_outer.addLayout(form)
        create_btn = QPushButton("Oluştur", form_widget)
        create_btn.clicked.connect(self._create)
        form_outer.addWidget(create_btn)
        form_outer.addStretch(1)
        self._stack.addWidget(form_widget)

    def load_for_project(self, project_id: int) -> None:
        self._project_id = project_id
        self._list.clear()
        for h in self._repo.list_for_project(project_id):
            item = QListWidgetItem(_fmt_hole(h), self._list)
            item.setData(Qt.ItemDataRole.UserRole, h.id)
        if self._list.count() > 0:
            self._list.setCurrentRow(0)
            self._list.setFocus()
        self._stack.setCurrentIndex(0)

    def keyPressEvent(self, e: QKeyEvent) -> None:  # type: ignore[override]
        idx = self._stack.currentIndex()
        if idx == 0 and e.key() == Qt.Key.Key_N:
            self._show_new_form()
            return
        if e.key() == Qt.Key.Key_Escape:
            if idx == 1:
                self._stack.setCurrentIndex(0)
            else:
                self.back_requested.emit()
            return
        super().keyPressEvent(e)

    def _show_new_form(self) -> None:
        self._name.clear()
        self._tip.clear()
        self._stack.setCurrentIndex(1)
        self._name.setFocus()

    def _activate_current(self, item: QListWidgetItem) -> None:
        self.hole_chosen.emit(int(item.data(Qt.ItemDataRole.UserRole)))

    def _create(self) -> None:
        if self._project_id is None:
            return
        ad = self._name.text().strip()
        if not ad:
            return
        new_id = self._repo.create(
            project_id=self._project_id,
            kuyu_adi=ad,
            tip=self._tip.text().strip() or None,
        )
        self.hole_chosen.emit(new_id)


def _fmt_hole(h: Hole) -> str:
    parts = [h.kuyu_adi]
    if h.tip:
        parts.append(f"({h.tip})")
    return "  ".join(parts)
