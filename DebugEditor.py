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
"""Developer hot-reload script.

Unloads all MayaEditorCore sub-modules from ``sys.modules`` and re-imports
them so code changes take effect without restarting Maya.

Usage
-----
Run this script from Maya's Script Editor (or source it) after editing any
``MayaEditorCore`` module.
"""

import sys

import maya.cmds as cmds


def editor() -> None:
    """Delete stale MayaEditorCore modules and re-import the editor.

    Removes all known sub-modules from ``sys.modules``, then does a fresh
    import of ``MayaEditorCore`` and opens the editor dialog.
    """
    if cmds.workspaceControl("NCCA_Script_EditorWorkspaceControl", exists=True):
        cmds.deleteUI("NCCA_Script_EditorWorkspaceControl", control=True)

    modules = (
        "MayaEditorCore.EditorDialog",
        "MayaEditorCore",
        "MayaEditorCore.PythonTextEdit",
        "MayaEditorCore.PythonHighlighter",
        "MayaEditorCore.MelHighlighter",
        "MayaEditorCore.Workspace",
        "MayaEditorCore.EditorToolBar",
        "MayaEditorCore.OutputToolBar",
        "MayaEditorCore.TextEdit",
        "MayaEditorCore.LineNumberArea",
        "MayaEditorCore.MelTextEdit",
        "MayaEditorCore.SidebarModels",
        "MayaEditorCore.FindDialog",
        "MayaEditorCore.EditorIcons",
        "MayaEditorCore.BaseHighlighter",
        "MayaEditorCore.CodeFoldingManager",
        "MayaEditorCore.SettingsManager",
        "MayaEditorCore.OutputManager",
    )

    root_path = cmds.moduleInfo(path=True, moduleName="MayaEditor")
    sys.path.insert(0, root_path + "/plug-ins")
    if "MayaEditorCore.EditorDialog" in sys.modules.keys():
        for module in modules:
            del sys.modules[module]
        print("deleting and reloading module")

    import MayaEditorCore

    MayaEditorCore.EditorDialog()


editor()
