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
"""Output toolbar with clear, copy, save and help controls."""

from typing import Any, Optional

import maya.cmds as cmds
from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QLabel,
    QPushButton,
    QToolBar,
)


class OutputToolBar(QToolBar):
    """Toolbar for the output window with clear, copy, save, and help controls."""

    autocomplete_toggled = Signal(bool)
    help_toggled = Signal(bool)
    lint_toggled = Signal(bool)

    def __init__(self, parent: Optional[Any] = None) -> None:
        """Construct the output toolbar.

        Parameters
        ----------
        parent : QDialog or None
            The parent EditorDialog instance.
        """
        super().__init__(parent)
        assert parent is not None
        self._output_window = parent.output_window
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
        self.addSeparator()

        label = QLabel("Output Level")
        self.addWidget(label)
        output_level = QComboBox()
        output_level.addItem("Echo All")
        output_level.addItem("Normal")
        output_level.setCurrentIndex(1)
        output_level.currentIndexChanged.connect(self.update_output_level)
        self.addWidget(output_level)
        self.addSeparator()

        show_help = QCheckBox("Show Help")
        show_help.setCheckable(True)
        show_help.setChecked(True)
        show_help.toggled.connect(self.show_help)
        self.addWidget(show_help)

        show_lint = QCheckBox("Show Lint")
        show_lint.setCheckable(True)
        show_lint.setChecked(False)
        show_lint.toggled.connect(self.show_lint)
        self.addWidget(show_lint)

        autocomplete_toggle = QCheckBox("Autocomplete")
        autocomplete_toggle.setCheckable(True)
        autocomplete_toggle.setChecked(True)  # Enabled by default
        autocomplete_toggle.toggled.connect(self.toggle_autocomplete)
        self.addWidget(autocomplete_toggle)

        open_web_help = QPushButton("Online Help")
        open_web_help.clicked.connect(lambda x: cmds.help(doc=True))
        self.addWidget(open_web_help)

    @Slot(bool)
    def show_help(self, state: bool) -> None:
        """Toggle the help panel visibility.

        Parameters
        ----------
        state : bool
            True to show, False to hide.
        """
        self.help_toggled.emit(state)

    @Slot(bool)
    def show_lint(self, state: bool) -> None:
        """Toggle the lint panel visibility.

        Parameters
        ----------
        state : bool
            True to show, False to hide.
        """
        self.lint_toggled.emit(state)

    @Slot(bool)
    def toggle_autocomplete(self, state: bool) -> None:
        """Toggle autocomplete popup visibility.

        Parameters
        ----------
        state : bool
            True to show popup, False to hide.
        """
        self.autocomplete_toggled.emit(state)

    @Slot(int)
    def update_output_level(self, index: int) -> None:
        """Update the Maya command echo level.

        Parameters
        ----------
        index : int
            0 for Echo All, 1 for Normal.
        """
        cmds.commandEcho(state=index)

    def clipboard_copy(self) -> None:
        """Copy the output window content to the clipboard."""
        clipboard = QApplication.clipboard()
        clipboard.clear(mode=clipboard.Clipboard)
        text = self._output_window.toPlainText()
        clipboard.setText(text, mode=clipboard.Clipboard)

    def save_to_file(self) -> None:
        """Save the output window content to a text file."""
        file_name, _ = QFileDialog.getSaveFileName(
            self, "Save Output Text", "untitled.txt", "Text (*.txt)"
        )
        if file_name:
            with open(file_name, "w") as output_file:
                output_file.write(self._output_window.toPlainText())
