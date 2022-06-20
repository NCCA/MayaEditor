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


class MainWindow(QDialog):
    def __init__(self, parent=None):

        super().__init__()
        MayaEditorCore.EditorDialog(parent=self)
     
if __name__ == "__main__":
    QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
    app = QApplication(sys.argv)
    # This has to be done before generating the window but after init of Qt
    maya.standalone.initialize(name="python")
    # I know all imports should be at the top but this needs to be done after 
    # Maya is initialize else you just get stubs that don't work.
    import maya.cmds as cmds

    # query the MayaEditor module file for location of source
    root_path = cmds.moduleInfo(path=True, moduleName="MayaEditor")
    # add this to our python path to we can access the modules
    sys.path.insert(0, root_path + "/plug-ins")
    # Again a late import but relies on Maya so needs to be done here.
    import MayaEditorCore

    # Now construct our main window. This will stand in for the Maya Main window
    window = MainWindow()
    window.resize(1024, 720)
    window.show()
    app.exec_()
