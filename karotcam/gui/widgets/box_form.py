"""Sıradaki kutu önerisini gösteren ve `D` ile düzenlemeye izin veren widget.

Görüntü modu: salt etiket. Düzenle modu: kutu_no + iki derinlik QSpin'i + Onayla.
"""
from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QStackedLayout,
    QWidget,
)


@dataclass(frozen=True, slots=True)
class NextBox:
    kutu_no: int
    derinlik_baslangic: float
    derinlik_bitis: float


class BoxForm(QWidget):
    """Görüntü/Düzenle modlarını tek widget'ta tutar."""

    edited = pyqtSignal(object)  # NextBox yayılır

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._stack = QStackedLayout(self)

        # --- görüntü modu ---
        self._view_widget = QWidget(self)
        view_layout = QHBoxLayout(self._view_widget)
        view_layout.setContentsMargins(0, 0, 0, 0)
        self._label = QLabel("Sıradaki Kutu: —", self._view_widget)
        view_layout.addWidget(self._label)
        view_layout.addStretch(1)
        view_layout.addWidget(QLabel("[düzenle: D]", self._view_widget))
        self._stack.addWidget(self._view_widget)

        # --- düzenle modu ---
        self._edit_widget = QWidget(self)
        edit_layout = QHBoxLayout(self._edit_widget)
        edit_layout.setContentsMargins(0, 0, 0, 0)
        edit_layout.addWidget(QLabel("Kutu No:", self._edit_widget))
        self._kutu = QSpinBox(self._edit_widget)
        self._kutu.setRange(1, 9999)
        edit_layout.addWidget(self._kutu)
        edit_layout.addWidget(QLabel("Başlangıç:", self._edit_widget))
        self._dbas = QDoubleSpinBox(self._edit_widget)
        self._dbas.setRange(0.0, 99999.0)
        self._dbas.setDecimals(2)
        edit_layout.addWidget(self._dbas)
        edit_layout.addWidget(QLabel("Bitiş:", self._edit_widget))
        self._dbit = QDoubleSpinBox(self._edit_widget)
        self._dbit.setRange(0.0, 99999.0)
        self._dbit.setDecimals(2)
        edit_layout.addWidget(self._dbit)
        self._confirm = QPushButton("Onayla [Enter]", self._edit_widget)
        self._confirm.setDefault(True)
        self._confirm.clicked.connect(self._emit_edited)
        edit_layout.addWidget(self._confirm)
        self._stack.addWidget(self._edit_widget)

    def set_suggestion(self, box: NextBox) -> None:
        self._label.setText(
            f"Sıradaki Kutu: K{box.kutu_no:04d}    "
            f"Derinlik: {box.derinlik_baslangic:.2f} - {box.derinlik_bitis:.2f}"
        )
        self._kutu.setValue(box.kutu_no)
        self._dbas.setValue(box.derinlik_baslangic)
        self._dbit.setValue(box.derinlik_bitis)
        self._stack.setCurrentIndex(0)

    def is_editing(self) -> bool:
        return self._stack.currentIndex() == 1

    def enter_edit_mode(self) -> None:
        self._stack.setCurrentIndex(1)
        self._kutu.setFocus(Qt.FocusReason.OtherFocusReason)

    def confirm_edit(self) -> None:
        self._emit_edited()

    def cancel_edit(self) -> None:
        self._stack.setCurrentIndex(0)

    def _emit_edited(self) -> None:
        self.edited.emit(
            NextBox(
                kutu_no=self._kutu.value(),
                derinlik_baslangic=self._dbas.value(),
                derinlik_bitis=self._dbit.value(),
            )
        )
        self._stack.setCurrentIndex(0)
