from pathlib import Path

from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *

"""
This class contains the different models used by the sidebar, this allows us to switch the display
from Active Files (Workspace mode), file system, and class / function navigator
"""


class SideBarModels(QObject):
    """
    SideBarModel contains different Qt Item models for the sidebar QTreeView
    Slots :
    append_to_workspace add file to workspace mode
    remove_from_workspace removes short filename from model
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.workspace = QStandardItemModel()
        self.active_model = self.workspace
        self.file_system_model = QFileSystemModel()
        self.file_system_model.setRootPath(Path.cwd().name)
        filters = ["*.txt", "*.py", "*.mel", "*.md"]
        self.file_system_model.setNameFilters(filters)

    def append_to_workspace(self, name: str) -> None:
        """
        Add a short name to our workspace model, this name will be used by the main editor when removing
        Parameters :
        name(str) : the short name to display in the model
        """
        item = QStandardItem()
        item.setText(name)
        self.workspace.insertRow(0, item)

    def remove_from_workspace(self, name: str) -> None:
        items = self.workspace.findItems(name, Qt.MatchContains)
        for i in items:
            self.workspace.removeRow(i.row())

    @Slot(int)
    def change_active_model(self, index):
        # I know I could use a list of a dictionary to store this but I think this makes the
        # rest of the code much neater and we will only have 3-4 types to content with
        # Guess this is the C++ programmer in me coming out.
        if index == 0:
            self.active_model = self.workspace
        elif index == 1:
            self.active_mode = self.file_system_model
