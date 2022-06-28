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
        self.is_saved = True
        self.filename = "untitled.ma"
        layout = QHBoxLayout()
        widget = QWidget()
        widget.setLayout(layout)
        layout.addChildWidget(self.editor)
        self.setCentralWidget(widget)
        self.create_scene_toolbar()

        self.show()

    def create_scene_toolbar(self):
        self.toolbar = QToolBar(self)
        self.toolbar.setWindowTitle("Maya Scene Controls")
        self.toolbar.setFloatable(True)
        self.toolbar.setMovable(True)
        new_scene = QPushButton("New Scene")
        self.toolbar.addWidget(new_scene)
        new_scene.clicked.connect(self.new_maya_scene)

        save_scene = QPushButton("Save Scene")
        self.toolbar.addWidget(save_scene)
        save_scene.clicked.connect(self.save_maya_scene)

        save_scene_as = QPushButton("Save As")
        self.toolbar.addWidget(save_scene_as)
        label = QLabel("Scene Format")
        self.toolbar.addWidget(label)
        save_scene_as.clicked.connect(self.save_maya_scene_as)
        self.scene_format = QComboBox()
        self.scene_format.addItem(".ma")
        self.scene_format.addItem(".mb")
        self.toolbar.addWidget(self.scene_format)

        self.addToolBar(self.toolbar)

    def new_maya_scene(self):
        print("new maya scene")
        filename = self.get_file_name()
        if filename is not None:
            self.filename = filename
            cmds.file(f=True, new=True)
            cmds.file(rename=self.filename)
            self.save()
        else:
            msg_box = QMessageBox()
            msg_box.setWindowTitle("Warning!")
            msg_box.setText("Maya Scene Not Saved")
            msg_box.setInformativeText("Do you want to save your changes?")
            msg_box.setStandardButtons(
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
            )
            msg_box.setDefaultButton(QMessageBox.Save)
            ret = msg_box.exec_()

            if ret == QMessageBox.Save:
                self.save()
                return True
            else:
                return False

    def save_maya_scene(self):
        if self.filename == "untitled.ma":
            filename = self.get_file_name()
            cmds.file(rename=self.filename)
        if self.is_saved:
            self.save()

    def save_maya_scene_as(self):
        if self.filename == "untitled.ma":
            filename = self.get_file_name()
            cmds.file(rename=self.filename)
            self.save()

    def get_file_name(self) -> str:

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Select Filename Name",
            "untitled.ma",
            ("Maya Scenes (*.ma,*.mb)"),
        )
        return filename

    def write_output(self, text, stdout):
        self.editor.output_window.append_html(text)

    def save(self) -> None:
        if self.scene_format.currentIndex() == 0:
            cmds.file(f=True, type="mayaAscii", save=True)
        else:
            cmds.file(f=True, type="mayaBinary", save=True)
        self.is_saved = True

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
