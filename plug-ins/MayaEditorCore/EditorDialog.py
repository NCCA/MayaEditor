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
from .Highlighter import Highlighter
from .PlainTextEdit import PlainTextEdit
from .Workspace import Workspace


def get_main_window() -> Any:
    """this returns the maya main window for parenting"""
    window = omui.MQtUtil.mainWindow()
    return wrapInstance(int(window), QWidget)


class EditorDialog(QDialog):
    open_files: QTreeWidget
    editor_splitter: QSplitter
    output_window: PlainTextEdit
    menu_bar: QMenuBar
    main_grid_layout: QGridLayout
    editor_tab: QTabWidget
    dock_widget: QDockWidget

    def __init__(self, parent=get_main_window()):
        """init the class and setup dialog"""
        super().__init__(parent)
        # This should work but crashes Maya2023 go figure!
        # self.callback_id = OpenMaya.MCommandMessage.addCommandOutputFilterCallback( self.message_callback  )
        self.settings = QSettings("NCCA", "NCCA_Maya_Editor")
        self.root_path = cmds.moduleInfo(path=True, moduleName="MayaEditor")
        # loader = QUiLoader()
        # file = QFile(self.root_path + "/plug-ins/ui/form.ui")
        # file.open(QFile.ReadOnly)
        # self.ui = loader.load(file, parentWidget=self)
        # file.close()
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
        self.load_workspace_to_editor(self.settings.value("workspace"))
        splitter_settings = self.settings.value("splitter")
        self.editor_splitter.restoreState(splitter_settings)

        if sz := self.settings.value("size"):
            self.resize(sz)

    def message_callback(self, message: str) -> None:
        self.output_window.append(message.strip())  # type: ignore

    def closeEvent(self, event: QCloseEvent) -> None:
        # OpenMaya.MMessage.removeCallback(self.callback_id)
        print("Closing Dialog")
        self.settings.setValue("splitter", self.editor_splitter.saveState())
        self.settings.setValue("size", self.size())
        super(EditorDialog, self).closeEvent(event)

    def create_menu_bar(self) -> None:
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

        self.main_grid_layout.setMenuBar(self.menu_bar)

    def open_file(self) -> None:
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
                tab_index = self.editor_tab.addTab(editor, py_file)
                self.workspace.add_file(file_name)

    def new_file(self) -> None:
        editor = PlainTextEdit("", "untitled.py")
        self.editor_tab.insertTab(0, editor, "untitled.py")

    def create_tool_bar(self) -> None:
        self.tool_bar = QToolBar(self)
        self.tool_bar.setFloatable(True)
        self.tool_bar.setMovable(True)
        run_button = QPushButton("Run")
        self.tool_bar.addWidget(run_button)
        # Add to main dialog
        self.dock_widget.setWidget(self.tool_bar)

    def tab_close_requested(self, index: int) -> None:
        """slot called when a tab close is pressed, logic to see if we need to
        save or not is included"""
        print(f"tab close {index} ")
        tab: QTabWidget = self.editor_tab
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
        # first create new workspace then clear current one
        if self.workspace.is_saved is not True:
            self.save_workspace()
        else:
            tab = self.editor_tab
            for t in range(0, tab.count() + 1):
                tab.removeTab(t)
            self.workspace.new()

    def save_workspace(self) -> None:
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Select Workspace Name",
            "untitled.workspace",
            ("Workspace (*.workspace)"),
        )
        if file_name is not None:
            self.workspace.save(file_name)

    def close_workspace(self) -> None:
        pass

    def open_workspace(self) -> None:
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
        self.workspace.load(file_name)
        for code_file_name in self.workspace.files:
            with open(code_file_name, "r") as code_file:
                py_file = str(Path(code_file_name).name)
                editor = PlainTextEdit(code_file.read(), file_name)
                tab_index = self.editor_tab.addTab(editor, py_file)
                item = QTreeWidgetItem(self.open_files)
                item.setText(0, py_file)
                self.open_files.addTopLevelItem(item)
