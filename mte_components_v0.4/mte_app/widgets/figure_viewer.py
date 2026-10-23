from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class FigureViewer(QWidget):
    """Embedded viewer for MATLAB-exported PNG figures."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._paths: list[Path] = []
        self._index = -1
        self._pixmap: QPixmap | None = None
        self._fit_to_width = True

        self.title_label = QLabel("MATLAB Figures")
        self.title_label.setObjectName("figureTitle")

        self.previous_button = QPushButton("◀")
        self.next_button = QPushButton("▶")
        self.fit_button = QPushButton("Fit")
        self.actual_button = QPushButton("100%")
        self.counter_label = QLabel("0 / 0")

        controls = QHBoxLayout()
        controls.addWidget(self.previous_button)
        controls.addWidget(self.next_button)
        controls.addWidget(self.fit_button)
        controls.addWidget(self.actual_button)
        controls.addStretch(1)
        controls.addWidget(self.counter_label)

        self.image_label = QLabel("No MATLAB figure generated.")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumHeight(180)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.image_label)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.title_label)
        layout.addLayout(controls)
        layout.addWidget(self.scroll, 1)

        self.previous_button.clicked.connect(self.previous)
        self.next_button.clicked.connect(self.next)
        self.fit_button.clicked.connect(self.fit_to_width)
        self.actual_button.clicked.connect(self.actual_size)
        self.scroll.viewport().installEventFilter(self)
        self._update_controls()

    def figure_paths(self) -> list[str]:
        return [str(path) for path in self._paths if path.exists()]

    def clear(self) -> None:
        self._paths.clear()
        self._index = -1
        self._pixmap = None
        self.image_label.clear()
        self.image_label.setText("No MATLAB figure generated.")
        self._update_controls()

    def add_figure(self, path: str) -> None:
        figure_path = Path(path)
        if not figure_path.exists():
            return
        self._paths.append(figure_path)
        if self._index < 0:
            self._index = 0
        self._show_current()

    def previous(self) -> None:
        if not self._paths:
            return
        self._index = (self._index - 1) % len(self._paths)
        self._show_current()

    def next(self) -> None:
        if not self._paths:
            return
        self._index = (self._index + 1) % len(self._paths)
        self._show_current()

    def fit_to_width(self) -> None:
        self._fit_to_width = True
        self._render_pixmap()

    def actual_size(self) -> None:
        self._fit_to_width = False
        self._render_pixmap()

    def _show_current(self) -> None:
        if not self._paths or self._index < 0:
            return
        self._pixmap = QPixmap(str(self._paths[self._index]))
        self._render_pixmap()
        self._update_controls()

    def _render_pixmap(self) -> None:
        if self._pixmap is None or self._pixmap.isNull():
            return
        if self._fit_to_width:
            available = max(200, self.scroll.viewport().width() - 20)
            shown = self._pixmap.scaledToWidth(
                available,
                Qt.TransformationMode.SmoothTransformation,
            )
        else:
            shown = self._pixmap
        self.image_label.setPixmap(shown)
        self.image_label.adjustSize()

    def _update_controls(self) -> None:
        count = len(self._paths)
        current = self._index + 1 if self._index >= 0 else 0
        self.counter_label.setText(f"{current} / {count}")
        self.previous_button.setEnabled(count > 1)
        self.next_button.setEnabled(count > 1)
        self.fit_button.setEnabled(count > 0)
        self.actual_button.setEnabled(count > 0)

    def eventFilter(self, obj, event):
        if obj is self.scroll.viewport() and event.type() == QEvent.Type.Resize:
            if self._fit_to_width:
                self._render_pixmap()
        return super().eventFilter(obj, event)
