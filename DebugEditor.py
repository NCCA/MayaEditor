import importlib
import sys


def editor():
    root_path = cmds.moduleInfo(path=True, moduleName="MayaEditor")
    sys.path.insert(0, root_path + "/plug-ins")
    if "MayaEditorCore.EditorDialog" in sys.modules.keys():
        del sys.modules["MayaEditorCore.EditorDialog"]
        del sys.modules["MayaEditorCore"]
        del sys.modules["MayaEditorCore.PlainTextEdit"]
        del sys.modules["MayaEditorCore.Highlighter"]
        del sys.modules["MayaEditorCore.Workspace"]
        del sys.modules["MayaEditorCore.Settings"]

        print("deleting and reloading module")
    import MayaEditorCore

    MayaEditorCore.EditorDialog()


editor()
