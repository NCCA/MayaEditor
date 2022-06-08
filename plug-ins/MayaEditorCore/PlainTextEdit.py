import importlib.util
from typing import Any

import jedi
from maya import utils
from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import QFileDialog, QPlainTextEdit, QTextEdit, QToolTip, QWidget

from .Highlighter import Highlighter


# Based on the Qt Editor Demo
class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.codeEditor = editor

    def sizeHint(self):
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.codeEditor.lineNumberAreaPaintEvent(event)


class PlainTextEdit(QPlainTextEdit):
    """
    Need to override the simple QPlainTextEdit so we can capture the
    ToolTip event and create custom ones from us.
    """

    parent: Any
    line_number_area: LineNumberArea

    def __init__(self, code, filename, parent=None):
        super().__init__(parent)
        # self.setMouseTracking(True)
        self.parent = parent
        self.line_number_area = LineNumberArea(self)
        self.setStyleSheet("background-color: rgb(30,30,30);color : rgb(250,250,250);")
        self.filename = filename
        self.setPlainText(code)
        self.highlighter = Highlighter()
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

    def set_editor_fonts(self, font):
        """allow the editor to change fonts"""
        metrics = QFontMetrics(font)
        self.setTabStopDistance(
            QFontMetricsF(self.font()).horizontalAdvance(" ") * self.tab_size
        )

        self.setFont(font)

    def selection_changed(self, state):
        self.execute_selected = state

    def text_changed(self):
        """When the initial text is set this signal is executed so add
        logic to ensure needs saving only gets set on 2nd call and beyond"""
        if self.first_edit == False:
            self.first_edit = True
        else:
            self.needs_saving = True

    def eventFilter(self, obj, event):
        """
        Filter events for the text editor, at present only CTRL +s for save
        and CTRL + Return for run are used
        """
        if isinstance(obj, PlainTextEdit) and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Return and event.modifiers() == Qt.ControlModifier:
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
        """going to re-implement the event for tool tips then
        pass on to parent if not a tool tip
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
        # Grab the help event and get the position
        jedi_data = jedi.Script(self.toPlainText())
        help_event = event
        pos = QPoint(help_event.pos())
        # find text under the cursos and lookup
        cursor = self.cursorForPosition(pos)
        cursor.select(QTextCursor.WordUnderCursor)
        print(f"{cursor.blockNumber()+1=}")
        hint = jedi_data.help(line=cursor.blockNumber() + 1)
        print(f"{type(hint)} {hint=}")
        signatures = jedi_data.call_signatures()
        print(f"{signatures=}")
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
        if self.execute_selected:
            cursor = self.textCursor()
            text = cursor.selectedText()
            # returns a unicode paragraph instead of \n
            # so replace
            text = text.replace("\u2029", "\n")
            value = utils.executeInMainThreadWithResult(text)
        else:
            value = utils.executeInMainThreadWithResult(self.toPlainText())

    def save_file(self):
        """save the file, return True is saveed else False to flag cancel was selected"""
        # if file is called untitled.py it needs saving as
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
        digits = 1
        count = max(1, self.blockCount())
        while count >= 10:
            count /= 10
            digits += 1
        space = 8 + self.fontMetrics().width("9") * digits
        return space

    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):

        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(
                0, rect.y(), self.line_number_area.width(), rect.height()
            )

        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)

        cr = self.contentsRect()
        self.line_number_area.setGeometry(
            QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height())
        )

    def lineNumberAreaPaintEvent(self, event):
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
