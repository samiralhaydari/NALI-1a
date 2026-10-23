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

from .code_editor import CodeEditor
from .highlighters import LeanHighlighter, MatlabHighlighter, PythonHighlighter


_HIGHLIGHTERS = {
    "matlab": MatlabHighlighter,
    "python": PythonHighlighter,
    "lean": LeanHighlighter,
}


class CodePanel(QFrame):
    run_requested = Signal()
    stop_requested = Signal()

    def __init__(
        self,
        title: str,
        subtitle: str,
        run_label: str,
        *,
        language: str,
        show_diagnostics: bool = False,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.language = language.lower()

        self.title_label = QLabel(title)
        self.title_label.setObjectName("panelTitle")

        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setObjectName("panelSubtitle")

        self.editor = CodeEditor()
        self.editor.setPlaceholderText(f"Enter {title} code here...")
        self.editor.setTabStopDistance(28)

        highlighter_type = _HIGHLIGHTERS.get(self.language)
        self.highlighter = highlighter_type(self.editor.document()) if highlighter_type else None

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
        self.cursor_label = QLabel("Ln 1, Col 1")
        self.cursor_label.setObjectName("cursorLabel")

        button_row = QHBoxLayout()
        button_row.addWidget(self.run_button)
        button_row.addWidget(self.stop_button)
        button_row.addStretch(1)
        button_row.addWidget(self.cursor_label)
        button_row.addWidget(self.status_label)

        self.diagnostic_frame = QFrame()
        self.diagnostic_frame.setObjectName("diagnosticFrame")
        diagnostic_layout = QVBoxLayout(self.diagnostic_frame)
        diagnostic_layout.setContentsMargins(8, 6, 8, 6)
        self.diagnostic_title = QLabel()
        self.diagnostic_title.setObjectName("diagnosticTitle")
        self.diagnostic_detail = QLabel()
        self.diagnostic_detail.setWordWrap(True)
        diagnostic_layout.addWidget(self.diagnostic_title)
        diagnostic_layout.addWidget(self.diagnostic_detail)
        self.diagnostic_frame.setVisible(show_diagnostics)

        layout = QVBoxLayout(self)
        layout.addWidget(self.title_label)
        layout.addWidget(self.subtitle_label)
        layout.addWidget(QLabel("Input"))
        layout.addWidget(self.editor, 3)
        layout.addLayout(button_row)
        if show_diagnostics:
            layout.addWidget(self.diagnostic_frame)
        layout.addWidget(QLabel("Output"))
        layout.addWidget(self.output, 2)

        self.run_button.clicked.connect(self.run_requested.emit)
        self.stop_button.clicked.connect(self.stop_requested.emit)
        self.editor.cursorPositionChanged.connect(self._update_cursor_label)

    def _update_cursor_label(self) -> None:
        cursor = self.editor.textCursor()
        self.cursor_label.setText(
            f"Ln {cursor.blockNumber() + 1}, Col {cursor.positionInBlock() + 1}"
        )

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

    def clear_diagnostic(self) -> None:
        self.diagnostic_title.clear()
        self.diagnostic_detail.clear()
        self.diagnostic_frame.setProperty("state", "idle")
        self.diagnostic_frame.style().unpolish(self.diagnostic_frame)
        self.diagnostic_frame.style().polish(self.diagnostic_frame)

    def set_diagnostic(
        self,
        *,
        title: str,
        detail: str,
        state: str,
    ) -> None:
        self.diagnostic_title.setText(title)
        self.diagnostic_detail.setText(detail)
        self.diagnostic_frame.setProperty("state", state)
        self.diagnostic_frame.style().unpolish(self.diagnostic_frame)
        self.diagnostic_frame.style().polish(self.diagnostic_frame)
