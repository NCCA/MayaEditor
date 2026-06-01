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
"""Editor toolbar with run, goto and quick-load controls."""

from pathlib import Path
from typing import Any, Optional

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QCompleter,
    QFileSystemModel,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QToolBar,
)


class EditorToolBar(QToolBar):
    """Main editor toolbar with run, project-run, goto, and quick-load widgets."""

    rename_workspace_requested = Signal()
    file_open_requested = Signal(str)

    def __init__(self, parent: Optional[Any] = None) -> None:
        """Construct the toolbar and connect parent slots.

        Parameters
        ----------
        parent : QDialog or None
            The parent EditorDialog instance.
        """
        super().__init__(parent)
        assert parent is not None
        self.setFloatable(True)
        self.setMovable(True)

        run_project = QPushButton("Run Project")
        run_project.setDefault(False)
        run_project.clicked.connect(parent.tool_bar_run_project_clicked)
        self.addWidget(run_project)

        self.active_project_file = QComboBox()
        self.addWidget(self.active_project_file)
        self.addSeparator()

        run_button = QPushButton("Run Current")
        run_button.clicked.connect(parent.tool_bar_run_clicked)
        self.addWidget(run_button)
        self.addSeparator()

        label = QLabel("Goto :")
        self.addWidget(label)
        goto_number = QSpinBox()
        goto_number.setMinimum(1)
        goto_number.setMaximum(99999)
        goto_number.valueChanged.connect(parent.tool_bar_goto_changed)
        self.addWidget(goto_number)
        self.addSeparator()

        label = QLabel("Quick Load")
        self.addWidget(label)
        self.quick_load_edit = QLineEdit()
        completer = QCompleter()
        file_system_model = QFileSystemModel(completer)
        root_path = str(Path.home().expanduser())
        file_system_model.setRootPath(root_path)
        filters = ["*.txt", "*.py", "*.mel", "*.md"]
        file_system_model.setNameFilters(filters)
        completer.setModel(file_system_model)
        self.quick_load_edit.setCompleter(completer)
        self.quick_load_edit.setText(root_path)
        self.quick_load_edit.returnPressed.connect(self.quick_load)
        self.quick_load_edit.inputRejected.connect(
            lambda x: self.quick_load_edit.clear()
        )
        self.addWidget(self.quick_load_edit)

        self.addSeparator()
        self.workspace_label = QLabel("")
        self.workspace_label.setToolTip("Double-click to rename workspace")
        self.workspace_label.setStyleSheet(
            "QLabel { font-weight: bold; padding: 2px 8px; }"
        )
        self.workspace_label.installEventFilter(self)
        self.addWidget(self.workspace_label)

    def eventFilter(self, obj: object, event: QEvent) -> bool:
        """Handle double-click on the workspace label to trigger rename."""
        if (
            obj is self.workspace_label
            and event.type() == QEvent.Type.MouseButtonDblClick
        ):
            self.rename_workspace_requested.emit()
            return True
        return bool(super().eventFilter(obj, event))

    def update_workspace_label(self, name: str) -> None:
        """Update the workspace label text.

        Parameters
        ----------
        name : str
            The new workspace name.
        """
        self.workspace_label.setText(name)

    def quick_load(self) -> None:
        """Load the file entered in the quick-load field."""
        filename = self.quick_load_edit.text()
        path = Path(filename)
        parent = self.parent()
        if path.is_file() and parent and hasattr(parent, "workspace"):
            if filename not in parent.workspace.files:
                self.file_open_requested.emit(filename)

    def add_to_active_file_list(self, filename: str) -> None:
        """Add a filename to the run-project combo box.

        Parameters
        ----------
        filename : str
            The display name to add.
        """
        self.active_project_file.addItem(filename)

    def remove_from_active_file_list(self, filename: str) -> None:
        """Remove a filename from the run-project combo box.

        Parameters
        ----------
        filename : str
            The display name to remove.
        """
        index = self.active_project_file.findText(filename, Qt.MatchContains)
        self.active_project_file.removeItem(index)
