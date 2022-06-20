#!mayapy
import os
import sys

sys.path.insert(0, os.getcwd() + "/plug-ins/")

import importlib.util

import maya.standalone
from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtUiTools import *
from PySide2.QtWidgets import *


class MainWindow(QMainWindow):
    def __init__(self, parent=None):

        super().__init__()
        MayaEditorCore.EditorDialog(parent=self)
     
if __name__ == "__main__":
    QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
    app = QApplication(sys.argv)
    maya.standalone.initialize(name="python")
    import maya.cmds as cmds

    # query the MayaEditor module file for location of source
    root_path = cmds.moduleInfo(path=True, moduleName="MayaEditor")
    # add this to our python path to we can access the modules
    sys.path.insert(0, root_path + "/plug-ins")
    import MayaEditorCore

    window = MainWindow()
    window.resize(1024, 720)
    window.show()
    app.exec_()
