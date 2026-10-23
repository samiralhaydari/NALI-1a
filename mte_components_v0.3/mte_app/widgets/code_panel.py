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
from .figure_viewer import FigureViewer
from .find_replace_bar import FindReplaceBar
from .highlighters import LeanHighlighter, MatlabHighlighter, PythonHighlighter


_HIGHLIGHTERS = {
    "matlab": MatlabHighlighter,
    "python": PythonHighlighter,
    "lean": LeanHighlighter,
}


class CodePanel(QFrame):
    run_requested = Signal()
    stop_requested = Signal()
    diagnostic_location_requested = Signal(int, int)

    def __init__(
        self,
        title: str,
        subtitle: str,
        run_label: str,
        *,
        language: str,
        show_diagnostics: bool = False,
        show_figures: bool = False,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.language = language.lower()
        self._diagnostic_line: int | None = None
        self._diagnostic_column: int | None = None

        self.title_label = QLabel(title)
        self.title_label.setObjectName("panelTitle")
        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setObjectName("panelSubtitle")

        self.editor = CodeEditor()
        self.editor.setPlaceholderText(f"Enter {title} code here...")
        self.editor.setTabStopDistance(28)
        highlighter_type = _HIGHLIGHTERS.get(self.language)
        self.highlighter = highlighter_type(self.editor.document()) if highlighter_type else None

        self.find_bar = FindReplaceBar()
        self.find_bar.setVisible(False)

        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setPlaceholderText("Execution output will appear here...")

        fixed = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        self.editor.setFont(fixed)
        self.output.setFont(fixed)

        self.run_button = QPushButton(run_label)
        self.stop_button = QPushButton("Stop")
        self.stop_button.setEnabled(False)
        self.find_button = QPushButton("Find")
        self.zoom_out_button = QPushButton("−")
        self.zoom_reset_button = QPushButton("100%")
        self.zoom_in_button = QPushButton("+")

        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("statusLabel")
        self.cursor_label = QLabel("Ln 1, Col 1")
        self.cursor_label.setObjectName("cursorLabel")

        button_row = QHBoxLayout()
        button_row.addWidget(self.run_button)
        button_row.addWidget(self.stop_button)
        button_row.addWidget(self.find_button)
        button_row.addWidget(self.zoom_out_button)
        button_row.addWidget(self.zoom_reset_button)
        button_row.addWidget(self.zoom_in_button)
        button_row.addStretch(1)
        button_row.addWidget(self.cursor_label)
        button_row.addWidget(self.status_label)

        self.diagnostic_frame = QFrame()
        self.diagnostic_frame.setObjectName("diagnosticFrame")
        diagnostic_layout = QVBoxLayout(self.diagnostic_frame)
        diagnostic_layout.setContentsMargins(8, 6, 8, 6)

        diagnostic_header = QHBoxLayout()
        self.diagnostic_title = QLabel()
        self.diagnostic_title.setObjectName("diagnosticTitle")
        self.diagnostic_jump_button = QPushButton()
        self.diagnostic_jump_button.setVisible(False)
        diagnostic_header.addWidget(self.diagnostic_title)
        diagnostic_header.addStretch(1)
        diagnostic_header.addWidget(self.diagnostic_jump_button)

        self.diagnostic_detail = QLabel()
        self.diagnostic_detail.setWordWrap(True)
        diagnostic_layout.addLayout(diagnostic_header)
        diagnostic_layout.addWidget(self.diagnostic_detail)
        self.diagnostic_frame.setVisible(show_diagnostics)

        self.figure_viewer = FigureViewer()
        self.figure_viewer.setVisible(show_figures)

        layout = QVBoxLayout(self)
        layout.addWidget(self.title_label)
        layout.addWidget(self.subtitle_label)
        layout.addWidget(QLabel("Input"))
        layout.addWidget(self.editor, 3)
        layout.addWidget(self.find_bar)
        layout.addLayout(button_row)
        if show_diagnostics:
            layout.addWidget(self.diagnostic_frame)
        layout.addWidget(QLabel("Output"))
        layout.addWidget(self.output, 2)
        if show_figures:
            layout.addWidget(self.figure_viewer, 2)

        self.run_button.clicked.connect(self.run_requested.emit)
        self.stop_button.clicked.connect(self.stop_requested.emit)
        self.find_button.clicked.connect(self.show_find)
        self.zoom_in_button.clicked.connect(self.zoom_in)
        self.zoom_out_button.clicked.connect(self.zoom_out)
        self.zoom_reset_button.clicked.connect(self.reset_zoom)
        self.editor.cursorPositionChanged.connect(self._update_cursor_label)

        self.find_bar.find_next.connect(self._find_next)
        self.find_bar.find_previous.connect(self._find_previous)
        self.find_bar.replace_one.connect(self._replace_one)
        self.find_bar.replace_all.connect(self._replace_all)
        self.find_bar.close_requested.connect(self.hide_find)
        self.diagnostic_jump_button.clicked.connect(self._request_diagnostic_jump)
        self._update_zoom_label()

    def _update_cursor_label(self) -> None:
        cursor = self.editor.textCursor()
        self.cursor_label.setText(
            f"Ln {cursor.blockNumber() + 1}, Col {cursor.positionInBlock() + 1}"
        )

    def _update_zoom_label(self) -> None:
        self.zoom_reset_button.setText(f"{self.editor.zoom_percent}%")

    def show_find(self, replace: bool = False) -> None:
        self.find_bar.setVisible(True)
        self.find_bar.focus_find(select_all=False)
        if replace:
            self.find_bar.replace_edit.setFocus()

    def hide_find(self) -> None:
        self.find_bar.setVisible(False)
        self.editor.setFocus()

    def _find_next(self, text: str, case_sensitive: bool) -> None:
        found = self.editor.find_text(text, case_sensitive=case_sensitive)
        self.status_label.setText("Found" if found else "Not found")

    def _find_previous(self, text: str, case_sensitive: bool) -> None:
        found = self.editor.find_text(text, backwards=True, case_sensitive=case_sensitive)
        self.status_label.setText("Found" if found else "Not found")

    def _replace_one(self, find_text: str, replacement: str, case_sensitive: bool) -> None:
        result = self.editor.replace_current(
            find_text,
            replacement,
            case_sensitive=case_sensitive,
        )
        self.status_label.setText("Replace/find complete" if result else "Not found")

    def _replace_all(self, find_text: str, replacement: str, case_sensitive: bool) -> None:
        count = self.editor.replace_all(
            find_text,
            replacement,
            case_sensitive=case_sensitive,
        )
        self.status_label.setText(f"Replaced {count}")

    def zoom_in(self) -> None:
        self.editor.zoom_in_editor()
        self._update_zoom_label()

    def zoom_out(self) -> None:
        self.editor.zoom_out_editor()
        self._update_zoom_label()

    def reset_zoom(self) -> None:
        self.editor.reset_zoom()
        self._update_zoom_label()

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
        self._diagnostic_line = None
        self._diagnostic_column = None
        self.diagnostic_title.clear()
        self.diagnostic_detail.clear()
        self.diagnostic_jump_button.setVisible(False)
        self.diagnostic_frame.setProperty("state", "idle")
        self.diagnostic_frame.style().unpolish(self.diagnostic_frame)
        self.diagnostic_frame.style().polish(self.diagnostic_frame)

    def set_diagnostic(
        self,
        *,
        title: str,
        detail: str,
        state: str,
        line: int | None = None,
        column: int | None = None,
    ) -> None:
        self._diagnostic_line = line
        self._diagnostic_column = column
        self.diagnostic_title.setText(title)
        self.diagnostic_detail.setText(detail)
        if line is not None:
            col = column or 1
            self.diagnostic_jump_button.setText(f"Go to Ln {line}, Col {col}")
            self.diagnostic_jump_button.setVisible(True)
        else:
            self.diagnostic_jump_button.setVisible(False)

        self.diagnostic_frame.setProperty("state", state)
        self.diagnostic_frame.style().unpolish(self.diagnostic_frame)
        self.diagnostic_frame.style().polish(self.diagnostic_frame)

    def _request_diagnostic_jump(self) -> None:
        if self._diagnostic_line is not None:
            self.diagnostic_location_requested.emit(
                self._diagnostic_line,
                self._diagnostic_column or 1,
            )
