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
"""MayaEditor plugin — registers the ``MayaEditor`` MPxCommand.

Load the MayaEditorCore package and provide a dockable script editor that
replaces the built-in Script Editor.
"""

import os
import sys
from builtins import int
from typing import Any, Optional

import maya.api.OpenMaya as OpenMaya
import maya.api.OpenMayaUI as OpenMayaUI
import maya.cmds as cmds
import maya.mel as mel

try:
    root_path = cmds.moduleInfo(path=True, moduleName="MayaEditor")
except RuntimeError:
    root_path = os.path.dirname(os.path.abspath(__file__)).replace("/plug-ins", "")

sys.path.insert(0, root_path + "/plug-ins")
try:
    print("deleting MayaEditorCore")
    del sys.modules["MayaEditorCore"]
except KeyError:
    pass

try:
    import MayaEditorCore  # noqa: F401
except ImportError:
    OpenMaya.MGlobal.displayError("Trouble importing MayaEditorCore Module")
    raise

# Maya's MayaQWidgetDockableMixin requires the same window instance to be returned
# across workspace control restore cycles. This global is the only practical way
# to maintain the instance across plugin reloads and workspace restores.
# The try/except block above that deletes MayaEditorCore from sys.modules
# handles hot-reloading of the core logic while this global preserves the
# window handle required by Maya's UI restoration mechanism.
MayaEditorMixinWindow: Optional[Any] = None


def MayaEditorUIScript(restore: bool = False) -> Optional[Any]:
    """Create or restore the MayaEditor dockable UI.

    Parameters
    ----------
    restore : bool
        When True the workspace control already exists and only the UI needs
        to be restored into it.

    Returns
    -------
    QWidget or None
        The editor mixin window.
    """
    global MayaEditorMixinWindow
    import MayaEditorCore

    if restore:
        restoredControl = OpenMayaUI.MQtUtil.getCurrentParent()

    if MayaEditorMixinWindow is None:
        print("creating a new ui")
        try:
            MayaEditorMixinWindow = MayaEditorCore.EditorDialog()
            MayaEditorMixinWindow.setObjectName("MayaEditor")
        except Exception:
            import traceback

            OpenMaya.MGlobal.displayWarning(traceback.format_exc())
            raise

    if restore:
        mixinPtr = OpenMayaUI.MQtUtil.findControl(MayaEditorMixinWindow.objectName())
        OpenMayaUI.MQtUtil.addWidgetToMayaLayout(int(mixinPtr), int(restoredControl))
    else:
        MayaEditorMixinWindow.show(
            dockable=True,
            height=600,
            width=800,
            uiScript="MayaEditorUIScript(restore=True)",
        )
    return MayaEditorMixinWindow


maya_useNewAPI = True


class MayaEditor(OpenMaya.MPxCommand):
    """MPxCommand that opens the NCCA Maya Editor window."""

    CMD_NAME: str = "MayaEditor"
    ui: Optional[Any] = None

    def __init__(self) -> None:
        """Initialise the command."""
        super().__init__()

    @classmethod
    def doIt(cls, args: Any) -> Optional[Any]:
        """Execute the command: create or show the editor UI.

        Parameters
        ----------
        args : Any
            Command arguments (unused).

        Returns
        -------
        QWidget or None
            The editor widget instance.
        """
        ui = MayaEditorUIScript()
        if ui is not None:
            try:
                cmds.workspaceControl(
                    "MayaEditorWorkspaceControl", e=True, restore=True
                )
            except Exception:
                pass
        return ui

    @classmethod
    def creator(cls) -> "MayaEditor":
        """Factory method called by Maya to create a command instance.

        Returns
        -------
        MayaEditor
            A new instance of the command.
        """
        return cls()

    @classmethod
    def cleanup(cls) -> None:
        """Delete the editor mixin window and release resources."""
        global MayaEditorMixinWindow
        if MayaEditorMixinWindow is not None:
            try:
                MayaEditorMixinWindow.close()
            except Exception:
                pass
            try:
                cmds.deleteUI(
                    f"{MayaEditorMixinWindow.objectName()}WorkspaceControl",
                    control=True,
                )
            except Exception:
                pass
            MayaEditorMixinWindow.setParent(None)
            MayaEditorMixinWindow.deleteLater()
            MayaEditorMixinWindow = None


def initializePlugin(plugin: Any) -> None:
    """Register the MayaEditor command with Maya.

    Parameters
    ----------
    plugin : MObject
        The plugin object provided by Maya.
    """
    vendor = "NCCA"
    version = "1.0.0"
    plugin_fn = OpenMaya.MFnPlugin(plugin, vendor, version)
    try:
        plugin_fn.registerCommand(MayaEditor.CMD_NAME, MayaEditor.creator)
        cmds.evalDeferred("cmds.MayaEditor()")
        mel.eval("""
                global proc ScriptEditor() {
                    python("cmds.MayaEditor()");
                }
            """)
    except Exception:
        OpenMaya.MGlobal.displayError(
            f"Failed to register command: {MayaEditor.CMD_NAME}"
        )


SCRIPT_EDITOR_PROC = """
global proc ScriptEditor()
{
    if (`scriptedPanel -q -exists scriptEditorPanel1`)
    {
        scriptedPanel -e -tor scriptEditorPanel1;
        showWindow scriptEditorPanel1Window;
        selectCurrentExecuterControl;
    }
    else
    {
        CommandWindow;
    }
}
"""


def uninitializePlugin(plugin: Any) -> None:
    """Deregister the MayaEditor command.

    Parameters
    ----------
    plugin : MObject
        The plugin object provided by Maya.
    """
    MayaEditor.cleanup()
    plugin_fn = OpenMaya.MFnPlugin(plugin)
    try:
        plugin_fn.deregisterCommand(MayaEditor.CMD_NAME)

    except Exception:
        OpenMaya.MGlobal.displayError(
            f"Failed to deregister command: {MayaEditor.CMD_NAME}"
        )
    mel.eval(SCRIPT_EDITOR_PROC)


if __name__ == "__main__":
    plugin_name = "MayaEditor.py"
    cmds.evalDeferred(
        f'if cmds.pluginInfo("{plugin_name}", q=True, loaded=True): cmds.unloadPlugin("{plugin_name}")'
    )
    cmds.evalDeferred(
        f'if not cmds.pluginInfo("{plugin_name}", q=True, loaded=True): cmds.loadPlugin("{plugin_name}")'
    )
