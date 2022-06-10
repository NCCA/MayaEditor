# Copyright (C) 2022  Jonathan Macey
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
#  any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""Workspace module for the NCCA Maya Editor.

Contains all the code an functions for creating, reading and writing workspace data.
"""
import json
from typing import List

from PySide2.QtCore import QDir
from PySide2.QtWidgets import QInputDialog, QLineEdit, QMessageBox


class Workspace:
    """Class to manage workspaces in editor."""

    def __init__(self):
        """Workspace class to hold the data about the current workspaces."""
        self.workspace_name: str = ""
        self.files: List[str] = []
        self.is_saved: bool = True
        self.file_name: str = ""

    def add_file(self, file: str) -> None:
        """Add a file to the workspace.

        Add a new file to the Workspace at present this is the full path.

        Parameters :
        file (str) : the full path to the file to be saved.
        """
        self.files.append(file)
        self.is_saved = False

    def save(self, filename: str) -> None:
        """Save the workspace.

        The workspace is saved using a json format for ease, we don't need the full dictionary so we create what we need. We also save an internal state
        each time we save so we can check when re-loading the workspace.

        Parameters :
        filename (str) : the full path to save the workspace to
        """
        workspace = {}
        workspace["name"] = self.workspace_name
        workspace["files"] = self.files  # type: ignore
        workspace["file_name"] = self.file_name
        with open(filename, "w") as workspace_file:
            json.dump(workspace, indent=4, fp=workspace_file)
        self.is_saved = True

    def load(self, filename: str) -> None:
        """Load in a new workspace.

        This loads in a new workspace no check on overwrite are done
        Parameters :
        filename (str) : the full path to workspace to load
        """
        self.files.clear()
        try:
            with open(filename, "r") as workspace_file:
                workspace = json.load(workspace_file)
                self.name = workspace["name"]
                self.files = workspace["files"]
                self.file_name = workspace.get("file_name")
        except:
            print("problem loading last workspace")

    def new(self) -> None:
        """Create a new workspace.

        We check to ensure that the current workspace has been saved before loading a new one.
        """
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
