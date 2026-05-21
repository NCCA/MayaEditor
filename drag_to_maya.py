"""Drag-and-drop Maya module installer.

This module is intended to be drag-dropped into Maya's viewport to install
and load the MayaEditor module.
"""

from __future__ import annotations

import importlib
import sys
import textwrap
from pathlib import Path
from typing import Any, Optional

import maya.cmds as cmds

MODULE_NAME: str = "MayaEditor"


def reload_package(package_name: str, reimport: bool = True) -> Optional[object]:
    """
    Purge all cached submodules for a package and optionally reimport.
    Unloads deepest submodules first to avoid KeyError on parent removal.
    Safe to call repeatedly during development.
    """
    to_unload = sorted(
        [
            k
            for k in sys.modules
            if k == package_name or k.startswith(package_name + ".")
        ],
        key=lambda x: x.count("."),
        reverse=True,  # deepest submodules first
    )
    for key in to_unload:
        del sys.modules[key]

    if reimport:
        return importlib.import_module(package_name)
    return None


def install_module() -> None:
    """
    Write a .mod file into Maya's user modules directory and load the module.
    Uses textwrap.dedent so the file contains no leading whitespace that would
    confuse Maya's module parser.
    """
    print("Installing module...")
    user_dir = Path(cmds.internalVar(userAppDir=True))
    modules_dir = user_dir / "modules"
    modules_dir.mkdir(parents=True, exist_ok=True)

    mod_file_path = modules_dir / f"{MODULE_NAME}.mod"
    mod_content = textwrap.dedent(f"""\
        + {MODULE_NAME} 1.0 {Path(__file__).parent}
        MAYA_PLUG_IN_PATH +:= plug-ins
        MAYA_SCRIPT_PATH +:= plug-ins/AETemplates
        XBMLANGPATH +:= icons
        PYTHONPATH +:= plug-ins/
    """)

    mod_file_path.write_text(mod_content, encoding="utf-8")
    print(f"  Module file written to: {mod_file_path}")

    cmds.loadModule(scan=True)
    cmds.loadModule(load=MODULE_NAME)
    print("  Module loaded.")


def onMayaDroppedPythonFile(*args: Any, **kwargs: Any) -> None:  # noqa: N802
    """Entry point called automatically when this file is drag-dropped into Maya."""
    print("Installer dropped.")

    # Remove any stale reference to this installer script itself
    try:
        sys.modules.pop("drag_to_maya", None)
    except Exception as exc:
        print(f"Warning: failed to remove stale module reference — {exc}")

    try:
        install_module()
    except Exception as exc:
        cmds.error(f"ClutterBase: module install failed — {exc}")
        return

    reload_package("MayaEditorCore")
