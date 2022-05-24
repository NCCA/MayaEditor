from maya import utils
from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import QPlainTextEdit, QToolTip, QWidget

from .Highlighter import Highlighter


class PlainTextEdit(QPlainTextEdit):
    """
    Need to override the simple QPlainTextEdit so we can capture the
    ToolTip event and create custom ones from us.
    """

    def __init__(self, code, parent=None):
        super().__init__(parent)
        # self.setMouseTracking(True)
        # self.parent = parent
        self.setStyleSheet("background-color: rgb(30,30,30);color : rgb(250,250,250);")

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

    def set_editor_fonts(self, font):
        """allow the editor to change fonts"""
        metrics = QFontMetrics(font)
        self.setTabStopDistance(
            QFontMetricsF(self.font()).horizontalAdvance(" ") * self.tab_size
        )

        self.setFont(font)

    def selection_changed(self, state):
        self.execute_selected = state

    def eventFilter(self, obj, event):
        if isinstance(obj, PlainTextEdit):
            if event.type() == QEvent.KeyPress:
                if (
                    event.key() == Qt.Key_Return
                    and event.modifiers() == Qt.ControlModifier
                ):
                    if self.execute_selected:
                        cursor = self.textCursor()
                        text = cursor.selectedText()
                        # returns a unicode paragraph instead of \n
                        # so replace
                        text = text.replace("\u2029", "\n")
                        value = utils.executeInMainThreadWithResult(text)
                    else:

                        value = utils.executeInMainThreadWithResult(self.toPlainText())

                    return True
                else:
                    return False
        else:
            return False

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
