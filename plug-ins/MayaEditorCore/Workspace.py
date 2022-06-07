import json
from typing import List

from PySide2.QtCore import QDir
from PySide2.QtWidgets import QInputDialog, QLineEdit, QMessageBox


class Workspace:
    def __init__(self):
        self.workspace_name: str = ""
        self.files: List[str] = []
        self.is_saved: bool = True
        self.file_name: str = ""

    def add_file(self, file: str) -> None:
        self.files.append(file)
        self.is_saved = False

    def save(self, filename: str) -> None:
        workspace = {}
        workspace["name"] = self.workspace_name
        workspace["files"] = self.files  # type: ignore
        workspace["file_name"] = self.file_name
        with open(filename, "w") as workspace_file:
            json.dump(workspace, indent=4, fp=workspace_file)
        self.is_saved = True

    def load(self, filename: str) -> None:
        self.files.clear()

        with open(filename, "r") as workspace_file:
            workspace = json.load(workspace_file)
            self.name = workspace["name"]
            self.files = workspace["files"]
            self.file_name = workspace.get("file_name")

    def new(self) -> None:
        if self.is_saved is not True:
            msg_box = QMessageBox()
            msg_box.setWindowTitle("Warning!")
            msg_box.setText("Workspace Not Saved")
            msg_box.setInformativeText("Do you want to save your changes?")
            msg_box.setStandardButtons(
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
            )
            msg_box.setDefaultButton(QMessageBox.Save)
            ret = msg_box.exec_()
            if ret == QMessageBox.Save:
                self.save(self.file_name)
            elif ret == QMessageBox.Discard:
                pass
            elif ret == QMessageBox.Cancel:
                return

        text, ok = QInputDialog().getText(
            None,  # type: ignore
            "New Workspace",
            "Workspace:",
            QLineEdit.EchoMode.Normal,
        )

        if ok and text:
            self.files.clear()
            self.name = text
            self.file_name = ""
            self.is_saved = False
