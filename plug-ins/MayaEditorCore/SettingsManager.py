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
"""Settings management for the NCCA Maya Editor.

Owns QSettings persistence, font selection, and ruff-executable configuration.
Keeps all QSettings I/O out of EditorDialogCore.
"""

from typing import Any

from PySide6.QtCore import QDir, QSettings, QSize
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFileDialog, QFontDialog

from .PythonTextEdit import PythonTextEdit


class SettingsManager:
    """Manages load/save of QSettings and font/ruff-executable configuration.

    Parameters
    ----------
    dialog : EditorDialogCore
        The owning editor dialog.  Kept as ``self._dialog`` for access to UI
        elements and signals without creating a circular import.
    settings : QSettings
        The QSettings instance to read from and write to.
    """

    def __init__(self, dialog: Any, settings: QSettings) -> None:
        self._dialog = dialog
        self._settings = settings
        self._ruff_executable: str = ""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self) -> None:
        """Load editor settings from QSettings.

        Each section is wrapped individually so a corrupt or missing value never
        prevents the editor from opening.  PySide6 (Maya 2026+) broke the
        PySide2-style ``type=`` kwarg on QSettings.value() and also raises with
        complex default values, so all casting is done manually.
        """
        try:
            self._dialog.ui.editor_splitter.restoreState(
                self._settings.value("splitter")
            )
        except Exception:
            pass
        try:
            self._dialog.ui.vertical_splitter.restoreState(
                self._settings.value("vertical_splitter")
            )
        except Exception:
            pass
        try:
            size = self._settings.value("size")
            if size is not None:
                self._dialog.resize(size)
            else:
                self._dialog.resize(QSize(1024, 720))
        except Exception:
            self._dialog.resize(QSize(1024, 720))

        # Load ruff executable BEFORE loading workspace files so that any
        # editors created during workspace restore already have the correct path.
        try:
            ruff_exe = self._settings.value("ruff_executable")
            self._ruff_executable = str(ruff_exe) if ruff_exe else ""
        except Exception:
            self._ruff_executable = ""

        try:
            workspace = self._settings.value("workspace")
            if workspace:
                self._dialog.load_workspace_to_editor(workspace)
        except Exception:
            pass
        try:
            root = self._settings.value("file_system_root")
            if root:
                self._dialog.file_system_root = str(root)
        except Exception:
            pass

        self._settings.beginGroup("Font")
        try:
            name = str(self._settings.value("font-name") or "Courier New")
            size = int(self._settings.value("font-size") or 12)
            weight = int(self._settings.value("font-weight") or 50)
            _italic = self._settings.value("font-italic")
            italic = _italic in (True, "true", "True", "1", 1)
        except Exception:
            name, size, weight, italic = "Courier New", 12, 50, False
        self._settings.endGroup()

        self._dialog.font = QFont(name, size, weight, italic)
        self._dialog.update_fonts.emit(self._dialog.font)

    def save(self) -> None:
        """Save current editor settings to QSettings."""
        self._settings.setValue(
            "splitter", self._dialog.ui.editor_splitter.saveState()
        )
        self._settings.setValue(
            "vertical_splitter", self._dialog.ui.vertical_splitter.saveState()
        )
        self._settings.setValue("size", self._dialog.size())
        self._settings.setValue("workspace", self._dialog.workspace.file_name)
        self._settings.setValue("file_system_root", self._dialog.file_system_root)
        self._settings.setValue("ruff_executable", self._ruff_executable)
        self._settings.beginGroup("Font")
        self._settings.setValue("font-name", self._dialog.font.family())
        self._settings.setValue("font-size", self._dialog.font.pointSize())
        self._settings.setValue("font-weight", self._dialog.font.weight())
        self._settings.setValue("font-italic", self._dialog.font.italic())
        self._settings.endGroup()

    def change_font(self) -> None:
        """Show a font dialog and apply the selected font to all editors."""
        ok, font = QFontDialog.getFont(self._dialog)
        if ok:
            self._dialog.font = font
            self._dialog.update_fonts.emit(self._dialog.font)

    def set_ruff_executable(self) -> None:
        """Open a file dialog to set a custom path for the ruff executable.

        The chosen path is persisted in QSettings under the key
        ``"ruff_executable"`` and applied to every Python editor tab that is
        currently open as well as any subsequently created tab.
        """
        current = str(self._settings.value("ruff_executable") or "")
        path, _ = QFileDialog.getOpenFileName(
            self._dialog,
            "Select ruff Executable",
            current or "/usr/local/bin",
            "Executable (*)",
        )
        if path:
            self._settings.setValue("ruff_executable", path)
            self._ruff_executable = path
            # Update every open Python editor via thread-safe signal and
            # immediately re-run the linter so the user sees results right away.
            tab = self._dialog.ui.editor_tab
            for i in range(tab.count()):
                editor = tab.widget(i)
                if isinstance(editor, PythonTextEdit):
                    editor._linter.set_executable(path)
                    editor._run_linter()
