from __future__ import annotations

import re

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QPainter, QTextCursor, QTextDocument, QTextFormat
from PySide6.QtWidgets import QPlainTextEdit, QWidget


class LineNumberArea(QWidget):
    def __init__(self, editor: "CodeEditor"):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event) -> None:
        self.editor.line_number_area_paint_event(event)


class CodeEditor(QPlainTextEdit):
    """Code editor with line numbers, navigation, find/replace and zoom."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.line_number_area = LineNumberArea(self)
        self._zoom_steps = 0

        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)
        self.update_line_number_area_width(0)
        self.highlight_current_line()

    @property
    def zoom_percent(self) -> int:
        return max(40, 100 + self._zoom_steps * 10)

    def line_number_area_width(self) -> int:
        digits = max(1, len(str(max(1, self.blockCount()))))
        return 12 + self.fontMetrics().horizontalAdvance("9") * digits

    def update_line_number_area_width(self, _new_block_count: int) -> None:
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect: QRect, dy: int) -> None:
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(
                0, rect.y(), self.line_number_area.width(), rect.height()
            )
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        contents = self.contentsRect()
        self.line_number_area.setGeometry(
            QRect(
                contents.left(),
                contents.top(),
                self.line_number_area_width(),
                contents.height(),
            )
        )

    def line_number_area_paint_event(self, event) -> None:
        painter = QPainter(self.line_number_area)
        palette = self.palette()
        painter.fillRect(event.rect(), palette.alternateBase())

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = round(
            self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        )
        bottom = top + round(self.blockBoundingRect(block).height())

        painter.setPen(palette.mid().color())
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.drawText(
                    0,
                    top,
                    self.line_number_area.width() - 5,
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight,
                    str(block_number + 1),
                )
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            block_number += 1

    def highlight_current_line(self) -> None:
        if self.isReadOnly():
            return
        selection = QPlainTextEdit.ExtraSelection()
        selection.format.setBackground(self.palette().alternateBase().color())
        selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
        selection.cursor = self.textCursor()
        selection.cursor.clearSelection()
        self.setExtraSelections([selection])

    def goto_line_column(self, line: int, column: int = 1) -> None:
        line = max(1, line)
        column = max(1, column)
        block = self.document().findBlockByNumber(line - 1)
        if not block.isValid():
            return
        cursor = QTextCursor(block)
        max_position = block.position() + max(0, block.length() - 1)
        cursor.setPosition(min(block.position() + column - 1, max_position))
        self.setTextCursor(cursor)
        self.centerCursor()
        self.setFocus()

    def find_text(
        self,
        text: str,
        *,
        backwards: bool = False,
        case_sensitive: bool = False,
    ) -> bool:
        if not text:
            return False
        flags = QTextDocument.FindFlag()
        if backwards:
            flags |= QTextDocument.FindFlag.FindBackward
        if case_sensitive:
            flags |= QTextDocument.FindFlag.FindCaseSensitively
        if self.find(text, flags):
            return True
        cursor = self.textCursor()
        cursor.movePosition(
            QTextCursor.MoveOperation.End
            if backwards
            else QTextCursor.MoveOperation.Start
        )
        self.setTextCursor(cursor)
        return self.find(text, flags)

    def replace_current(
        self,
        find_text: str,
        replacement: str,
        *,
        case_sensitive: bool = False,
    ) -> bool:
        cursor = self.textCursor()
        selected = cursor.selectedText()
        matches = (
            selected == find_text
            if case_sensitive
            else selected.casefold() == find_text.casefold()
        )
        if find_text and matches:
            cursor.insertText(replacement)
            self.setTextCursor(cursor)
            self.find_text(find_text, case_sensitive=case_sensitive)
            return True
        return self.find_text(find_text, case_sensitive=case_sensitive)

    def replace_all(
        self,
        find_text: str,
        replacement: str,
        *,
        case_sensitive: bool = False,
    ) -> int:
        if not find_text:
            return 0
        source = self.toPlainText()
        if case_sensitive:
            count = source.count(find_text)
            updated = source.replace(find_text, replacement)
        else:
            pattern = re.compile(re.escape(find_text), re.IGNORECASE)
            updated, count = pattern.subn(lambda _m: replacement, source)
        if count:
            old_position = self.textCursor().position()
            self.setPlainText(updated)
            cursor = self.textCursor()
            cursor.setPosition(min(old_position, len(updated)))
            self.setTextCursor(cursor)
        return count

    def zoom_in_editor(self) -> None:
        if self._zoom_steps >= 10:
            return
        self.zoomIn(1)
        self._zoom_steps += 1
        self.update_line_number_area_width(0)

    def zoom_out_editor(self) -> None:
        if self._zoom_steps <= -6:
            return
        self.zoomOut(1)
        self._zoom_steps -= 1
        self.update_line_number_area_width(0)

    def reset_zoom(self) -> None:
        while self._zoom_steps > 0:
            self.zoomOut(1)
            self._zoom_steps -= 1
        while self._zoom_steps < 0:
            self.zoomIn(1)
            self._zoom_steps += 1
        self.update_line_number_area_width(0)

    def keyPressEvent(self, event) -> None:
        if (
            event.key() == Qt.Key.Key_Tab
            and not (event.modifiers() & Qt.KeyboardModifier.ControlModifier)
        ):
            self.insertPlainText("    ")
            return
        super().keyPressEvent(event)
