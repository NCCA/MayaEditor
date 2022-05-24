import os
import socket
import sys
from pathlib import Path

import maya.api.OpenMaya as OpenMaya
import maya.api.OpenMayaUI as OpenMayaUI
import maya.cmds as cmds
import maya.OpenMayaMPx as OpenMayaMPx
import maya.OpenMayaUI as omui
from maya import utils
from PySide2.QtCore import QEvent, QFile, Qt
from PySide2.QtGui import QColor, QFont
from PySide2.QtUiTools import QUiLoader
from PySide2.QtWidgets import QAction, QFileDialog, QMenu, QMenuBar, QWidget
from shiboken2 import wrapInstance

from .Highlighter import Highlighter
from .PlainTextEdit import PlainTextEdit


def get_main_window():
    """this returns the maya main window for parenting"""
    window = omui.MQtUtil.mainWindow()
    return wrapInstance(int(window), QWidget)


class EditorDialog(QWidget):
    def __init__(self, parent=get_main_window()):
        """init the class and setup dialog"""
        super().__init__(parent)
        # This should work but crashes Maya2023 go figure!
        # self.callback_id = OpenMaya.MCommandMessage.addCommandOutputFilterCallback(self.message_callback)

        self.root_path = cmds.moduleInfo(path=True, moduleName="MayaEditor")
        loader = QUiLoader()
        file = QFile(self.root_path + "/plug-ins/ui/form.ui")
        file.open(QFile.ReadOnly)
        self.ui = loader.load(file, parentWidget=self)
        file.close()
        # This should make the window stay on top
        self.ui.setWindowFlags(Qt.Tool)
        self.create_menu_bar()
        self.ui.show()
        self.installEventFilter(self)

    def message_callback(self, message):
        self.ui.output_window.append(message.strip())
        pass

    def closeEvent(self, event):
        # OpenMaya.MMessage.removeCallback(self.callback_id)
        pass

    def create_menu_bar(self):
        self.menu_bar = QMenuBar()
        file_menu = QMenu("&File")
        self.menu_bar.addMenu(file_menu)

        open_action = QAction("&Open", self)
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)

        new_action = QAction("&New", self)
        new_action.triggered.connect(self.new_file)
        file_menu.addAction(new_action)

        self.ui.main_grid_layout.setMenuBar(self.menu_bar)

    def open_file(self):
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
                self.ui.editor_tab.addTab(editor, py_file)

    def new_file(self):
        editor = PlainTextEdit("", "untitled.py")
        # editor.installEventFilter(self)
        self.ui.editor_tab.insertTab(0, editor, "untitled.py")
