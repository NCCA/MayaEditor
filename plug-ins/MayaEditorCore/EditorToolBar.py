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
        """Construct our toolbar and connect items

        This creates the main toolbar with run, run default goto, search etc
        Parameters :
        parent (QDialog) : the parent widget must be the EditorDialog
        """
        super().__init__(parent)
        self.parent: Callable[[QObject], QObject] = parent
        self.setFloatable(True)
        self.setMovable(True)
        # Add the run project this allows us to run a file as the main that
        # isn't necessarily the file we are editing, something that bugs me on
        # a lot of editors
        run_project = QPushButton("Run Project")
        run_project.clicked.connect(parent.tool_bar_run_project_clicked)
        self.addWidget(run_project)
        self.active_project_file = QComboBox()
        self.addWidget(self.active_project_file)
        self.addSeparator()
        # Add run button for active editor
        run_button = QPushButton("Run Current")
        run_button.clicked.connect(parent.tool_bar_run_clicked)
        self.addWidget(run_button)
        # add goto section
        self.addSeparator()
        label = QLabel("Goto :")
        self.addWidget(label)
        goto_number = QSpinBox()
        goto_number.setMinimum(1)
        goto_number.setMaximum(999999)
        goto_number.valueChanged.connect(parent.tool_bar_goto_changed)
        self.addWidget(goto_number)
        

    def add_to_active_file_list(self, filename: str) -> None:
        """Add filename to run project combo."""
        self.active_project_file.addItem(filename)

    def remove_from_active_file_list(self, filename : str) -> None :
        print(f"{filename}")
        index= self.active_project_file.findText(filename,Qt.MatchContains)
        self.active_project_file.removeItem(index)
