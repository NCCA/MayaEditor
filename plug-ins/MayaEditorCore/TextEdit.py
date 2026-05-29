# Copyright (C) 2022  Jonathan Macey
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
#  any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""Base TextEdit class extending QPlainTextEdit for the Maya Editor.

This is the base class for all editor text edits, providing line numbers,
find/replace, zoom, and common signal wiring.
"""

from pathlib import Path
from typing import Any, Optional

from PySide6.QtCore import QEvent, QObject, QRect, Qt, Signal, Slot
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetricsF,
    QPaintEvent,
    QPainter,
    QPen,
    QResizeEvent,
    QTextCursor,
    QTextDocument,
    QTextFormat,
)
from PySide6.QtWidgets import (
    QFileDialog,
    QInputDialog,
    QPlainTextEdit,
    QTabWidget,
    QTextEdit,
)

from .CodeFoldingManager import CodeFoldingManager
from .FindDialog import FindDialog
from .LineNumberArea import LineNumberArea

FOLD_ICON_WIDTH = 14


class TextEdit(QPlainTextEdit):
    """Custom QPlainTextEdit with line numbers, zoom, find/replace and signals.

    Signals
    -------
    update_output : Signal(str)
        Emitted with plain text to append to the output window.
    update_output_html : Signal(str)
        Emitted with HTML text to append to the output window.
    draw_line : Signal()
        Emitted to draw a separator line in the output window.
    """

    update_output = Signal(str)
    update_output_html = Signal(str)
    draw_line = Signal()
    add_file_to_workspace = Signal(str)

    def __init__(
        self,
        read_only: bool = True,
        show_line_numbers: bool = True,
        code: Optional[str] = None,
        filename: Optional[str] = None,
        parent: Optional[Any] = None,
    ) -> None:
        """Construct the TextEdit.

        Parameters
        ----------
        read_only : bool
            Whether the editor should be read-only.
        show_line_numbers : bool
            Whether to show line numbers in the margin.
        code : str or None
            Initial source code to load.
        filename : str or None
            Filename associated with this editor.
        parent : QObject or None
            Parent widget.
        """
        super().__init__(parent)
        self.parent: Optional[Any] = parent
        self.setStyleSheet("background-color: rgb(30,30,30);color : rgb(250,250,250);")
        self.tab_size: int = 4
        self.installEventFilter(self)
        self.setReadOnly(read_only)
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.ensureCursorVisible()
        self.find_dialog: Optional[FindDialog] = None
        self.found_index: int = 0
        self.found_count: int = 0
        self.filename: Optional[str] = filename
        if code:
            self.setPlainText(code)
            self.find_dialog = FindDialog(self)
            self.find_dialog.hide()
        self.installEventFilter(self)
        self.show_line_numbers: bool = show_line_numbers
        if self.show_line_numbers:
            self.line_number_area: LineNumberArea = LineNumberArea(self)
            self.blockCountChanged.connect(self.update_line_number_area_width)
            self.updateRequest.connect(self.update_line_number_area)
            self.cursorPositionChanged.connect(self.highlight_current_line)
        self.needs_saving: bool = False
        self.first_edit: bool = False
        self.folding = CodeFoldingManager(self)
        self.textChanged.connect(self.text_changed)

    def text_changed(self) -> None:
        """Mark the editor as needing saving on the second text change onward.

        The first text change is the initial population of the editor content,
        which should not trigger a "needs saving" state.
        """
        if not self.first_edit:
            self.first_edit = True
        else:
            self.needs_saving = True
        self.folding.clear_folds()

    @Slot(QFont)
    def set_editor_fonts(self, font: QFont) -> None:
        """Set the editor font and update tab stop distance.

        Parameters
        ----------
        font : QFont
            The font to apply.
        """
        self.setTabStopDistance(
            QFontMetricsF(self.font()).horizontalAdvance(" ") * self.tab_size
        )
        self.setFont(font)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """Filter key events for editor shortcuts.

        Supported shortcuts:
        - Ctrl+S : save file
        - Ctrl++/= : zoom in
        - Ctrl+- : zoom out
        - Ctrl+G : goto line
        - Ctrl+F : show find dialog

        Parameters
        ----------
        obj : QObject
            The object that triggered the event.
        event : QEvent
            The event to process.

        Returns
        -------
        bool
            True if the event was handled, False otherwise.
        """
        if isinstance(obj, TextEdit) and event.type() == QEvent.KeyPress:
            key_event = event
            if (
                key_event.key() == Qt.Key_S
                and key_event.modifiers() == Qt.ControlModifier
            ):
                self.save_file()
                return True
            elif (
                key_event.key() in (Qt.Key_Plus, Qt.Key_Equal)
                and key_event.modifiers() == Qt.ControlModifier
            ):
                obj.zoomIn(1)
                return True
            elif (
                key_event.key() == Qt.Key_Minus
                and key_event.modifiers() == Qt.ControlModifier
            ):
                obj.zoomOut(1)
                return True
            elif (
                key_event.key() == Qt.Key_G
                and key_event.modifiers() == Qt.ControlModifier
            ):
                self.goto_line()
                return True
            elif (
                key_event.key() == Qt.Key_F
                and key_event.modifiers() == Qt.ControlModifier
            ):
                self.show_find_dialog()
                return True
            elif key_event.key() == Qt.Key_Return and not self.hasFocus():
                return True
            else:
                return False
        else:
            return False

    def event(self, event: QEvent) -> bool:
        """Handle wheel events for Ctrl+scroll zoom.

        Parameters
        ----------
        event : QEvent
            The event to process.

        Returns
        -------
        bool
            True if the event was handled, False otherwise.
        """
        if event.type() == QEvent.Wheel:
            if event.modifiers() == Qt.ControlModifier:
                if event.angleDelta().y() > 0:
                    self.zoomIn(1)
                else:
                    self.zoomOut(1)
                return True
        return bool(QPlainTextEdit.event(self, event))

    def goto_line(self, line_number: int = 0) -> None:
        """Move the cursor to the specified line.

        If *line_number* is 0 a dialog is shown prompting for the line number.

        Parameters
        ----------
        line_number : int
            The 1-based line to go to. 0 prompts the user.
        """
        if line_number == 0:
            cursor = self.textCursor()
            line_number, ok = QInputDialog.getInt(
                self,
                "Goto Line",
                "line",
                cursor.blockNumber() + 1,
                1,
                self.blockCount() + 1,
                Qt.Tool,
            )
            if not ok:
                return
        cursor = QTextCursor(self.document().findBlockByLineNumber(line_number - 1))
        self.ensureCursorVisible()
        self.setTextCursor(cursor)

    def save_file(self) -> bool:
        """Save the current editor content to its file.

        If the filename is ``untitled.txt`` a save dialog is shown.

        Returns
        -------
        bool
            True if the file was saved, False if cancelled.
        """
        if self.filename == "untitled.txt":
            filename, _ = QFileDialog.getSaveFileName(
                self, "Save As", "", "All Files (*.*)"
            )
            if filename is None:
                return False
            else:
                self.filename = filename
                self.add_file_to_workspace.emit(filename)
        if self.filename:
            with open(self.filename, "w") as code_file:
                code_file.write(self.toPlainText())
            self.needs_saving = False
            self._update_tab_title()
        return True

    def _update_tab_title(self) -> None:
        """Update the tab text to reflect the current filename."""
        if not self.filename:
            return
        p = QObject.parent(self)
        while p is not None:
            if isinstance(p, QTabWidget):
                idx = p.indexOf(self)
                if idx >= 0:
                    p.setTabText(idx, Path(self.filename).name)
                break
            p = QObject.parent(p)

    def show_find_dialog(self) -> None:
        """Toggle the visibility of the find dialog."""
        if self.find_dialog:
            if self.find_dialog.isVisible():
                self.find_dialog.hide()
            else:
                geometry = QObject.parent(self).geometry() if QObject.parent(self) else QRect()
                self.find_dialog.move(
                    geometry.width() - self.find_dialog.width() - 10,
                    geometry.top(),
                )
                self.find_dialog.show()
                self.find_dialog.text_search.setFocus()

    @Slot(str)
    def append_plain_text(self, text: str) -> None:
        """Append plain text to the editor at the end.

        Parameters
        ----------
        text : str
            The text to append.
        """
        self.moveCursor(QTextCursor.End)
        self.insertPlainText(text)

    @Slot(str)
    def append_html(self, text: str) -> None:
        """Append HTML to the editor at the end.

        Parameters
        ----------
        text : str
            The HTML text to append.
        """
        self.moveCursor(QTextCursor.End)
        cursor = self.textCursor()
        cursor.insertHtml(f"<p><pre>{text}<pre></p>")

    @Slot()
    def append_line(self) -> None:
        """Append a horizontal separator line to the output."""
        self.moveCursor(QTextCursor.End)
        self.appendHtml("<hr>")

    def line_number_area_width(self) -> int:
        """Calculate the width needed for the line number area.

        Returns
        -------
        int
            Width in pixels based on the number of lines.
        """
        digits = 2
        count = max(1, self.blockCount())
        while count >= 10:
            count /= 10
            digits += 1
        space = int(self.fontMetrics().averageCharWidth() * digits)
        return space + FOLD_ICON_WIDTH

    def update_line_number_area_width(self, _: int) -> None:
        """Update the viewport margins to accommodate the line number area."""
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect: QRect, dy: int) -> None:
        """Update the line number area when the editor scrolls or resizes.

        Parameters
        ----------
        rect : QRect
            The rectangle that needs updating.
        dy : int
            The vertical scroll delta.
        """
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(
                0, rect.y(), self.line_number_area.width(), rect.height()
            )
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Resize the line number area when the editor is resized.

        Parameters
        ----------
        event : QResizeEvent
            The resize event.
        """
        super().resizeEvent(event)
        if self.show_line_numbers:
            cr = self.contentsRect()
            self.line_number_area.setGeometry(
                QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height())
            )

    def lineNumberAreaPaintEvent(self, event: QPaintEvent) -> None:
        """Paint the line numbers in the margin area.

        Parameters
        ----------
        event : QPaintEvent
            The paint event.
        """
        if self.show_line_numbers:
            mypainter = QPainter(self.line_number_area)
            mypainter.setFont(self.font())
            mypainter.fillRect(event.rect(), QColor(43, 43, 43))
            block = self.firstVisibleBlock()
            blockNumber = block.blockNumber()
            top = (
                self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
            )
            bottom = top + self.blockBoundingRect(block).height()
            height = self.fontMetrics().height()
            number_area_width = self.line_number_area.width() - FOLD_ICON_WIDTH
            while block.isValid() and (top <= event.rect().bottom()):
                if block.isVisible() and (bottom >= event.rect().top()):
                    if self.folding.is_fold_start(block):
                        is_folded = self.folding.fold_states.get(blockNumber, False)
                        icon_size = 10
                        icon_x = number_area_width + (FOLD_ICON_WIDTH - icon_size) // 2
                        icon_y = top + (height - icon_size) // 2
                        box = QRect(icon_x, icon_y, icon_size, icon_size)
                        mypainter.setPen(QPen(QColor(160, 160, 160), 1))
                        mypainter.setBrush(QColor(60, 60, 60))
                        mypainter.drawRect(box)
                        mypainter.setPen(QColor(255, 255, 255))
                        mypainter.drawText(
                            box, Qt.AlignCenter, "+" if is_folded else "-"
                        )
                    number = str(blockNumber + 1) + " "
                    mypainter.setPen(Qt.yellow)
                    mypainter.drawText(
                        0,
                        top,
                        number_area_width,
                        height,
                        Qt.AlignRight,
                        number,
                    )
                block = block.next()
                top = bottom
                bottom = top + self.blockBoundingRect(block).height()
                blockNumber += 1

    def highlight_current_line(self) -> None:
        """Highlight the current line with a background colour."""
        extraSelections = []
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            lineColor = QColor(45, 45, 45)
            selection.format.setBackground(lineColor)
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extraSelections.append(selection)
        self.setExtraSelections(extraSelections)

    @Slot(bool)
    def toggle_line_number(self, state: bool) -> None:
        """Toggle line number visibility.

        Parameters
        ----------
        state : bool
            True to show line numbers, False to hide them.
        """
        self.show_line_numbers = state
        self.update()

    @Slot(str)
    def search_text(self, text: str) -> None:
        """Search for text and report the match count.

        Parameters
        ----------
        text : str
            The text to search for.
        """
        self.found_count = 1
        self.found_index = 1
        while self.find(text):
            self.found_count += 1
        if self.find_dialog:
            self.find_dialog.items_found.setText(
                f"{self.found_index} of {self.found_count}"
            )
        self.moveCursor(QTextCursor.Start)
        self.find(text)

    def find_next(self, text: str) -> None:
        """Find the next occurrence of the search text.

        Parameters
        ----------
        text : str
            The text to search for.
        """
        if self.find(text):
            self.found_index += 1
            if self.find_dialog:
                self.find_dialog.items_found.setText(
                    f"{self.found_index} of {self.found_count}"
                )
        else:
            self.moveCursor(QTextCursor.Start)
            self.found_index = 1

    def _find_flags(self) -> QTextDocument.FindFlag:
        """Build QTextDocument find flags from the find-dialog UI state.

        Returns
        -------
        QTextDocument.FindFlag
            Combined find flags (case sensitivity, whole word).
        """
        flags = QTextDocument.FindFlag(0)
        if self.find_dialog and self.find_dialog.case_sensitive.isChecked():
            flags |= QTextDocument.FindCaseSensitively
        if self.find_dialog and self.find_dialog.whole_word.isChecked():
            flags |= QTextDocument.FindWholeWords
        return flags

    @Slot(str, str)
    def replace_current(self, search_text: str, replace_text: str) -> None:
        """Replace the current match and move to the next.

        Parameters
        ----------
        search_text : str
            Text to search for.
        replace_text : str
            Text to replace with.
        """
        tc = self.textCursor()
        if tc.hasSelection() and tc.selectedText() == search_text:
            tc.insertText(replace_text)
        self.find(search_text, self._find_flags())

    @Slot(str, str)
    def replace_all(self, search_text: str, replace_text: str) -> None:
        """Replace all occurrences of search_text with replace_text.

        Parameters
        ----------
        search_text : str
            Text to search for.
        replace_text : str
            Text to replace with.
        """
        if not search_text:
            return
        flags = self._find_flags()
        count = 0
        self.moveCursor(QTextCursor.Start)
        while self.find(search_text, flags):
            tc = self.textCursor()
            tc.insertText(replace_text)
            count += 1
        if self.find_dialog:
            if count:
                self.find_dialog.items_found.setText(f"Replaced {count} occurrences")
            else:
                self.find_dialog.items_found.setText("no results found")

