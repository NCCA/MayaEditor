############################################################################### Copyright (C) 2022  Jonathan Macey
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
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.##############################################################################
"""Workspace module for the NCCA Maya Editor.

Manages the list of files associated with a workspace, and handles saving
/ loading workspace data in JSON format.
"""

import json
from pathlib import Path
from typing import List

from PySide6.QtWidgets import QInputDialog, QLineEdit, QMessageBox


class Workspace:
    """Manages workspace data: a named collection of file paths."""

    def __init__(self) -> None:
        """Initialise an empty workspace with default values."""
        self.workspace_name: str = ""
        self.files: List[str] = []
        self.is_saved: bool = True
        self.file_name: str = ""
        self.root: str = ""

    def add_file(self, file: str) -> None:
        """Add a file path to the workspace if not already present.

        Parameters
        ----------
        file : str
            Full path to the file to add.
        """
        if file not in self.files:
            self.files.append(file)
        self.is_saved = False

    def remove_file(self, file: str) -> None:
        """Remove a file from the workspace by partial name match.

        Parameters
        ----------
        file : str
            Partial or full filename to remove.
        """
        for name in list(self.files):
            if file in name:
                self.files.remove(name)
                self.is_saved = False
                return

    def save(self, filename: str) -> None:
        """Save the workspace as a JSON file.

        Parameters
        ----------
        filename : str
            Full path where the workspace file will be written.
        """
        workspace = {
            "name": self.workspace_name,
            "files": self.files,
            "root": self.root,
        }
        with open(filename, "w") as workspace_file:
            json.dump(workspace, indent=4, fp=workspace_file)
        self.is_saved = True

    def load(self, filename: str) -> bool:
        """Load a workspace from a JSON file.

        Parameters
        ----------
        filename : str
            Full path to the workspace file to load.

        Returns
        -------
        bool
            True if the workspace was loaded successfully, False otherwise.
        """
        self.files.clear()
        self.file_name = filename
        path = Path(filename)
        if path.is_file():
            try:
                with open(filename, "r") as workspace_file:
                    workspace = json.load(workspace_file)
                    self.workspace_name = workspace["name"]
                    self.files = workspace["files"]
                    self.root = workspace.get("root", "")
                    return True
            except Exception:
                print("problem loading last workspace")
                self.workspace_name = ""
                self.files = []
                self.file_name = ""
                self.root = ""
                return False
        else:
            return False

    def new(self) -> None:
        """Create a new workspace after checking the current one is saved."""
        if self.check_saved():
            text, ok = QInputDialog().getText(
                None,
                "New Workspace",
                "Workspace:",
                QLineEdit.EchoMode.Normal,
            )
            if ok and text:
                self.files.clear()
                self.workspace_name = text
                self.file_name = ""
                self.root = ""
                self.is_saved = False

    def check_saved(self) -> bool:
        """Prompt to save the workspace if it has unsaved changes.

        Returns
        -------
        bool
            True if the user saved or discarded changes, False on cancel.
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
            ret = msg_box.exec()
            if ret == QMessageBox.Save:
                self.save(self.file_name)
                return True
            elif ret == QMessageBox.Discard:
                return True
            else:
                return False
        return True

    def close(self) -> None:
        """Check for unsaved changes when the workspace is closed."""
        self.check_saved()
