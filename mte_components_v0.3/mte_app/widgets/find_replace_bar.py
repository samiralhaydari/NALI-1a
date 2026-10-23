from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)


class FindReplaceBar(QWidget):
    find_next = Signal(str, bool)
    find_previous = Signal(str, bool)
    replace_one = Signal(str, str, bool)
    replace_all = Signal(str, str, bool)
    close_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.find_edit = QLineEdit()
        self.find_edit.setPlaceholderText("Find…")
        self.replace_edit = QLineEdit()
        self.replace_edit.setPlaceholderText("Replace with…")
        self.case_check = QCheckBox("Match case")

        previous_button = QPushButton("Previous")
        next_button = QPushButton("Next")
        replace_button = QPushButton("Replace")
        replace_all_button = QPushButton("Replace All")
        close_button = QPushButton("×")
        close_button.setToolTip("Close find/replace")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.addWidget(QLabel("Find"))
        layout.addWidget(self.find_edit, 1)
        layout.addWidget(previous_button)
        layout.addWidget(next_button)
        layout.addWidget(QLabel("Replace"))
        layout.addWidget(self.replace_edit, 1)
        layout.addWidget(replace_button)
        layout.addWidget(replace_all_button)
        layout.addWidget(self.case_check)
        layout.addWidget(close_button)

        next_button.clicked.connect(self._emit_next)
        previous_button.clicked.connect(self._emit_previous)
        replace_button.clicked.connect(self._emit_replace_one)
        replace_all_button.clicked.connect(self._emit_replace_all)
        close_button.clicked.connect(self.close_requested.emit)
        self.find_edit.returnPressed.connect(self._emit_next)

    def focus_find(self, select_all: bool = True) -> None:
        self.find_edit.setFocus()
        if select_all:
            self.find_edit.selectAll()

    def _emit_next(self) -> None:
        self.find_next.emit(self.find_edit.text(), self.case_check.isChecked())

    def _emit_previous(self) -> None:
        self.find_previous.emit(self.find_edit.text(), self.case_check.isChecked())

    def _emit_replace_one(self) -> None:
        self.replace_one.emit(
            self.find_edit.text(),
            self.replace_edit.text(),
            self.case_check.isChecked(),
        )

    def _emit_replace_all(self) -> None:
        self.replace_all.emit(
            self.find_edit.text(),
            self.replace_edit.text(),
            self.case_check.isChecked(),
        )
