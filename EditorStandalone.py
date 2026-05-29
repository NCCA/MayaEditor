#!/Applications/Autodesk/maya2026/Maya.app/Contents/bin/mayapy
"""Standalone Maya editor launcher for use outside of Maya's GUI.

Requires ``maya.standalone.initialize()`` before importing ``maya.cmds``.
"""

import os
import sys
from typing import Optional

sys.path.insert(0, os.getcwd() + "/plug-ins/")


import maya.standalone
from PySide6.QtCore import QCoreApplication, QObject, Qt, Signal
from PySide6.QtGui import QKeyEvent, QResizeEvent
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QToolBar,
    QWidget,
)


class OutputWrapper(QObject):
    """Intercepts stdout/stderr and emits them as signals."""

    output_write = Signal(object, object)

    def __init__(self, parent: QObject, stdout: bool = True) -> None:
        """Wrap a stream and redirect it.

        Parameters
        ----------
        parent : QObject
            Parent object.
        stdout : bool
            True to wrap sys.stdout, False for sys.stderr.
        """
        super().__init__(parent)
        if stdout:
            self._stream = sys.stdout
            sys.stdout = self
        else:
            self._stream = sys.stderr
            sys.stderr = self
        self._stdout = stdout

    def write(self, text: str) -> None:
        """Emit the text via signal.

        Parameters
        ----------
        text : str
            The text to emit.
        """
        self.output_write.emit(text, self._stdout)

    def flush(self) -> None:
        """Flush the original stream."""
        if hasattr(self._stream, "flush"):
            self._stream.flush()

    def restore(self) -> None:
        """Restore the original stdout/stderr stream."""
        if self._stdout:
            sys.stdout = self._stream
        else:
            sys.stderr = self._stream


class MainWindow(QMainWindow):
    """Main window for the standalone Maya editor."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Construct the main window with editor and scene controls.

        Parameters
        ----------
        parent : QWidget or None
            Parent widget.
        """
        super().__init__()
        self._stdout_wrapper = OutputWrapper(self, True)
        self._stdout_wrapper.output_write.connect(self.write_output)
        self._stderr_wrapper = OutputWrapper(self, False)
        self._stderr_wrapper.output_write.connect(self.write_output)

        self.editor = MayaEditorCore.EditorDialogStandalone()
        self.is_saved: bool = True
        self.filename: str = "untitled.ma"

        layout = QHBoxLayout()
        widget = QWidget()
        widget.setLayout(layout)
        layout.addWidget(self.editor)
        self.setCentralWidget(widget)
        self.create_scene_toolbar()
        self.show()

    def create_scene_toolbar(self) -> None:
        """Create a toolbar with Maya scene controls (new, save, save-as)."""
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

    def new_maya_scene(self) -> bool:
        """Create a new Maya scene, prompting to save the current one.

        Returns
        -------
        bool
            True if the scene was created or discarded, False on cancel.
        """
        print("new maya scene")
        filename = self.get_file_name()
        if filename:
            self.filename = filename
            cmds.file(f=True, new=True)
            cmds.file(rename=self.filename)
            self.save()
            return True
        else:
            msg_box = QMessageBox()
            msg_box.setWindowTitle("Warning!")
            msg_box.setText("Maya Scene Not Saved")
            msg_box.setInformativeText("Do you want to save your changes?")
            msg_box.setStandardButtons(QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
            msg_box.setDefaultButton(QMessageBox.Save)
            ret = msg_box.exec()
            if ret == QMessageBox.Save:
                self.save()
                return True
        return False

    def save_maya_scene(self) -> None:
        """Save the current Maya scene."""
        if self.filename == "untitled.ma":
            cmds.file(rename=self.filename)
        if self.is_saved:
            self.save()

    def save_maya_scene_as(self) -> None:
        """Save the current Maya scene with a new name."""
        if self.filename == "untitled.ma":
            cmds.file(rename=self.filename)
            self.save()

    def get_file_name(self) -> str:
        """Show a save-file dialog for Maya scenes.

        Returns
        -------
        str
            The selected filename, or empty string if cancelled.
        """
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Select Filename Name",
            "untitled.ma",
            "Maya Scenes (*.ma,*.mb)",
        )
        return str(filename)

    def write_output(self, text: str, stdout: bool) -> None:
        """Route text to the editor's output window.

        Parameters
        ----------
        text : str
            The text to write.
        stdout : bool
            Whether the output came from stdout or stderr.
        """
        if hasattr(self, "editor"):
            self.editor.output_window.append_html(text)

    def save(self) -> None:
        """Save the Maya scene in the selected format (ASCII or binary)."""
        if self.scene_format.currentIndex() == 0:
            cmds.file(f=True, type="mayaAscii", save=True)
        else:
            cmds.file(f=True, type="mayaBinary", save=True)
        self.is_saved = True

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Exit on Escape key.

        Parameters
        ----------
        event : QKeyEvent
            The key event.
        """
        if event.key() == Qt.Key_Escape:
            QApplication.exit(1)

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Resize the editor to fill the window.

        Parameters
        ----------
        event : QResizeEvent
            The resize event.
        """
        self.editor.resize(event.size())
        super().resizeEvent(event)


if __name__ == "__main__":
    QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
    app = QApplication(sys.argv)
    maya.standalone.initialize(name="python")

    import maya.cmds as cmds

    root_path = cmds.moduleInfo(path=True, moduleName="MayaEditor")
    sys.path.insert(0, root_path + "/plug-ins")
    import sys
    import trace

    import MayaEditorCore

    try:
        window = MainWindow()
        window.resize(1024, 720)
        window.show()
        app.exec()
        maya.standalone.uninitialize()
    except Exception:
        traceback.print_exc()
    finally:
        window._stdout_wrapper.restore()
        window._stderr_wrapper.restore()
