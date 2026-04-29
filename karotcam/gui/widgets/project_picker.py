"""Proje seçim ekranı + inline 'Yeni Proje' formu."""
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

from karotcam.db.models import Project
from karotcam.db.repository import ProjectRepository


class ProjectPicker(QWidget):
    project_chosen = pyqtSignal(int)  # project_id

    def __init__(self, repo: ProjectRepository, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._repo = repo
        self._stack = QStackedLayout(self)

        # --- liste modu ---
        list_widget = QWidget(self)
        list_layout = QVBoxLayout(list_widget)
        list_layout.addWidget(QLabel("Proje Seç", list_widget))
        self._list = QListWidget(list_widget)
        self._list.itemActivated.connect(self._activate_current)
        list_layout.addWidget(self._list, 1)
        bottom = QHBoxLayout()
        self._new_btn = QPushButton("Yeni Proje [N]", list_widget)
        self._new_btn.clicked.connect(self._show_new_form)
        bottom.addStretch(1)
        bottom.addWidget(self._new_btn)
        list_layout.addLayout(bottom)
        self._stack.addWidget(list_widget)

        # --- yeni proje formu ---
        form_widget = QWidget(self)
        form_outer = QVBoxLayout(form_widget)
        form_outer.addWidget(QLabel("Yeni Proje", form_widget))
        form = QFormLayout()
        self._name = QLineEdit(form_widget)
        self._company = QLineEdit(form_widget)
        self._location = QLineEdit(form_widget)
        form.addRow("Proje Adı", self._name)
        form.addRow("Şirket", self._company)
        form.addRow("Konum", self._location)
        form_outer.addLayout(form)
        create_btn = QPushButton("Oluştur", form_widget)
        create_btn.clicked.connect(self._create)
        form_outer.addWidget(create_btn)
        form_outer.addStretch(1)
        self._stack.addWidget(form_widget)

    def refresh(self) -> None:
        self._list.clear()
        for p in self._repo.list_all():
            item = QListWidgetItem(_fmt_project(p), self._list)
            item.setData(Qt.ItemDataRole.UserRole, p.id)
        if self._list.count() > 0:
            self._list.setCurrentRow(0)
            self._list.setFocus()
        self._stack.setCurrentIndex(0)

    def keyPressEvent(self, e: QKeyEvent) -> None:  # type: ignore[override]
        if self._stack.currentIndex() == 0 and e.key() == Qt.Key.Key_N:
            self._show_new_form()
            return
        super().keyPressEvent(e)

    def _show_new_form(self) -> None:
        self._name.clear()
        self._company.clear()
        self._location.clear()
        self._stack.setCurrentIndex(1)
        self._name.setFocus()

    def _activate_current(self, item: QListWidgetItem) -> None:
        self.project_chosen.emit(int(item.data(Qt.ItemDataRole.UserRole)))

    def _create(self) -> None:
        ad = self._name.text().strip()
        if not ad:
            return
        new_id = self._repo.create(
            ad=ad,
            sirket=self._company.text().strip() or None,
            konum=self._location.text().strip() or None,
        )
        self.project_chosen.emit(new_id)


def _fmt_project(p: Project) -> str:
    parts = [p.ad]
    if p.sirket:
        parts.append(f"({p.sirket})")
    if p.konum:
        parts.append(f"— {p.konum}")
    return "  ".join(parts)
