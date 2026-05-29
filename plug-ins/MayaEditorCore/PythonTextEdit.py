#!/usr/bin/env python3
# Copyright (C) 2022  Jonathan Macey
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""Python editor widget extending TextEdit with highlighting, AST code model and execution."""

import ast
from collections import namedtuple
from typing import Any, Dict, List, Optional

import maya.cmds as cmds
from maya import utils
from PySide6.QtCore import QEvent, QObject, QPoint, QStringListModel, Qt, QTimer, Signal, Slot
from PySide6.QtGui import QColor, QKeyEvent, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QCompleter, QFileDialog, QTextEdit, QToolTip

from .JediCompleter import JediCompletionPopup, get_jedi_completions
from .PythonHighlighter import PythonHighlighter
from .RuffLinter import Diagnostic, RuffLinter
from .TextEdit import TextEdit

# Optional Jedi-based autocomplete support
try:
    from jedi import Script  # type: ignore

    _JEDI_AVAILABLE = True
except Exception:
    Script = None  # type: ignore
    _JEDI_AVAILABLE = False

code_model_data = namedtuple("code_model_data", "type line_number name")  # noqa: PYI024
class_model_data = namedtuple("class_model_data", "name line_number")  # noqa: PYI024

# Underline colours for diagnostics
_COLOUR_ERROR = QColor(255, 80, 80, 220)  # red
_COLOUR_WARNING = QColor(255, 200, 0, 200)  # amber


class PythonTextEdit(TextEdit):
    """QPlainTextEdit customised for Python script editing with highlighting and execution.

    Signals
    -------
    code_model_changed : Signal()
        Emitted when the code model (class/function list) is regenerated.
    lint_results_changed : Signal(list)
        Emitted with a list of :class:`~RuffLinter.Diagnostic` whenever a lint
        run completes.  Connect this to a lint-results panel.
    """

    completer = QCompleter()
    code_model_changed = Signal()
    lint_results_changed = Signal(list)  # List[Diagnostic]

    # Debounce interval in milliseconds before triggering a lint run
    _LINT_DEBOUNCE_MS: int = 500

    def __init__(
        self,
        read_only: bool = True,
        show_line_numbers: bool = True,
        code: Optional[str] = None,
        filename: Optional[str] = None,
        live: bool = False,
        parent: Optional[Any] = None,
    ) -> None:
        """Construct a PythonTextEdit.

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
        self.highlighter = PythonHighlighter()
        self.highlighter.setDocument(self.document())
        self.execute_selected: bool = False
        self.installEventFilter(self)
        self.live: bool = live

        # Use custom Jedi popup instead of QCompleter
        self._jedi_popup = JediCompletionPopup(self)
        self._jedi_popup.completion_selected.connect(self._insert_completion)
        self._popup_enabled = True  # Can be toggled via toolbar to hide popup
        self.copyAvailable.connect(self.selection_changed)
        self.code_model: List[Any] = []
        self.generate_code_model()

        # --- Ruff linting setup ---
        self._diagnostics: List[Diagnostic] = []
        self._linter = RuffLinter(parent=self)
        self._linter.diagnostics_ready.connect(self._apply_diagnostics)

        self._lint_timer = QTimer(self)
        self._lint_timer.setSingleShot(True)
        self._lint_timer.setInterval(self._LINT_DEBOUNCE_MS)
        self._lint_timer.timeout.connect(self._run_linter)

        # Trigger debounce on every document change
        self.document().contentsChanged.connect(self._lint_timer.start)

        # Enable mouse-tracking so we can show tooltips on hover
        self.setMouseTracking(True)

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """Filter key events for Python editor shortcuts.

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
        if isinstance(obj, PythonTextEdit) and event.type() == QEvent.KeyPress:
            key_event = event
            if (
                key_event.key() == Qt.Key_Return and key_event.modifiers() == Qt.ControlModifier
            ) or key_event.key() == Qt.Key_F5:
                self.execute_code()
                return True
            elif key_event.key() == Qt.Key_S and key_event.modifiers() == Qt.ControlModifier:
                self.save_file()
                return True
            else:
                return super().eventFilter(obj, event)
        return False

    def event(self, event: QEvent) -> bool:
        """Process events passed directly to the editor.

        Intercepts :class:`QEvent.ToolTip` to display lint diagnostic messages
        when the mouse hovers over an underlined region.
        """
        if event.type() == QEvent.ToolTip:
            help_event = event
            pos: QPoint = help_event.pos()
            cursor = self.cursorForPosition(pos)
            tip = self._tooltip_at_cursor(cursor)
            if tip:
                QToolTip.showText(help_event.globalPos(), tip, self)
            else:
                QToolTip.hideText()
            return True
        return TextEdit.event(self, event)

    # ------------------------------------------------------------------
    # Completion helpers (Jedi)
    # ------------------------------------------------------------------
    def _update_completions(self) -> None:
        """Query Jedi for completions at the current cursor and show custom popup."""
        # Always get completions but only show popup if enabled
        if not self._popup_enabled:
            return

        try:
            cursor = self.textCursor()
            source = self.document().toPlainText()
            line = cursor.blockNumber() + 1
            col = cursor.positionInBlock()

            # Get completions from Jedi
            completions = get_jedi_completions(source, line, col, self.filename or "")

            # Show custom popup
            if completions:
                self._jedi_popup.show_completions(self, completions)
            else:
                self._jedi_popup.hide()
        except Exception:
            pass

    @Slot(bool)
    def setAutoCompletion(self, enabled: bool) -> None:
        """Enable or disable the Jedi completion popup."""
        self._popup_enabled = enabled
        if not enabled:
            self._jedi_popup.hide()

    def _insert_completion(self, text: str) -> None:
        """Insert a selected completion into the editor, replacing the current word."""
        try:
            cursor = self.textCursor()
            doc_text = self.toPlainText()
            pos = cursor.position()

            # Find the start of the current word (alphanumeric or underscore)
            start = pos
            while (
                start > 0
                and start - 1 < len(doc_text)
                and (doc_text[start - 1].isalnum() or doc_text[start - 1] == "_")
            ):
                start -= 1

            # Safety check
            if start < 0 or start > len(doc_text) or pos < 0 or pos > len(doc_text):
                return

            partial_word = doc_text[start:pos]

            # Select and replace
            cursor.setPosition(start)
            cursor.setPosition(pos, QTextCursor.KeepAnchor)
            cursor.insertText(text)

            # Move cursor to end of inserted text
            self.setTextCursor(cursor)
        except Exception:
            pass

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle key events with Jedi popup integration.

        If the Jedi completion popup is visible, navigation keys are forwarded
        to the popup. Otherwise the key is processed normally, and completions
        are updated after alphanumeric or dot input.
        """
        if self._jedi_popup.isVisible():
            if event.key() in (Qt.Key_Up, Qt.Key_Down, Qt.Key_Return, Qt.Key_Enter, Qt.Key_Escape, Qt.Key_Tab):
                self._jedi_popup.keyPressEvent(event)
                return

        # Process the key normally
        super().keyPressEvent(event)

        # Update completions after typing
        try:
            ch = event.text()
            if ch and (ch.isalnum() or ch == "_" or ch == "."):
                self._update_completions()
            elif ch in (" ", "(", ")", "[", "]", "{", "}", ",", ";"):
                # Hide popup on these characters
                self._jedi_popup.hide()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def execute_code(self) -> None:
        """Execute the Python code in the editor.

        If text is selected, only the selection is executed.
        In live mode the editor is cleared after execution.
        """
        if self.execute_selected:
            cursor = self.textCursor()
            text = cursor.selectedText()
            text = text.replace("\u2029", "\n")
            if self.live:
                self.update_output.emit(self.toPlainText() + "\n")
                self.draw_line.emit()
            value = utils.executeInMainThreadWithResult(text)
            if self.live and value is not None:
                value = str(value) + "\n"
                self.draw_line.emit()
                self.update_output_html.emit(value)
                self.draw_line.emit()
        else:
            text_to_run = self.toPlainText() + "\n"
            if self.live:
                self.update_output.emit(text_to_run)
                self.draw_line.emit()
                self.clear()
            value = utils.executeInMainThreadWithResult(text_to_run)
            if self.live and value is not None:
                value = str(value)
                self.update_output.emit(value)

    def selection_changed(self, state: bool) -> None:
        """Track whether text is selected for partial execution."""
        self.execute_selected = state

    # ------------------------------------------------------------------
    # File I/O
    # ------------------------------------------------------------------

    def save_file(self) -> bool:
        """Save the current editor content.

        If the filename is ``untitled.py`` a save dialog is shown.
        Also triggers a lint run on save.
        """
        if self.filename == "untitled.py":
            filename, _ = QFileDialog.getSaveFileName(self, "Save As", "", "Python (*.py)")
            if not filename:
                return False
            self.filename = filename
            if self.parent and hasattr(self.parent, "workspace"):
                self.parent.workspace.add_file(filename)
        if self.filename:
            with open(self.filename, "w") as code_file:
                code_file.write(self.toPlainText())
            self.needs_saving = False
            self.generate_code_model()
            self._update_tab_title()
            # Run linter immediately on save (bypass the debounce timer)
            self._run_linter()
        return True

    # ------------------------------------------------------------------
    # Code model
    # ------------------------------------------------------------------

    def extract_classes_and_functions(
        self, node_to_traverse: Any, current_object: List[Any], inside_class: bool = False
    ) -> None:
        """Recursively extract class and function definitions from the AST."""
        for node in node_to_traverse.body:
            if isinstance(node, ast.ClassDef):
                cls_entry: Dict[Any, List[Any]] = {class_model_data(node.name, node.lineno): []}
                current_object.append(cls_entry)
                self.extract_classes_and_functions(
                    node,
                    cls_entry[class_model_data(node.name, node.lineno)],
                    inside_class=True,
                )
            if isinstance(node, ast.FunctionDef):
                func = "method" if inside_class else "function"
                current_object.append(code_model_data(type=func, line_number=node.lineno, name=node.name))

    def generate_code_model(self) -> None:
        """Parse the document with AST and rebuild the code model."""
        document = self.document().toRawText()
        document = document.replace("\u2029", "\n")
        try:
            node_to_traverse = ast.parse(document)
        except SyntaxError:
            # Syntax errors are surfaced via ruff; silently skip AST rebuild
            return
        self.code_model = []  # reset
        self.extract_classes_and_functions(node_to_traverse, self.code_model)
        self.code_model_changed.emit()

    # ------------------------------------------------------------------
    # Linting
    # ------------------------------------------------------------------

    @Slot()
    def _run_linter(self) -> None:
        """Send the current document contents to the background linter."""
        source = self.document().toRawText().replace("\u2029", "\n")
        filename = self.filename or "untitled.py"
        self._linter.lint(source, filename)

    @Slot(list)
    def _apply_diagnostics(self, diagnostics: List[Diagnostic]) -> None:
        """Receive lint results and render underlines in the editor."""
        self._diagnostics = diagnostics
        selections = []
        doc = self.document()

        for diag in diagnostics:
            block = doc.findBlockByLineNumber(diag.row - 1)
            if not block.isValid():
                continue

            start_pos = block.position() + max(0, diag.col - 1)

            end_block = doc.findBlockByLineNumber(diag.end_row - 1)
            if end_block.isValid() and (diag.end_row > diag.row or diag.end_col > diag.col):
                end_pos = end_block.position() + max(0, diag.end_col - 1)
            else:
                end_pos = block.position() + block.length() - 1

            if end_pos <= start_pos:
                end_pos = start_pos + 1

            cursor = QTextCursor(doc)
            cursor.setPosition(start_pos)
            cursor.setPosition(end_pos, QTextCursor.KeepAnchor)

            fmt = QTextCharFormat()
            colour = _COLOUR_ERROR if diag.severity == "error" else _COLOUR_WARNING
            fmt.setUnderlineColor(colour)
            fmt.setUnderlineStyle(QTextCharFormat.WaveUnderline)
            fmt.setToolTip(f"{diag.code}: {diag.message}")

            sel = QTextEdit.ExtraSelection()
            sel.cursor = cursor
            sel.format = fmt
            selections.append(sel)

        self.setExtraSelections(selections)
        self.lint_results_changed.emit(diagnostics)

    def _tooltip_at_cursor(self, cursor: QTextCursor) -> str:
        """Build a tooltip string from lint diagnostics at the given cursor position.

        Parameters
        ----------
        cursor : QTextCursor
            The cursor position to check for diagnostics.

        Returns
        -------
        str
            Newline-separated diagnostic messages, or empty string if none.
        """
        pos = cursor.position()
        messages = []
        for sel in self.extraSelections():
            start = sel.cursor.selectionStart()
            end = sel.cursor.selectionEnd()
            if start <= pos <= end:
                tip = sel.format.toolTip()
                if tip:
                    messages.append(tip)
        return "\n".join(messages)

    def closeEvent(self, event: Any) -> None:  # type: ignore[override]
        """Stop the linter thread when the editor is closed."""
        self._linter.stop()
        super().closeEvent(event)
