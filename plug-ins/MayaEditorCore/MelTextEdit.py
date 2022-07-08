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
"""MelTextEdit and related classes this Class extends the QPlainTextEdit."""
import importlib.util
from lib2to3.pgen2.pgen import generate_grammar
from pydoc import doc
from typing import Any, Callable, Optional, Type

import maya.api.OpenMaya as OpenMaya
import maya.mel as mel
from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import (
    QFileDialog,
    QInputDialog,
    QLineEdit,
    QPlainTextEdit,
    QTextEdit,
    QToolTip,
    QWidget,
)

# from .LineNumberArea import LineNumberArea
from .MelHighlighter import MelHighlighter
from .TextEdit import TextEdit


class MelTextEdit(TextEdit):
    """Custom QPlainTextEdit.


    Custom QPlainTextEdit to allow us to add extra code editor features such as
    shortcuts zooms and line numbers
    """

    def __init__(
        self,
        read_only: bool = True,
        show_line_numbers: bool = True,
        code: Optional[str] = None,
        filename: Optional[str] = None,
        live: bool = False,
        parent: Optional[Any] = None,
    ):
        """
        Construct our MelTextEdit.

        Parameters:
        code (str): The source code for the editor.
        filename (str) : The name of the source file used by the tab.
        live (bool) : if set to true we echo output and clear on run like the maya one
        parent (QObject) : parent widget.
        """
        super().__init__(read_only, show_line_numbers, code, filename, parent)

        self.highlighter = MelHighlighter()
        self.highlighter.setDocument(self.document())
        self.execute_selected = False
        self.live = live
        self.copyAvailable.connect(self.selection_changed)
        self.code_model = list()

    def eventFilter(self, obj: QObject, event: QEvent):
        """Event filter for key events.

        We filter different keyboard combinations for shortcuts here at present.
        Ctrl (Command mac) + Return : execute code.
        Ctrl (Command mac) + S : save file.
        F5 : run current file
        Parameters :
        obj (QObject) : the object passing the event.
        event (QEvent) : the event to be processed.
        Returns : True on processed or False to pass to next event filter.

        """
        if isinstance(obj, MelTextEdit) and event.type() == QEvent.KeyPress:
            if (
                event.key() == Qt.Key_Return
                and event.modifiers() == Qt.ControlModifier
                or event.key() == Qt.Key_F5
            ):
                self.execute_code()
                return True
            elif event.key() == Qt.Key_S and event.modifiers() == Qt.ControlModifier:
                self.save_file()
                return True
            else:
                return False  # return super().eventFilter(obj, event)
        else:
            return False

    def event(self, event):
        """Process the events directly passed to the editor.

        This is mainly used for toolTips and Wheel events at present but may be
        used for more in the future.

        Parameters :
        event (QEvent) : the event to be processed.
        Returns :  True is event is processed here else False to pass on.
        """
        if event.type() is QEvent.ToolTip:
            self.process_tooltip(event)
            return True
        else:
            return TextEdit.event(self, event)

    def process_tooltip(self, event) -> None:
        """Process the tooltip event.

        Called from the event filter and is used to generate code hints
        Parameters :
        event (QEvent) : the toolTip event.
        """
        # Grab the help event and get the position
        help_event = event
        pos = QPoint(help_event.pos())
        # find text under the cursos and lookup
        cursor = self.cursorForPosition(pos)
        cursor.select(QTextCursor.WordUnderCursor)
        raw_text = cursor.selectedText()
        QToolTip.showText(help_event.globalPos(), "Coming soon help tooltups")

    def execute_code(self) -> None:
        """Execute the code in the current Editor.

        This will either execute the selected text or the whole file dependant upon
        the execute_selected flag. Called from the event filter on CTR + Return.
        """
        if self.execute_selected:
            cursor = self.textCursor()
            text = cursor.selectedText()
            # returns a unicode paragraph instead of \n
            # so replace
            text = text.replace("\u2029", "\n")
            if self.live:
                self.update_output.emit(self.toPlainText() + "\n")

            value = mel.eval(text)
            if self.live and value != None:
                value = str(value) + "\n"
                self.update_output_html.emit(value)
        else:
            text_to_run = self.toPlainText()
            if self.live:
                self.update_output.emit(text_to_run)
                self.clear()
            value = mel.eval(text_to_run)
            # if we are a live window clear the editor
            if self.live and value != None:
                value = str(value)
                self.update_output.emit(value)

    def selection_changed(self, state):
        """Signal called when text is selected.
        This is used to set the flag in the editor so if we have selected code we
        only execute that rather than the whole file.
        """
        self.execute_selected = state

    def save_file(self) -> bool:
        """Save the current editor file.

        This is called from the event filter or menu when the file is to be saved.
        It will check to see if the file is called untitled.py if so this will be an unsaved file so will popup a file save dialog, if this is canceled False will be returned else true for a saved file.

        Returns : True if saved else False to flag cancel was selected.
        """
        if self.filename == "untitled.py":
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Save As",
                "",
                ("Python (*.py)"),
            )
            if filename is None:
                return False
            else:
                self.filename = filename
                self.parent.workspace.add_file(filename)

        # Now we have a filename save
        with open(self.filename, "w") as code_file:
            code_file.write(self.toPlainText())
        self.needs_saving = False
        return True

    def text_changed(self):
        self.generate_code_model()
        return super().text_changed()

    def extract_mel_function(self, code: str) -> str:
        """
        Scan the mel function and extract, easiest way is to search for
        ( as a function must have this.
        """
        code = code.split(" ")
        for exp in code:
            if "(" in exp:
                return exp[: exp.find("(")]

    def generate_code_model(self):
        document = self.document()
        lines_of_code = document.blockCount()
        self.code_model.clear()
        for line in range(lines_of_code):
            text = document.findBlockByLineNumber(line).text()
            if "global" in text and "proc" in text:
                function = self.extract_mel_function(text)
                self.code_model.append(["global", line + 1, function])
            elif "proc" in text:
                function = self.extract_mel_function(text)
                self.code_model.append(["proc", line + 1, function])
