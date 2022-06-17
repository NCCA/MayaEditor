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

"""PythonTextEdit and related classes this Class extends the QPlainTextEdit."""
import importlib.util
from typing import Any, Callable, Optional, Type

import jedi
import maya.api.OpenMaya as OpenMaya
from maya import utils
from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import (QFileDialog, QInputDialog, QLineEdit,
                               QPlainTextEdit, QTextEdit, QToolTip, QWidget)

from .PythonHighlighter import PythonHighlighter
from .TextEdit import TextEdit


class PythonTextEdit(TextEdit):
    """Custom QPlainTextEdit.

    Custom QPlainTextEdit to allow us to add extra code editor features such as
    shortcuts zooms and line numbers
    """
    

    def __init__(
        self ,read_only : bool =True, show_line_numbers : bool=True , code: Optional[str] = None, filename: Optional[str] = None, live : bool =False,parent: Optional[Any] = None):
        """
        Construct our PythonTextEdit.

        Parameters:
        code (str): The source code for the editor.
        filename (str) : The name of the source file used by the tab.
        live (bool) : if set to true we echo output and clear on run like the maya one
        parent (QObject) : parent widget.
        """
        super().__init__( read_only , show_line_numbers , code,filename, parent)

        self.highlighter = PythonHighlighter()
        self.highlighter.setDocument(self.document())
        self.execute_selected = False
        self.installEventFilter(self)
        self.live=live

        

    def eventFilter(self, obj: QObject, event: QEvent):
        """Event filter for key events.

        We filter different keyboard combinations for shortcuts here at present.
        Ctrl (Command mac) + Return : execute code.
        Ctrl (Command mac) + S : save file.
        Ctrl (Command mac) + + or = : zoom in.
        Ctrl (Command mac) + - : zoom out.
        Ctrl (Command mac) + G : goto line
        F5 : run current file
        Parameters :
        obj (QObject) : the object passing the event.
        event (QEvent) : the event to be processed.
        Returns : True on processed or False to pass to next event filter.

        """
        if isinstance(obj, PythonTextEdit) and event.type() == QEvent.KeyPress:
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
                return False
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
        elif event.type() is QEvent.Wheel:
            if event.modifiers() == Qt.ControlModifier:
                if event.delta() > 0:
                    self.zoomIn(1)
                else:
                    self.zoomOut(1)
            return True
        else:
            return QPlainTextEdit.event(self, event)

    def process_tooltip(self, event):
        """Process the tooltip event.

        Called from the event filter and is used to generate code hints
        Parameters :
        event (QEvent) : the toolTip event.
        """
        # Grab the help event and get the position
        jedi_data = jedi.Script(self.toPlainText())
        help_event = event
        pos = QPoint(help_event.pos())
        # find text under the cursos and lookup
        cursor = self.cursorForPosition(pos)
        cursor.select(QTextCursor.WordUnderCursor)
        hint = jedi_data.help(line=cursor.blockNumber() + 1)
        signatures = jedi_data.call_signatures()
        # help text is not the best, form to HTML and paragraph
        raw_text = cursor.selectedText()
        if hint:
            try:
                doc_str = eval(raw_text).__doc__
            except:
                doc_str = ""
            help_text = f"""<html><p><b>Name : </b>{hint[0].name}</p><br>
                <p><b>Description : </b> {hint[0].description}  </p>
                <br><p> <b>Docs</b> : <pre>{doc_str}</pre> </p>
                </html>"""
            QToolTip.showText(help_event.globalPos(), help_text)

    def execute_code(self):
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
                self.update_output.emit(self.toPlainText()+"\n")
                self.draw_line.emit()

            value = utils.executeInMainThreadWithResult(text)
            if self.live and value != None:
                value=str(value)+"\n"
                self.draw_line.emit()

                self.update_output_html.emit(value)
                self.draw_line.emit()

        else:
            text_to_run = self.toPlainText()+"\n"
            if self.live:
                self.update_output.emit(text_to_run)
                self.draw_line.emit()
                self.clear()
            value = utils.executeInMainThreadWithResult(text_to_run)
            # if we are a live window output the results
            if self.live and value != None:
                value=str(value)
                self.update_output.emit(value)

    def save_file(self):
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
        # Now we have a filename save
        with open(self.filename, "w") as code_file:
            code_file.write(self.toPlainText())
        self.needs_saving = False
        return True

