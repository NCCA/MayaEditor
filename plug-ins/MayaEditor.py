import os
import sys

import maya.api.OpenMaya as OpenMaya
import maya.api.OpenMayaUI as OpenMayaUI
import maya.cmds as cmds
import maya.OpenMayaMPx as OpenMayaMPx
import maya.OpenMayaUI as omui
from PySide2 import QtCore, QtWidgets
from PySide2.QtCore import QFile
from PySide2.QtGui import QColor, QFont
from PySide2.QtUiTools import QUiLoader
from shiboken2 import wrapInstance

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


def maya_useNewAPI():
    """
    Can either use this function (which works on earlier versions)
    or we can set maya_useNewAPI = True
    """
    pass


maya_useNewAPI = True


class MayaEditor(OpenMaya.MPxCommand):

    CMD_NAME = "MayaEditor"
    ui = None

    def __init__(self):
        super(MayaEditor, self).__init__()
        cmds.commandPort(name=":7777", sourceType="python", echoOutput=True)

    @classmethod
    def doIt(cls, args):
        """
        Called when the command is executed in script
        """
        if MayaEditor.ui is None:
            MayaEditor.ui = MayaEditorCore.EditorDialog()
            MayaEditor.ui.showNormal()
        else:
            MayaEditor.ui.showNormal()

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
