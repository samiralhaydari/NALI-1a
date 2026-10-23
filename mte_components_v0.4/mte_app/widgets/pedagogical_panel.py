from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)


class PedagogicalPanel(QFrame):
    hint_requested = Signal(str)
    export_requested = Signal()
    reflection_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("pedagogicalPanel")

        header = QHBoxLayout()
        title = QLabel("LEARNING TRACE")
        title.setObjectName("learningTraceTitle")
        self.export_button = QPushButton("Export Submission…")
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self.export_button)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_summary_tab(), "Evidence Summary")
        self.tabs.addTab(self._build_attempts_tab(), "Attempt Timeline")
        self.tabs.addTab(self._build_guidance_tab(), "Hints & Reflection")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addLayout(header)
        layout.addWidget(self.tabs)

        self.export_button.clicked.connect(self.export_requested.emit)

    def _summary_card(self, title: str) -> tuple[QFrame, QLabel]:
        frame = QFrame()
        frame.setObjectName("summaryCard")
        label_title = QLabel(title)
        label_title.setObjectName("summaryCardTitle")
        content = QLabel("Not run yet.")
        content.setWordWrap(True)
        layout = QVBoxLayout(frame)
        layout.addWidget(label_title)
        layout.addWidget(content)
        return frame, content

    def _build_summary_tab(self) -> QWidget:
        widget = QWidget()
        self.matlab_card, self.matlab_summary = self._summary_card("MATLAB — exploration")
        self.python_card, self.python_summary = self._summary_card("Python — conjecture testing")
        self.lean_card, self.lean_summary = self._summary_card("Lean — formal verification")

        cards = QHBoxLayout()
        cards.addWidget(self.matlab_card)
        cards.addWidget(self.python_card)
        cards.addWidget(self.lean_card)

        self.overall_summary = QLabel("No execution evidence has been recorded yet.")
        self.overall_summary.setObjectName("overallSummary")
        self.overall_summary.setWordWrap(True)

        layout = QVBoxLayout(widget)
        layout.addLayout(cards)
        layout.addWidget(self.overall_summary)
        return widget

    def _build_attempts_tab(self) -> QWidget:
        widget = QWidget()
        self.attempt_tree = QTreeWidget()
        self.attempt_tree.setColumnCount(5)
        self.attempt_tree.setHeaderLabels(["#", "Time", "Stage", "Result", "Summary"])
        self.attempt_tree.setRootIsDecorated(False)
        self.attempt_tree.setAlternatingRowColors(True)
        self.attempt_tree.setColumnWidth(0, 45)
        self.attempt_tree.setColumnWidth(1, 180)
        self.attempt_tree.setColumnWidth(2, 90)
        self.attempt_tree.setColumnWidth(3, 120)

        note = QLabel(
            "Each execution is retained as part of the learning trail. A rejected proof or failed computation remains visible rather than being overwritten by the next attempt."
        )
        note.setWordWrap(True)

        layout = QVBoxLayout(widget)
        layout.addWidget(note)
        layout.addWidget(self.attempt_tree, 1)
        return widget

    def _build_guidance_tab(self) -> QWidget:
        widget = QWidget()
        hint_buttons = QHBoxLayout()
        for stage in ("MATLAB", "Python", "Lean"):
            button = QPushButton(f"Socratic hint: {stage}")
            button.clicked.connect(lambda _checked=False, s=stage: self.hint_requested.emit(s))
            hint_buttons.addWidget(button)
        hint_buttons.addStretch(1)

        self.hint_title = QLabel("Socratic hint")
        self.hint_title.setObjectName("hintTitle")
        self.hint_text = QLabel(
            "Select a language after an attempt. Hints are phrased as questions and do not insert a final solution."
        )
        self.hint_text.setWordWrap(True)
        self.hint_text.setObjectName("hintText")

        reflection_prompt = QLabel(
            "Reflection: What did the computational evidence suggest? What did Lean establish or reject? What assumption, representation, or strategy changed between attempts?"
        )
        reflection_prompt.setWordWrap(True)

        self.reflection_editor = QPlainTextEdit()
        self.reflection_editor.setPlaceholderText(
            "Write your interpretation and what you would try next. This reflection is saved with the .mte session and exported with the submission package."
        )
        self.reflection_editor.setMinimumHeight(110)

        layout = QVBoxLayout(widget)
        layout.addLayout(hint_buttons)
        layout.addWidget(self.hint_title)
        layout.addWidget(self.hint_text)
        layout.addSpacing(8)
        layout.addWidget(reflection_prompt)
        layout.addWidget(self.reflection_editor, 1)

        self.reflection_editor.textChanged.connect(self.reflection_changed.emit)
        return widget

    def set_summary(self, summary: dict[str, str]) -> None:
        self.matlab_summary.setText(summary.get("matlab", ""))
        self.python_summary.setText(summary.get("python", ""))
        self.lean_summary.setText(summary.get("lean", ""))
        self.overall_summary.setText(summary.get("overall", ""))

    def set_attempts(self, attempts: list[dict]) -> None:
        self.attempt_tree.clear()
        for item in attempts:
            self.add_attempt(item)

    def add_attempt(self, item: dict) -> None:
        timestamp = str(item.get("timestamp", ""))
        if "T" in timestamp:
            timestamp = timestamp.replace("T", " ")
        tree_item = QTreeWidgetItem(
            [
                str(item.get("attempt_id", "")),
                timestamp,
                str(item.get("stage", "")),
                str(item.get("status", "")),
                str(item.get("summary", "")),
            ]
        )
        tree_item.setToolTip(4, str(item.get("output_excerpt", "")))
        self.attempt_tree.addTopLevelItem(tree_item)
        self.attempt_tree.scrollToItem(tree_item)

    def set_hint(self, stage: str, text: str) -> None:
        self.hint_title.setText(f"Socratic hint — {stage}")
        self.hint_text.setText(text)
        self.tabs.setCurrentIndex(2)

    def reflection(self) -> str:
        return self.reflection_editor.toPlainText()

    def set_reflection(self, text: str) -> None:
        self.reflection_editor.setPlainText(text or "")
