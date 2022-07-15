from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtUiTools import *
from PySide2.QtWidgets import *


# As this is a popup on the text edit we need a widget, parent will handle position
class FindDialog(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.layout = QGridLayout()
        self.setLayout(self.layout)
        self.text_search = QLineEdit()
        self.text_search.setToolTip("search")
        self.layout.addWidget(self.text_search, 0, 0, 1, 2)
        self.text_search.textChanged.connect(self.parent.search_text)
        self.text_search.returnPressed.connect(self.return_pressed)
        self.items_found = QLabel("no results found")
        self.layout.addWidget(self.items_found, 0, 3)

        self.hide_button = QToolButton()
        self.hide_button.setToolTip("hide")
        self.hide_button.clicked.connect(self.hide)
        self.layout.addWidget(self.hide_button, 0, 8)
        self.replace = QLineEdit()
        self.layout.addWidget(self.replace, 1, 0, 1, 2)
        self.replace.setToolTip("replace")
        # need to set dimensions so do a show, then hide as not visible by default
        self.show()
        self.hide()
        # self.setWindowFlags(Qt.Popup)

    def return_pressed(self):
        self.parent.find_next(self.text_search.text())
