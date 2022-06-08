"""Editor Tool Bar code

This file contains the class to produce the main toolbar and buttons for the editor, most functions will connect to the parent 
"""
from typing import Any, Optional

from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtUiTools import *
from PySide2.QtWidgets import *


class EditorToolBar(QToolBar):
    """Inherit from the main toolbar class and extend"""

    def __init__(self, parent: Optional[Any] = None):
        """Construct our toolbar and connect items"""
        super().__init__(parent)
        self.parent: Callable[[QObject], QObject] = parent
        self.setFloatable(True)
        self.setMovable(True)
        # Add run button for active editor
        run_button = QPushButton("Run")
        run_button.clicked.connect(parent.tool_bar_run_clicked)
        self.addWidget(run_button)
        # add goto section
        self.addSeparator()
        label = QLabel("Goto :")
        self.addWidget(label)
        goto_number = QSpinBox()
        goto_number.setMinimum(1)
        goto_number.setMaximum(999999)
        self.addWidget(goto_number)
