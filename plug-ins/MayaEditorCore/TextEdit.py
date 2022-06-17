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
"""TextEdit and related classes this Class extends the QPlainTextEdit.

This is the base class of all the editor text edits

"""
import importlib.util
from turtle import width
from typing import Any, Callable, Optional, Type

import jedi
import maya.api.OpenMaya as OpenMaya
from maya import utils
from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import (QFileDialog, QInputDialog, QLineEdit,
                               QPlainTextEdit, QTextEdit, QToolTip, QWidget)

from .LineNumberArea import LineNumberArea


class TextEdit(QPlainTextEdit):
    """Custom QPlainTextEdit.

    Custom QPlainTextEdit to allow us to add extra code editor features such as
    shortcuts zooms and line numbers
    """
    update_output = Signal(str)
    update_output_html = Signal(str)
    draw_line = Signal()

    def __init__( self ,read_only : bool =True, show_line_numbers : bool=True , code: Optional[str] = None, filename: Optional[str] = None, parent: Optional[Any] = None):
        """
        Construct our TextEdit.

        Parameters:
        font (QFont) : font to use
        parent (QObject) : parent widget.
        """
        super().__init__(parent)
        self.parent: Callable[[QObject], QObject] = parent
        self.setStyleSheet("background-color: rgb(30,30,30);color : rgb(250,250,250);")
        self.tab_size=4
        self.installEventFilter(self)
        self.setReadOnly(read_only)
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.filename = filename
        if code  :
            self.setPlainText(code)
        self.installEventFilter(self)
        # if we need to display line numbers install events
        self.show_line_numbers=show_line_numbers
        if self.show_line_numbers :
            self.line_number_area: LineNumberArea = LineNumberArea(self)
            self.blockCountChanged.connect(self.update_line_number_area_width)
            self.updateRequest.connect(self.update_line_number_area)
            self.cursorPositionChanged.connect(self.highlight_current_line)
        self.needs_saving = False
        # hack as textChanged signal always called on set of text
        self.first_edit = False
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        
    

    def text_changed(self):
        """Signal called when text changed.

        When the initial text is set this signal is executed so add
        logic to ensure needs saving only gets set on 2nd call and beyond.
        """
        if self.first_edit == False:
            self.first_edit = True
        else:
            self.needs_saving = True


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
        Ctrl (Command mac) + S : save file.
        Ctrl (Command mac) + + or = : zoom in.
        Ctrl (Command mac) + - : zoom out.
        Ctrl (Command mac) + G : goto line
        Parameters :
        obj (QObject) : the object passing the event.
        event (QEvent) : the event to be processed.
        Returns : True on processed or False to pass to next event filter.

        """
        if isinstance(obj, TextEdit) and event.type() == QEvent.KeyPress: 
            if event.key() == Qt.Key_S and event.modifiers() == Qt.ControlModifier:
                self.save_file()
                return True
            elif (
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
                return QPlainTextEdit.event(self, event)
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


    def save_file(self):
        """Save the current editor file.

        This is called from the event filter or menu when the file is to be saved.
        It will check to see if the file is called untitled.py if so this will be an unsaved file so will popup a file save dialog, if this is canceled False will be returned else true for a saved file.

        Returns : True if saved else False to flag cancel was selected.
        """
        if self.filename == "untitled.txt":
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Save As",
                "",
                ("All Files (*.*)"),
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
    def append_line(self) :
        self.moveCursor(QTextCursor.End)
        cursor=self.textCursor()
 #       cursor.insertHtml('<hr>')
        self.appendHtml('<hr>')


    def line_number_area_width(self):
        """Get the size of the line area.

        This calculates the line area size based on Font metrics.

        Returns : size of the space needed for line area.
        """
        digits = 2
        count = max(1, self.blockCount())
        while count >= 10:
            count /= 10
            digits += 1
        space =  self.fontMetrics().averageCharWidth() * digits
        return space

    def update_line_number_area_width(self, _):
        """Update the line area width."""
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        """Update the Line area numbers."""
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(
                0, rect.y(), self.line_number_area.width(), rect.height()
            )

        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        """Event called on editor resize."""
        super().resizeEvent(event)
        if self.show_line_numbers :
            cr = self.contentsRect()
            self.line_number_area.setGeometry(
                QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height())
            )

    def lineNumberAreaPaintEvent(self, event):
        """Paint Event for the line number area."""
        mypainter = QPainter(self.line_number_area)
        mypainter.setFont(self.font())
        mypainter.fillRect(event.rect(), QColor(43, 43, 43))

        block = self.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()

        # Just to make sure I use the right font
        height = self.fontMetrics().height()
        width= self.fontMetrics().averageCharWidth()
        while block.isValid() and (top <= event.rect().bottom()):
            if block.isVisible() and (bottom >= event.rect().top()):
                number = str(blockNumber + 1) + " "
                mypainter.setPen(Qt.yellow)
                mypainter.drawText(
                    width, top, self.line_number_area.width(), height, Qt.AlignRight, number
                )

            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            blockNumber += 1

    def highlight_current_line(self):
        """Highlight the current line."""
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


