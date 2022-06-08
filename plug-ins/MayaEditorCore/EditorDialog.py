"""Editor Dialog Class for the NCCA Maya Editor.

This is the core Dialog class where all other elements are created and controlled. This can work stand alone as well as part of a plugin.
"""
import os
import socket
import sys
from pathlib import Path
from typing import Any

import maya.api.OpenMaya as OpenMaya
import maya.api.OpenMayaUI as OpenMayaUI
import maya.cmds as cmds
import maya.OpenMayaMPx as OpenMayaMPx
import maya.OpenMayaUI as omui
from maya import utils
from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtUiTools import *
from PySide2.QtWidgets import *

# Note this is from Maya not pyside so type hints not generated
from shiboken2 import wrapInstance  # type: ignore

from .CustomUILoader import UiLoader
from .EditorToolBar import EditorToolBar
from .Highlighter import Highlighter
from .PlainTextEdit import PlainTextEdit
from .Workspace import Workspace


def get_main_window() -> Any:
    """Return the maya main window for parenting.

    Grab the maya main window
    Returns : QWidget of the MayaMainWindow
    """
    window = omui.MQtUtil.mainWindow()
    return wrapInstance(int(window), QWidget)


class EditorDialog(QDialog):
    """Editor Dialog window main class.

    Inherits from QDialog and loads the ui from files.
    """

    def __init__(self, parent=get_main_window()):
        """Construct the class.

        Parameters :
        parent (QWidget) : the Maya parent window
        """
        super().__init__(parent)
        # This should work but crashes Maya2023 go figure!
        # self.callback_id = OpenMaya.MCommandMessage.addCommandOutputFilterCallback( self.message_callback  )
        self.settings = QSettings("NCCA", "NCCA_Maya_Editor")
        self.root_path = cmds.moduleInfo(path=True, moduleName="MayaEditor")
        UiLoader().loadUi(self.root_path + "/plug-ins/ui/form.ui", self)

        # This should make the window stay on top
        self.setWindowFlags(Qt.Tool)
        self.create_tool_bar()
        self.create_menu_bar()
        # connect tab close event
        self.editor_tab.tabCloseRequested.connect(self.tab_close_requested)

        self.open_files.setHeaderHidden(True)
        self.workspace = Workspace()
        self.load_settings()
        self.show()

    def load_settings(self) -> None:
        """Load in the setting from QSettings for the editor."""
        self.load_workspace_to_editor(self.settings.value("workspace"))
        splitter_settings = self.settings.value("splitter")
        self.editor_splitter.restoreState(splitter_settings)  # type: ignore

        if sz := self.settings.value("size"):
            self.resize(sz)

    def message_callback(self, message: str) -> None:
        """Use to put maya output to the output window.

        At present this is not working as using callbacks crash maya
        """
        self.output_window.append(message.strip())  # type: ignore

    def closeEvent(self, event: QCloseEvent) -> None:
        """Event called when the Dialog closeEvent is  triggered.

        We ensure that the setting are saved to the default settings.
        Parameters :
        event (QCloseEvent) : event passed in to close
        """
        # OpenMaya.MMessage.removeCallback(self.callback_id)
        print("Closing Dialog")
        self.settings.setValue("splitter", self.editor_splitter.saveState())  # type: ignore
        self.settings.setValue("size", self.size())
        super(EditorDialog, self).closeEvent(event)

    def create_menu_bar(self) -> None:
        """Create the menubar for the editor."""
        self.menu_bar = QMenuBar()
        file_menu = QMenu("&File")
        self.menu_bar.addMenu(file_menu)
        open_action = QAction("&Open", self)
        open_action.triggered.connect(self.open_file)  # type: ignore
        file_menu.addAction(open_action)

        new_action = QAction("&New", self)
        new_action.triggered.connect(self.new_file)  # type: ignore
        file_menu.addAction(new_action)

        workspace_menu = QMenu("&Workspace")
        new_workspace = QAction("New Workspace", self)
        new_workspace.triggered.connect(self.new_workspace)  # type: ignore
        workspace_menu.addAction(new_workspace)
        # open workspace
        open_workspace = QAction("Open Workspace", self)
        open_workspace.triggered.connect(self.open_workspace)  # type: ignore
        workspace_menu.addAction(open_workspace)
        # save workspace
        save_workspace = QAction("Save Workspace", self)
        save_workspace.triggered.connect(self.save_workspace)  # type: ignore
        workspace_menu.addAction(save_workspace)
        # close workspace
        close_workspace = QAction("Close Workspace", self)
        close_workspace.triggered.connect(self.close_workspace)  # type: ignore
        workspace_menu.addAction(close_workspace)

        self.menu_bar.addMenu(workspace_menu)

        self.main_grid_layout.setMenuBar(self.menu_bar)  # type: ignore

    def open_file(self) -> None:
        """Open a new file and add to the tabs."""
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Select File to Open",
            "",
            ("Mel / Python (*.py *.mel)"),
        )
        if file_name is not None:

            with open(file_name, "r") as code_file:
                py_file = str(Path(file_name).name)
                editor = PlainTextEdit(code_file.read(), file_name)
                # editor.installEventFilter(self)
                tab_index = self.editor_tab.addTab(editor, py_file)  # type: ignore
                self.workspace.add_file(file_name)

    def new_file(self) -> None:
        """Create a new file tab."""
        editor = PlainTextEdit("", "untitled.py")
        self.editor_tab.insertTab(0, editor, "untitled.py")  # type: ignore

    def create_tool_bar(self) -> None:
        """Create the toolbar."""
        self.tool_bar = EditorToolBar(self)  # QToolBar(self)
        # Add to main dialog
        self.dock_widget.setWidget(self.tool_bar)  # type: ignore

    def tab_close_requested(self, index: int) -> None:
        """Slot called when a tab close is pressed.

        logic to see if we need to save or not is included here for ease.
        Parameters :
        index (int) : index of the tab where the close was requested.
        """
        print(f"tab close {index} ")
        tab: QTabWidget = self.editor_tab  # type: ignore
        editor: PlainTextEdit = tab.widget(index)  # type: ignore

        if editor.needs_saving is not True:
            tab.removeTab(index)
        # need to check if we want to save or discard
        else:
            msg_box = QMessageBox()
            msg_box.setWindowTitle("Warning!")
            msg_box.setText("File has been Modified")
            msg_box.setInformativeText("Do you want to save your changes?")
            msg_box.setStandardButtons(
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
            )
            msg_box.setDefaultButton(QMessageBox.Save)
            ret = msg_box.exec_()
            if ret == QMessageBox.Save:
                saved = editor.save_file()
                if saved:
                    tab.removeTab(index)
                else:
                    return

            elif ret == QMessageBox.Discard:
                tab.removeTab(index)
            elif ret == QMessageBox.Cancel:
                pass

    def new_workspace(self) -> None:
        """Create a new workspace.

        Logic checks to ensure the previous workspace is saved or not.
        """
        if self.workspace.is_saved is not True:
            self.save_workspace()
        else:
            tab = self.editor_tab  # type: ignore
            for t in range(0, tab.count() + 1):
                tab.removeTab(t)
            self.workspace.new()

    def save_workspace(self) -> None:
        """Save current workspace."""
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Select Workspace Name",
            "untitled.workspace",
            ("Workspace (*.workspace)"),
        )
        if file_name is not None:
            self.workspace.save(file_name)

    def close_workspace(self) -> None:
        """Close the current workspace."""
        pass

    def open_workspace(self) -> None:
        """Open a new workspace.

        There is logic to ensure that the current one is saved or not.
        """
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Select Workspace Name",
            "untitled.workspace",
            ("Workspace (*.workspace)"),
        )
        if file_name is not None:
            self.settings.setValue("workspace", file_name)
            self.load_workspace_to_editor(file_name)

    def load_workspace_to_editor(self, file_name: str) -> None:
        """Load in the actual workspace data to the editor tab.

        This is called to load and create each new PlainTextEdit into the tabs
        Parameters :
        file_name (str) : full path to the editor file to load
        """
        self.workspace.load(file_name)
        for code_file_name in self.workspace.files:
            with open(code_file_name, "r") as code_file:
                py_file = str(Path(code_file_name).name)
                editor = PlainTextEdit(code_file.read(), file_name)
                tab_index = self.editor_tab.addTab(editor, py_file)  # type: ignore
                item = QTreeWidgetItem(self.open_files)  # type: ignore
                item.setText(0, py_file)
                self.open_files.addTopLevelItem(item)  # type: ignore
                self.tool_bar.add_to_active_file_list(py_file)

    @Slot()
    def tool_bar_run_clicked(self):
        """Slot used by the Toolbar run button."""
        self.editor_tab.currentWidget().execute_code()

    @Slot(int)
    def tool_bar_goto_changed(self, line: int):
        """Slot used by the Toolbar goto dial."""
        # Note we subtract 1 as the line is defaulting to the correct range
        self.editor_tab.currentWidget().goto_line(line - 1)

    @Slot()
    def tool_bar_run_project_clicked(self):
        """Slot called when run project clicked."""
        pass
        file_to_run = self.tool_bar.active_project_file.currentText()
        # first find the index of the active tab
        tab = self.editor_tab  # type: ignore
        index = 0
        for t in range(0, tab.count() + 1):
            if file_to_run == tab.tabText(t):
                index = t
                break
        self.editor_tab.widget(index).execute_code()
