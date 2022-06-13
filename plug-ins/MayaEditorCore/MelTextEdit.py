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
from typing import Any, Callable, Optional, Type

import jedi
import maya.api.OpenMaya as OpenMaya
import maya.mel as mel
from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import (QFileDialog, QInputDialog, QLineEdit,
                               QPlainTextEdit, QTextEdit, QToolTip, QWidget)

from .LineNumberArea import LineNumberArea
from .MelHighlighter import MelHighlighter


class MelTextEdit(QPlainTextEdit):
    """Custom QPlainTextEdit.
    

    Custom QPlainTextEdit to allow us to add extra code editor features such as
    shortcuts zooms and line numbers
    """
    update_output = Signal(str)
    update_output_html = Signal(str)
    draw_line = Signal()
    
    def __init__(
        self, code: str, filename: str, live=False, parent: Optional[Any] = None
    ):
        """
        Construct our MelTextEdit.

        Parameters:
        code (str): The source code for the editor.
        filename (str) : The name of the source file used by the tab.
        live (bool) : if set to true we echo output and clear on run like the maya one
        parent (QObject) : parent widget.
        """
        super().__init__(parent)
        self.line_number_area: LineNumberArea = LineNumberArea(self)
        self.setStyleSheet("background-color: rgb(30,30,30);color : rgb(250,250,250);")
        self.filename = filename
        self.setPlainText(code)
        self.highlighter = MelHighlighter()
        self.highlighter.setDocument(self.document())
        font = QFont(
            "Andale Mono",
            18,
            400,
            False,
        )
        self.tab_size = 4
        self.execute_selected = False
        self.set_editor_fonts(font)
        self.installEventFilter(self)
        self.copyAvailable.connect(self.selection_changed)
        self.textChanged.connect(self.text_changed)
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)
        self.needs_saving = False
        # hack as textChanged signal always called on set of text
        self.first_edit = False
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.live = live
        # Add some extra controls to this widget

    def set_editor_fonts(self, font):
        """Allow the editor to change fonts."""
        metrics = QFontMetrics(font)
        self.setTabStopDistance(
            QFontMetricsF(self.font()).horizontalAdvance(" ") * self.tab_size
        )

        self.setFont(font)

    def selection_changed(self, state):
        """Signal called when text is selected.

        This is used to set the flag in the editor so if we have selected code we
        only execute that rather than the whole file.
        """
        self.execute_selected = state

    def text_changed(self):
        """Signal called when text changed.

        When the initial text is set this signal is executed so add
        logic to ensure needs saving only gets set on 2nd call and beyond.
        """
        if self.first_edit == False:
            self.first_edit = True
        else:
            self.needs_saving = True

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
            value = mel.eval(text)
            if self.live and value != None:
                value=str(value)+"\n"
                self.draw_line.emit()

                self.update_output_html.emit(value)
                self.draw_line.emit()

        else:
            text_to_run = self.toPlainText()
            if self.live:
                self.update_output.emit(text_to_run)
                self.draw_line.emit()
                self.clear()
            value = mel.eval(text_to_run)
            # if we are a live window clear the editor
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

    def line_number_area_width(self):
        """Get the size of the line area.

        This calculates the line area size based on Font metrics.

        Returns : size of the space needed for line area.
        """
        digits = 1
        count = max(1, self.blockCount())
        while count >= 10:
            count /= 10
            digits += 1
        space = 8 + self.fontMetrics().width("9") * digits
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
        while block.isValid() and (top <= event.rect().bottom()):
            if block.isVisible() and (bottom >= event.rect().top()):
                number = str(blockNumber + 1) + " "
                mypainter.setPen(Qt.yellow)
                mypainter.drawText(
                    0, top, self.line_number_area.width(), height, Qt.AlignRight, number
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
