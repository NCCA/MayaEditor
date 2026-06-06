"""Sidebar model classes for workspace, file-system and code-outline views."""

import os as os_module
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QObject, Slot
from PySide6.QtGui import QIcon, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QFileSystemModel

from .MelTextEdit import MelTextEdit
from .PythonTextEdit import PythonTextEdit, code_model_data


class SideBarModels(QObject):
    """Manages the three sidebar models: workspace, file-system and code outline.

    Slots
    -----
    append_to_workspace(name, icon)
        Add a file to the workspace model.
    remove_from_workspace(name)
        Remove a filename from the workspace model.
    generate_code_model()
        Rebuild the code-outline model for the active editor.
    code_model_needs_update()
        Slot connected to editor tab changes.
    change_active_model(index)
        Switch the active sidebar model.
    """

    def __init__(
        self, parent: Any = None, root_path: str = ".", editor_tab: Any = None
    ) -> None:
        """Initialise the three models and load icons.

        Parameters
        ----------
        parent : QObject or None
            The parent QObject for Qt ownership.
        root_path : str
            Filesystem root path used to locate icon files.
        editor_tab : QTabWidget or None
            The editor tab widget used by generate_code_model.
        """
        super().__init__(parent)
        self._editor_tab = editor_tab
        self.workspace: QStandardItemModel = QStandardItemModel()
        self.active_model: QStandardItemModel = self.workspace
        self.file_system_model: QFileSystemModel = QFileSystemModel()
        self.file_system_model.setRootPath(str(Path.cwd().name))
        filters = ["*.txt", "*.py", "*.mel", "*.md"]
        self.file_system_model.setNameFilters(filters)
        self.code_system_model: QStandardItemModel = QStandardItemModel()

        sep = "\\" if os_module.name == "nt" else "/"
        self.class_icon = QIcon(f"{root_path}{sep}plug-ins{sep}icons{sep}class.png")
        self.method_icon = QIcon(f"{root_path}{sep}plug-ins{sep}icons{sep}method.png")
        self.function_icon = QIcon(
            f"{root_path}{sep}plug-ins{sep}icons{sep}function.png"
        )
        self.proc_icon = QIcon(f"{root_path}{sep}plug-ins{sep}icons{sep}proc.png")
        self.global_icon = QIcon(f"{root_path}{sep}plug-ins{sep}icons{sep}global.png")

    def append_to_workspace(self, name: str, icon: QIcon) -> None:
        """Add a short filename to the workspace model.

        Parameters
        ----------
        name : str
            The display name for the entry.
        icon : QIcon
            The icon to display alongside the name.
        """
        item = QStandardItem()
        item.setText(name)
        item.setIcon(icon)
        self.workspace.insertRow(0, item)

    def remove_from_workspace(self, name: str) -> None:
        """Remove entries matching *name* from the workspace model.

        Parameters
        ----------
        name : str
            The display name to match (partial match).
        """
        items = self.workspace.findItems(name, Qt.MatchContains)
        for i in items:
            self.workspace.removeRow(i.row())

    def create_mel_model(self, widget: MelTextEdit) -> None:
        """Populate the code model from a MEL editor's code_model data.

        Parameters
        ----------
        widget : MelTextEdit
            The MEL editor widget.
        """
        for proc in widget.code_model:
            item = QStandardItem()
            icon = self.proc_icon
            if proc.scope == "global":
                icon = self.global_icon
            item.setText(f"{proc.function_name}")
            item.setData(int(proc.line_number))
            item.setIcon(icon)
            self.code_system_model.appendRow(item)

    def create_python_model(self, widget: PythonTextEdit) -> None:
        """Populate the code model from a Python editor's code_model data.

        Parameters
        ----------
        widget : PythonTextEdit
            The Python editor widget.
        """
        for entry_data in widget.code_model:
            entry = QStandardItem()
            if isinstance(entry_data, code_model_data):
                entry.setText(f"{entry_data.name}")
                entry.setData(entry_data.line_number)
                entry.setIcon(self.function_icon)
                self.code_system_model.appendRow(entry)
            elif isinstance(entry_data, dict):
                class_info = list(entry_data.keys())[0]
                entry.setText(f"{class_info.name}")
                entry.setIcon(self.class_icon)
                entry.setData(class_info.line_number)
                methods = list(entry_data.values())
                for m in methods[0]:
                    method = QStandardItem()
                    method.setText(f"{m.name}")
                    method.setData(m.line_number)
                    method.setIcon(self.method_icon)
                    entry.appendRow(method)
                self.code_system_model.appendRow(entry)

    @Slot()
    def generate_code_model(self, text: str = "") -> None:
        """Rebuild the code-outline model for the currently active editor tab.

        Parameters
        ----------
        text : str
            Unused, present for slot compatibility.
        """
        self.code_system_model.clear()
        tab = self._editor_tab
        if tab is None:
            return
        widget = tab.widget(tab.currentIndex())
        if isinstance(widget, MelTextEdit):
            self.create_mel_model(widget)
        elif isinstance(widget, PythonTextEdit):
            self.create_python_model(widget)

    @Slot()
    def code_model_needs_update(self) -> None:
        """Update the code model if it is currently the active sidebar view."""
        if self.active_model == self.code_system_model:
            self.generate_code_model()

    @Slot(int)
    def change_active_model(self, index: int) -> None:
        """Switch the active sidebar model.

        Parameters
        ----------
        index : int
            0 = workspace, 1 = file-system, 2 = code outline.
        """
        if index == 0:
            self.active_model = self.workspace
        elif index == 1:
            self.active_model = self.file_system_model
        elif index == 2:
            self.active_model = self.code_system_model
