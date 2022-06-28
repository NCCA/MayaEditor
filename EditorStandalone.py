#!mayapy
import os
import sys
from contextlib import redirect_stdout

sys.path.insert(0, os.getcwd() + "/plug-ins/")

import importlib.util
import io

import maya.standalone
from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtUiTools import *
from PySide2.QtWidgets import *


class OutputWrapper(QObject):
    output_write = Signal(object, object)

    def __init__(self, parent, stdout=True):
        super().__init__(parent)
        if stdout:
            self._stream = sys.stdout
            sys.stdout = self
        else:
            self._stream = sys.stderr
            sys.stderr = self
        self._stdout = stdout

    def write(self, text):
        self.output_write.emit(text, self._stdout)


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__()
        stdout = OutputWrapper(self, True)
        stdout.output_write.connect(self.write_output)
        stderr = OutputWrapper(self, False)
        stderr.output_write.connect(self.write_output)
        self.editor = MayaEditorCore.EditorDialog(parent=self)

        layout = QHBoxLayout()
        widget = QWidget()
        widget.setLayout(layout)
        layout.addChildWidget(self.editor)
        self.setCentralWidget(widget)
        self.show()

    def write_output(self, text, stdout):
        self.editor.output_window.append_html(text)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key_Escape:
            QApplication.exit(1)

    def resizeEvent(self, event: QResizeEvent) -> None:
        self.editor.resize(event.size())
        return super().resizeEvent(event)


if __name__ == "__main__":

    QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
    app = QApplication(sys.argv)
    # This has to be done before generating the window but after init of Qt
    maya.standalone.initialize(name="python")

    # I know all imports should be at the top but this needs to be done after
    # Maya is initialize else you just get stubs that don't work.
    import maya.cmds as cmds
    import maya.OpenMayaUI as omui
    from shiboken2 import wrapInstance  # type: ignore

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
    maya.standalone.uninitialize()
