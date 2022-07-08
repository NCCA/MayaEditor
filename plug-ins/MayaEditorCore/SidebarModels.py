from pathlib import Path

from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *

from .MelTextEdit import MelTextEdit
from .PythonTextEdit import PythonTextEdit

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
        self.parent = parent
        self.workspace = QStandardItemModel()
        self.active_model = self.workspace
        self.file_system_model = QFileSystemModel()
        self.file_system_model.setRootPath(Path.cwd().name)
        filters = ["*.txt", "*.py", "*.mel", "*.md"]
        self.file_system_model.setNameFilters(filters)
        self.code_system_model = QStandardItemModel()

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

    def create_mel_model(self, widget):
        for proc in widget.code_model:
            item = QStandardItem()
            item.setText(proc[2])
            item.setData(int(proc[1]))
            self.code_system_model.appendRow(item)

    @Slot()
    def generate_code_model(self, text=""):
        self.code_system_model.clear()
        tab = self.parent.ui.editor_tab
        widget = tab.widget(tab.currentIndex())
        if isinstance(widget, MelTextEdit):
            self.create_mel_model(widget)

        elif isinstance(widget, PythonTextEdit):
            print("have python editor")

    @Slot()
    def editor_tab_updated(self):
        if self.active_model == self.code_system_model:
            self.generate_code_model()

    @Slot(int)
    def change_active_model(self, index):
        # I know I could use a list of a dictionary to store this but I think this makes the
        # rest of the code much neater and we will only have 3-4 types to content with
        # Guess this is the C++ programmer in me coming out.
        if index == 0:
            self.active_model = self.workspace
        elif index == 1:
            self.active_model = self.file_system_model
        elif index == 2:
            self.active_model = self.code_system_model
