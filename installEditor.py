#!/usr/bin/env python
import os
import platform
import sys
from pathlib import Path

maya_locations = {
    "Linux": "/maya",
    "Darwin": "/Library/Preferences/Autodesk/maya",
    "Windows": "\\Documents\\maya\\",
}


def install_module(location, os):
    print(f"installing to {location}")
    # first write the module file
    current_dir = Path.cwd()
    # if the module folder doesn't exist make it
    module_dir = Path(location + "//modules")
    module_path = location + "//modules/MayaEditor.mod"
    ## change to \\ for windows (easier then messing with Path objects)
    if os == "Windows":

        module_dir = Path(location + "\\modules")
        module_path = location + "modules\\MayaEditor.mod"

    module_dir.mkdir(exist_ok=True)

    if not Path(module_path).is_file():
        print("writing module file")
        with open(module_path, "w") as file:
            file.write(f"+ MayaEditor 1.0 {current_dir}\n")
            file.write("MAYA_PLUG_IN_PATH +:= plug-ins\n")


def check_maya_installed(op_sys):
    mloc = f"{Path.home()}{maya_locations.get(op_sys)}"
    if not os.path.isdir(mloc):
        raise
    return mloc


if __name__ == "__main__":
    op_sys = platform.system()
    try:
        m_loc = check_maya_installed(op_sys)
    except:
        print("Error can't find maya install")
        sys.exit(-1)

    install_module(m_loc, op_sys)
