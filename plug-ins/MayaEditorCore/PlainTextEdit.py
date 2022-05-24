from maya import utils
from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import QFileDialog, QPlainTextEdit, QToolTip, QWidget

from .Highlighter import Highlighter


class PlainTextEdit(QPlainTextEdit):
    """
    Need to override the simple QPlainTextEdit so we can capture the
    ToolTip event and create custom ones from us.
    """

    def __init__(self, code, filename, parent=None):
        super().__init__(parent)
        # self.setMouseTracking(True)
        # self.parent = parent
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

    # def event(self, event):
    #     """going to re-implement the event for tool tips then
    #     pass on to parent if not a tool tip
    #     """
    #     if event.type() is QEvent.ToolTip:
    #         help_event = event  # QHelpEvent(event,event.pos(),event.globalPos())
    #         pos = QPoint(help_event.pos())
    #         return True
    #     elif event.type() is QKeyEvent:
    #         print("key event")
    #     else:
    #         return QPlainTextEdit.event(self, event)
