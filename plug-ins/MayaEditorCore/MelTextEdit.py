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
"""MEL editor widget extending TextEdit with syntax highlighting and execution."""

from collections import namedtuple
from typing import Any, List, Optional

import maya.mel as mel
from PySide6.QtCore import QEvent, QObject, Qt, Signal
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QFileDialog

from .MelHighlighter import MelHighlighter
from .TextEdit import TextEdit


class MelTextEdit(TextEdit):
    """QPlainTextEdit customised for MEL script editing with highlighting and execution.

    Signals
    -------
    code_model_changed : Signal()
        Emitted when the code model (function list) is regenerated.
    """

    code_model_changed = Signal()
    code_model_data = namedtuple("code_model_data", "scope line_number function_name")  # noqa: PYI024

    def __init__(
        self,
        read_only: bool = True,
        show_line_numbers: bool = True,
        code: Optional[str] = None,
        filename: Optional[str] = None,
        live: bool = False,
        parent: Optional[Any] = None,
    ) -> None:
        """Construct a MelTextEdit.

        Parameters
        ----------
        read_only : bool
            Whether the editor is read-only.
        show_line_numbers : bool
            Whether to display line numbers.
        code : str or None
            Initial source code.
        filename : str or None
            Associated filename.
        live : bool
            If True, echo output and clear on run (like Maya's script editor).
        parent : QObject or None
            Parent widget.
        """
        super().__init__(read_only, show_line_numbers, code, filename, parent)
        self.highlighter = MelHighlighter()
        self.highlighter.setDocument(self.document())
        self.execute_selected: bool = False
        self.live: bool = live
        self.copyAvailable.connect(self.selection_changed)
        self.code_model: List[Any] = []
        self.generate_code_model()

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """Filter key events for MEL editor shortcuts.

        Supported shortcuts:
        - Ctrl+Return / F5 : execute code
        - Ctrl+S : save file

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
        if isinstance(obj, MelTextEdit) and event.type() == QEvent.KeyPress:
            key_event = event
            if (
                key_event.key() == Qt.Key_Return
                and key_event.modifiers() == Qt.ControlModifier
            ) or key_event.key() == Qt.Key_F5:
                self.execute_code()
                return True
            elif (
                key_event.key() == Qt.Key_S
                and key_event.modifiers() == Qt.ControlModifier
            ):
                self.save_file()
                return True
            else:
                return super().eventFilter(obj, event)
        return False

    def event(self, event: QEvent) -> bool:
        """Process events passed directly to the editor.

        Handles tooltip events for code hints.

        Parameters
        ----------
        event : QEvent
            The event to process.

        Returns
        -------
        bool
            True if the event was handled.
        """
        if event.type() == QEvent.ToolTip:
            self.process_tooltip(event)
            return True
        return TextEdit.event(self, event)

    def process_tooltip(self, event: QEvent) -> None:
        """Process a tooltip event (placeholder for MEL help integration).

        Parameters
        ----------
        event : QEvent
            The tooltip event.
        """
        from PySide6.QtCore import QPoint
        from PySide6.QtGui import QToolTip

        help_event = event
        pos = QPoint(help_event.pos())
        cursor = self.cursorForPosition(pos)
        cursor.select(QTextCursor.WordUnderCursor)
        QToolTip.showText(help_event.globalPos(), "Coming soon help tooltips")

    def execute_code(self) -> None:
        """Execute the MEL code in the editor.

        If text is selected, only the selection is executed.
        In live mode the editor is cleared after execution.
        """
        if self.execute_selected:
            cursor = self.textCursor()
            text = cursor.selectedText()
            text = text.replace("\u2029", "\n")
            if self.live:
                self.update_output.emit(self.toPlainText() + "\n")
            value = mel.eval(text)
            if self.live and value is not None:
                value = str(value) + "\n"
                self.update_output_html.emit(value)
        else:
            text_to_run = self.toPlainText()
            if self.live:
                self.update_output.emit(text_to_run)
                self.clear()
            value = mel.eval(text_to_run)
            if self.live and value is not None:
                value = str(value)
                self.update_output.emit(value)

    def selection_changed(self, state: bool) -> None:
        """Track whether text is selected for partial execution.

        Parameters
        ----------
        state : bool
            True if text is selected.
        """
        self.execute_selected = state

    def save_file(self) -> bool:
        """Save the current editor content.

        If the filename is ``untitled.mel`` a save dialog is shown.

        Returns
        -------
        bool
            True if saved, False if cancelled.
        """
        if self.filename == "untitled.mel":
            filename, _ = QFileDialog.getSaveFileName(
                self, "Save As", "", "Mel (*.mel)"
            )
            if not filename:
                return False
            self.filename = filename
            self.add_file_to_workspace.emit(filename)
        if self.filename:
            with open(self.filename, "w") as code_file:
                code_file.write(self.toPlainText())
            self.needs_saving = False
            self.generate_code_model()
            self._update_tab_title()
        return True

    def extract_mel_function(self, code: str) -> str:
        """Extract the function name from a MEL proc definition.

        Parameters
        ----------
        code : str
            The proc definition string.

        Returns
        -------
        str
            The function name, or empty if not found.
        """
        parts = code.split(" ")
        for exp in parts:
            if "(" in exp:
                return exp[: exp.find("(")]
        return ""

    def generate_code_model(self) -> None:
        """Scan the document for MEL proc definitions and build a code model."""
        document = self.document()
        lines_of_code = document.blockCount()
        self.code_model.clear()
        for line in range(lines_of_code):
            text = document.findBlockByLineNumber(line).text()
            if "global" in text and "proc" in text:
                function = self.extract_mel_function(text)
                self.code_model.append(
                    self.code_model_data(
                        scope="global", line_number=line + 1, function_name=function
                    )
                )
            elif "proc" in text:
                function = self.extract_mel_function(text)
                self.code_model.append(
                    self.code_model_data(
                        scope="proc", line_number=line + 1, function_name=function
                    )
                )
        self.code_model_changed.emit()
