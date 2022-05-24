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
        # Python 3 does inheritance differently to 2 so support both
        # as Maya 2020 is still Python 2
        if sys.version_info.major == 3:
            super().__init__(parent)
        # python 2
        else:
            super(EditorDialog, self).__init__(parent)
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

    def send_to_maya(self):
        value = utils.executeInMainThreadWithResult()
        # value = utils.executeDeferred(self.ui.python_editor.toPlainText())

    def create_menu_bar(self):

        self.menu_bar = QMenuBar()
        file_menu = QMenu("&File")
        self.menu_bar.addMenu(file_menu)

        open_action = QAction("&Open", self)
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)

        # open_menu = QMenu("&Open", file_menu)
        # open_action = QAction("&Open")
        # open_action.triggered.connect(self.open_file)
        # file_menu.addAction(open_action)
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
                editor = PlainTextEdit(code_file.read())
                # editor.installEventFilter(self)
                self.ui.editor_tab.addTab(editor, py_file)

    # def eventFilter(self, obj, event):
    #     if isinstance(obj, PlainTextEdit):
    #         if event.type() == QEvent.KeyPress:
    #             print(f"keypress {event.modifiers()=}")
    #             if (
    #                 event.key() == Qt.Key_Enter
    #                 and event.modifiers() == Qt.ControlModifier
    #             ):
    #                 print("ALT + ENTER")
    #                 return False
    #             else:
    #                 return True
    #     else:
    #         return True
