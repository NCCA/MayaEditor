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
        clear_output = QPushButton("Clear")
        clear_output.clicked.connect(parent.output_window.clear)
        self.addWidget(clear_output)
        copy_to_clipboard = QPushButton("Copy")
        copy_to_clipboard.clicked.connect(self.clipboard_copy)
        self.addWidget(copy_to_clipboard)
        save_to_file = QPushButton("Save")
        save_to_file.clicked.connect(self.save_to_file)
        self.addWidget(save_to_file)
        show_help = QCheckBox("Show Help")
        show_help.setCheckable(True)
        show_help.setChecked(True)
        show_help.toggled.connect(self.show_help)
        self.addWidget(show_help)

    @Slot(bool)
    def show_help(self, state: bool) -> None:
        self.parent.help_frame.setVisible(state)

    def clipboard_copy(self) -> None:
        clipboard = QApplication.clipboard()
        clipboard.clear(mode=clipboard.Clipboard)
        text = self.parent.output_window.toPlainText()
        clipboard.setText(text, mode=clipboard.Clipboard)

    def save_to_file(self):
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Save Output Text",
            "untitled.txt",
            ("Text (*.txt)"),
        )
        if file_name is not None:
            with open(file_name, "w") as output_file:
                output_file.write(self.parent.output_window.toPlainText())
