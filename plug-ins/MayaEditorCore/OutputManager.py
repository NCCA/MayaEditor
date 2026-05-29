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
"""Output panel manager for the NCCA Maya Editor.

Owns the output window, help panel, and lint panel widgets.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import maya.cmds as cmds

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QCompleter,
    QFrame,
    QGridLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
)

from .TextEdit import TextEdit

if TYPE_CHECKING:
    from .EditorDialog import EditorDialogCore


class OutputManager:
    """Manages the output window, help panel, and lint panel.

    Parameters
    ----------
    dialog : EditorDialogCore
        The parent editor dialog that owns this manager.
    """

    def __init__(self, dialog: EditorDialogCore) -> None:
        self._dialog = dialog

    def create(self) -> None:
        """Create the output window, help panel, and lint panel widgets.

        Widgets are added to ``self._dialog.ui.output_window_layout``.
        """
        self.output_window = TextEdit(
            parent=self._dialog, read_only=True, show_line_numbers=False
        )
        self._dialog.update_fonts.connect(self.output_window.set_editor_fonts)
        self._dialog.update_fonts.emit(self._dialog.font)

        self.output_splitter = QSplitter()
        self.output_splitter.addWidget(self.output_window)

        self.help_frame = QFrame()
        grid_layout = QGridLayout()
        grid_layout.setObjectName("grid_layout")
        self.help_frame.setLayout(grid_layout)

        self.help_items = QComboBox()
        self.help_items.setObjectName("help_items")
        grid_layout.addWidget(self.help_items, 0, 2, 1, 1)

        self._label = QLabel("Help")
        grid_layout.addWidget(self._label, 0, 0, 1, 1)

        self.search_help = QLineEdit(self.help_frame)
        self.search_help.setObjectName("search_help")
        self.search_help.setToolTip("type to search maya.cmds help")
        grid_layout.addWidget(self.search_help, 0, 1, 1, 1)

        self.help_output_window = TextEdit(
            parent=self.help_frame, read_only=True, show_line_numbers=False
        )
        grid_layout.addWidget(self.help_output_window, 1, 0, 3, 3)

        self.output_splitter.addWidget(self.help_frame)
        self._create_lint_panel()
        self._dialog.ui.output_window_layout.addWidget(self.output_splitter)

        self.maya_cmds: list[Any] = cmds.help("[a-z]*", list=True, lng="Python")
        for c in self.maya_cmds:
            self.help_items.addItem(c)
        self.help_items.currentIndexChanged.connect(self.run_maya_help)
        self.search_help.returnPressed.connect(self.search_maya_help)

        completer = QCompleter(self.maya_cmds)
        self.search_help.setCompleter(completer)

    def _create_lint_panel(self) -> None:
        """Create the lint results panel and add it to the output splitter.

        The panel is hidden by default and shown via the *Show Lint*
        checkbox in :class:`OutputToolBar`.
        """
        self.lint_panel = QTableWidget(0, 4)
        self.lint_panel.setHorizontalHeaderLabels(["Sev", "Line", "Code", "Message"])
        self.lint_panel.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.Stretch
        )
        self.lint_panel.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self.lint_panel.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self.lint_panel.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )
        self.lint_panel.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.lint_panel.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.lint_panel.verticalHeader().setVisible(False)
        self.lint_panel.setAlternatingRowColors(True)
        self.lint_panel.cellDoubleClicked.connect(self._lint_row_activated)
        self.lint_panel.setVisible(False)
        self.output_splitter.addWidget(self.lint_panel)

    def update_lint_panel(self, diagnostics: list) -> None:
        """Populate the lint panel with *diagnostics*.

        Parameters
        ----------
        diagnostics : list[Diagnostic]
            Diagnostics from the active Python editor.
        """
        self.lint_panel.setRowCount(0)
        for diag in diagnostics:
            row = self.lint_panel.rowCount()
            self.lint_panel.insertRow(row)

            sev_item = QTableWidgetItem(diag.severity[0].upper())  # "E" or "W"
            sev_item.setForeground(
                QColor(255, 80, 80) if diag.severity == "error" else QColor(255, 200, 0)
            )
            self.lint_panel.setItem(row, 0, sev_item)

            line_item = QTableWidgetItem(f"{diag.row}:{diag.col}")
            line_item.setData(Qt.UserRole, diag.row)
            self.lint_panel.setItem(row, 1, line_item)

            self.lint_panel.setItem(row, 2, QTableWidgetItem(diag.code))
            self.lint_panel.setItem(row, 3, QTableWidgetItem(diag.message))

    def _lint_row_activated(self, row: int, _col: int) -> None:
        """Jump the active editor to the line referenced by the clicked row.

        Parameters
        ----------
        row : int
            The row index in the lint panel.
        _col : int
            Unused column index.
        """
        line_item = self.lint_panel.item(row, 1)
        if line_item is None:
            return
        line_number = line_item.data(Qt.UserRole)
        if line_number is None:
            return
        editor = self._dialog.ui.editor_tab.currentWidget()
        if editor and hasattr(editor, "goto_line"):
            editor.goto_line(int(line_number) - 1)

    def run_maya_help(self, index: int) -> None:
        """Display help for the selected Maya command.

        Parameters
        ----------
        index : int
            Index of the selected command in the combo box.
        """
        command = self.help_items.currentText()
        output = cmds.help(command, language="python")
        output = output.strip("\n")
        self.help_output_window.clear()
        self.help_output_window.appendPlainText(output)

    def search_maya_help(self) -> None:
        """Display help for the Maya command entered in the search field."""
        help_text = self.search_help.text()
        if help_text in self.maya_cmds:
            output = cmds.help(help_text, language="python")
            output = output.strip("\n")
            self.help_output_window.clear()
            self.help_output_window.appendPlainText(output)
