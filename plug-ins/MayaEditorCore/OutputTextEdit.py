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
"""OutputTextEdit and related classes this Class extends the QPlainTextEdit."""
import importlib.util
from typing import Any, Callable, Optional, Type

import jedi
import maya.api.OpenMaya as OpenMaya
from maya import utils
from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import QInputDialog, QPlainTextEdit


class OutputTextEdit(QPlainTextEdit):
    """Custom QPlainTextEdit.

    Custom QPlainTextEdit to allow us to add extra code editor features such as
    shortcuts zooms and line numbers
    """

    def __init__( self ,parent: Optional[Any] = None):
        """
        Construct our OutputTextEdit.

        Parameters:
        font (QFont) : font to use
        parent (QObject) : parent widget.
        """
        super().__init__(parent)
        self.parent: Callable[[QObject], QObject] = parent
        self.setStyleSheet("background-color: rgb(30,30,30);color : rgb(250,250,250);")
        self.tab_size=4
        #self.set_editor_fonts(font)
        self.installEventFilter(self)
        self.setReadOnly(True)
        self.setLineWrapMode(QPlainTextEdit.NoWrap)

    @Slot(QFont)
    def set_editor_fonts(self, font):
        """Allow the editor to change fonts."""
        metrics = QFontMetrics(font)
        self.setTabStopDistance(
            QFontMetricsF(self.font()).horizontalAdvance(" ") * self.tab_size
        )

        self.setFont(font)


    def eventFilter(self, obj: QObject, event: QEvent):
        """Event filter for key events.

        We filter different keyboard combinations for shortcuts here at present.
        Ctrl (Command mac) + + or = : zoom in.
        Ctrl (Command mac) + - : zoom out.
        Parameters :
        obj (QObject) : the object passing the event.
        event (QEvent) : the event to be processed.
        Returns : True on processed or False to pass to next event filter.

        """
        if isinstance(obj, OutputTextEdit) and event.type() == QEvent.KeyPress:

            if (
                event.key() in (Qt.Key_Plus, Qt.Key_Equal)
                and event.modifiers() == Qt.ControlModifier
            ):
                obj.zoomIn(1)
                return True
            elif (
                event.key() == Qt.Key_Minus and event.modifiers() == Qt.ControlModifier
            ):
                obj.zoomOut(1)
                return True
            elif event.key() == Qt.Key_G and event.modifiers() == Qt.ControlModifier:
                self.goto_line()
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
    
        if event.type() is QEvent.Wheel:
            if event.modifiers() == Qt.ControlModifier:
                if event.delta() > 0:
                    self.zoomIn(1)
                else:
                    self.zoomOut(1)
            return True
        else:
            return QPlainTextEdit.event(self, event)


    def goto_line(self, line_number: int = 0) -> None:
        """Goto the line entered from the dialog.

        If line_number is 0 popup a dialog else use line this allows
        this method to be used from outside (via the toolbar)
        Parameters :
        line_number (int) : the line to goto, default zero will prompt for value
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
            if not ok:  # cancelled
                return

        cursor = QTextCursor(self.document().findBlockByLineNumber(line_number - 1))
        self.setTextCursor(cursor)

    @Slot(str)
    def append_plain_text(self,text : str) :
        self.moveCursor(QTextCursor.End)
        self.insertPlainText(text)

    @Slot(str)
    def append_html(self,text : str) :
        self.moveCursor(QTextCursor.End)
        cursor=self.textCursor()
        cursor.insertHtml(f"<p><pre>{text}<pre></p>")

    @Slot()
    def draw_line(self) :
        self.moveCursor(QTextCursor.End)
        cursor=self.textCursor()
 #       cursor.insertHtml('<hr>')
        self.appendHtml('<hr>')

