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
"""This is for Developer use only.

This function makes it easier for developers to run the editor as it will unload all the modules see code notes for how to use
"""
import importlib
import sys

import maya.cmds as cmds


def editor() -> None:
    # if you add a new module to the project add it here
    modules = (
        "MayaEditorCore.EditorDialog",
        "MayaEditorCore",
        "MayaEditorCore.PlainTextEdit",
        "MayaEditorCore.Highlighter",
        "MayaEditorCore.Workspace",
        "MayaEditorCore.EditorToolBar",
        "MayaEditorCore.OutputToolBar",
    )
    # query the MayaEditor module file for location of source
    root_path = cmds.moduleInfo(path=True, moduleName="MayaEditor")
    # add this to our python path to we can access the modules
    sys.path.insert(0, root_path + "/plug-ins")
    # if the module is already loaded remove the modules then reload
    if "MayaEditorCore.EditorDialog" in sys.modules.keys():
        for module in modules:
            del sys.modules[module]
        print("deleting and reloading module")
    import MayaEditorCore

    MayaEditorCore.EditorDialog()


editor()
