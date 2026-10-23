from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QFontDatabase, QTextCursor
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class CodePanel(QFrame):
    run_requested = Signal()
    stop_requested = Signal()

    def __init__(
        self,
        title: str,
        subtitle: str,
        run_label: str,
        *,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("panelTitle")

        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setObjectName("panelSubtitle")

        self.editor = QPlainTextEdit()
        self.editor.setPlaceholderText(f"Enter {title} code here...")
        self.editor.setTabStopDistance(28)

        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setPlaceholderText("Execution output will appear here...")

        fixed = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        self.editor.setFont(fixed)
        self.output.setFont(fixed)

        self.run_button = QPushButton(run_label)
        self.stop_button = QPushButton("Stop")
        self.stop_button.setEnabled(False)

        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("statusLabel")

        button_row = QHBoxLayout()
        button_row.addWidget(self.run_button)
        button_row.addWidget(self.stop_button)
        button_row.addStretch(1)
        button_row.addWidget(self.status_label)

        layout = QVBoxLayout(self)
        layout.addWidget(self.title_label)
        layout.addWidget(self.subtitle_label)
        layout.addWidget(QLabel("Input"))
        layout.addWidget(self.editor, 3)
        layout.addLayout(button_row)
        layout.addWidget(QLabel("Output"))
        layout.addWidget(self.output, 2)

        self.run_button.clicked.connect(self.run_requested.emit)
        self.stop_button.clicked.connect(self.stop_requested.emit)

    def clear_output(self) -> None:
        self.output.clear()

    def append_output(self, text: str) -> None:
        cursor = self.output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(text)
        self.output.setTextCursor(cursor)
        self.output.ensureCursorVisible()

    def set_running(self) -> None:
        self.status_label.setText("Running…")
        self.run_button.setEnabled(False)
        self.stop_button.setEnabled(True)

    def set_success(self, text: str = "Completed") -> None:
        self.status_label.setText(text)
        self.run_button.setEnabled(True)
        self.stop_button.setEnabled(False)

    def set_failure(self, text: str = "Failed") -> None:
        self.status_label.setText(text)
        self.run_button.setEnabled(True)
        self.stop_button.setEnabled(False)
