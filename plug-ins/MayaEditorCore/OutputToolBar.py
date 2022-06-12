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
"""Output Tool Bar code

This file contains the class to produce the main toolbar and buttons for the editor, most functions will connect to the parent 
"""
from typing import Any, Optional

from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtUiTools import *
from PySide2.QtWidgets import *


class OutputToolBar(QToolBar):
    """Inherit from the main toolbar class and extend"""

    def __init__(self, parent: Optional[Any] = None):
        """Construct our toolbar and connect items

        This creates the main toolbar with run, run default goto, search etc
        Parameters :
        parent (QDialog) : the parent widget must be the EditorDialog
        """
        super().__init__(parent)
        self.parent: Callable[[QObject], QObject] = parent
        self.setFloatable(False)
        self.setMovable(False)
        clear_output = QPushButton("Clear Output")
        clear_output.clicked.connect(parent.output_window.clear)
        self.addWidget(clear_output)
        

