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

    def __init__(self, code, filename, parent=None):
        super().__init__(parent)
        # self.setMouseTracking(True)
        self.parent = parent
        self.lineNumberArea = LineNumberArea(self)
        self.setStyleSheet("background-color: rgb(30,30,30);color : rgb(250,250,250);")
        self.filename = filename
        self.needs_saving = False
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
        self.needs_saving = True

    def eventFilter(self, obj, event):
        if isinstance(obj, PlainTextEdit):
            if event.type() == QEvent.KeyPress:
                if (
                    event.key() == Qt.Key_Return
                    and event.modifiers() == Qt.ControlModifier
                ):
                    self.execute_code()
                    return True
                elif (
                    event.key() == Qt.Key_S and event.modifiers() == Qt.ControlModifier
                ):
                    self.save_file()
                    return True
                else:
                    return False
        else:
            return False

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
        # if file is called untitled.py it needs saving as
        if self.filename == "untitled.py":
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Save As",
                "",
                ("Python (*.py)"),
            )
            if filename is None:
                return
            else:
                self.filename = filename

        with open(self.filename, "w") as code_file:
            code_file.write(self.toPlainText())
            self.needs_saving = False

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
            self.lineNumberArea.scroll(0, dy)
        else:
            self.lineNumberArea.update(
                0, rect.y(), self.lineNumberArea.width(), rect.height()
            )

        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)

        cr = self.contentsRect()
        self.lineNumberArea.setGeometry(
            QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height())
        )

    def lineNumberAreaPaintEvent(self, event):
        mypainter = QPainter(self.lineNumberArea)
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
                    0, top, self.lineNumberArea.width(), height, Qt.AlignRight, number
                )

            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            blockNumber += 1

    def highlight_current_line(self):
        extraSelections = []

        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            lineColor = QColor(Qt.lightgray)
            selection.format.setBackground(lineColor)
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extraSelections.append(selection)
        self.setExtraSelections(extraSelections)
