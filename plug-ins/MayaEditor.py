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
import os
import sys

import maya.api.OpenMaya as OpenMaya
import maya.api.OpenMayaUI as OpenMayaUI
import maya.cmds as cmds
from PySide2 import QtCore, QtWidgets
from PySide2.QtCore import QFile
from PySide2.QtGui import QColor, QFont
from PySide2.QtUiTools import QUiLoader
from shiboken2 import wrapInstance  # type: ignore
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
from builtins import int

# Grab the module root so we can append our python path
root_path = cmds.moduleInfo(path=True, moduleName="MayaEditor")
try:
    import importlib

    # for debug purposed it is easier to re-load module
    # so append to path then try to delete if exists.
    sys.path.insert(0, root_path + "/plug-ins")
    try:
        print("deleting MayaEditorCore")
        del sys.modules["MayaEditorCore"]
        import MayaEditorCore
    except:
        import MayaEditorCore
except ImportError:
    OpenMaya.MGlobal.displayError("Trouble importing MayaEditorCore Module")
    # throw exception and let maya deal with it
    raise

MayaEditorMixinWindow=None

def MayaEditorUIScript(restore=False):
    global MayaEditorMixinWindow
    import MayaEditorCore

    ''' When the control is restoring, the workspace control has already been created and
        all that needs to be done is restoring its UI.
    '''
    if restore == True:
        # Grab the created workspace control with the following.
        restoredControl = omui.MQtUtil.getCurrentParent()

    if MayaEditorMixinWindow is None:
        # Create a custom mixin widget for the first time
        print("creating a new ui")
        MayaEditorMixinWindow = MayaEditorCore.EditorDialog()
        MayaEditorMixinWindow.setObjectName('MayaEditor')

    if restore == True:
        # Add custom mixin widget to the workspace control
        mixinPtr = omui.MQtUtil.findControl(MayaEditorMixinWindow.objectName())
        omui.MQtUtil.addWidgetToMayaLayout(int(mixinPtr), int(restoredControl))
    else:
        # Create a workspace control for the mixin widget by passing all the needed parameters. See workspaceControl command documentation for all available flags.
        MayaEditorMixinWindow.show(dockable=True, height=600, width=800, uiScript='MayaEditorUIScript(restore=True)')

    return MayaEditorMixinWindow



''' Using the workspaceControl Maya command to query/edit flags about the created 
    we can use maya.cmds.workspaceControl('MayaEditorWorkspaceControl', e=True,restore=True)
    to re-show the workspace editor if needed. Will need to add this to a button at some stage
'''


maya_useNewAPI = True  # type: ignore


class MayaEditor(OpenMaya.MPxCommand):

    CMD_NAME = "MayaEditor"
    ui = None

    def __init__(self):
        super(MayaEditor, self).__init__()

    @classmethod
    def doIt(cls, args):
        """
        Called when the command is executed in script
        """
        ui = MayaEditorUIScript()
        if ui is not None:
            try :
                cmds.workspaceControl('MayaEditorWorkspaceControl', e=True, restore=True)
            except :
                pass
        return ui

    @classmethod
    def creator(cls):
        """
        Think of this as a factory
        """
        return MayaEditor()

    @classmethod
    def cleanup(cls):
        # cleanup the UI and call the destructors
        MayaEditor.ui.deleteLater()
        MayaEditor.ui = None


def initializePlugin(plugin):
    """
    Load our plugin
    """
    vendor = "NCCA"
    version = "1.0.0"

    plugin_fn = OpenMaya.MFnPlugin(plugin, vendor, version)
    try:
        plugin_fn.registerCommand(MayaEditor.CMD_NAME, MayaEditor.creator)
        cmds.evalDeferred("cmds.MayaEditor()")
    except:
        OpenMaya.MGlobal.displayError(
            "Failed to register command: {0}".format(MayaEditor.CMD_NAME)
        )


def uninitializePlugin(plugin):
    """
    Exit point for a plugin
    """
    # cleanup the dialog first
    MayaEditor.cleanup()
    plugin_fn = OpenMaya.MFnPlugin(plugin)
    try:
        plugin_fn.deregisterCommand(MayaEditor.CMD_NAME)
    except:
        OpenMaya.MGlobal.displayError(
            "Failed to deregister command: {0}".format(MayaEditor.CMD_NAME)
        )



if __name__ == "__main__":
    """
    So if we execute this in the script editor it will be a __main__ so we can put testing code etc here
    Loading the plugin will not run this
    As we are loading the plugin it needs to be in the plugin path.
    """

    plugin_name = "MayaEditor.py"

    cmds.evalDeferred(
        'if cmds.pluginInfo("{0}", q=True, loaded=True): cmds.unloadPlugin("{0}")'.format(
            plugin_name
        )
    )
    cmds.evalDeferred(
        'if not cmds.pluginInfo("{0}", q=True, loaded=True): cmds.loadPlugin("{0}")'.format(
            plugin_name
        )
    )
