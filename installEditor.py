#!/usr/bin/env python
import os
import platform
import sys
from pathlib import Path

maya_locations = {
    "Linux": "/maya",
    "Darwin": "/Library/Preferences/Autodesk/maya",
    "Windows": "\\Documents\\maya\\version",
}


def install_module(location):
    print(f"installing to {location}")
    # first write the module file
    current_dir = Path.cwd()
    module_path = location + "modules/MayaEditor.mod"
    if not Path().is_file(module_path):
        print("writing module file")
        with open(module_path, "w") as file:
            file.write(f"+ MayaEditor 1.0 {current_dir}\n")
            file.write("MAYA_PLUG_IN_PATH +:= plug-ins\n")


def check_maya_installed(op_sys):
    mloc = f"{Path.home()}{maya_locations.get(op_sys)}/"
    if not os.path.isdir(mloc):
        raise
    return mloc


if __name__ == "__main__":
    op_sys = platform.system()
    try:
        m_loc = check_maya_installed(op_sys)
    except:
        print("Error can't find maya install")
        sys.exit(os.EX_CONFIG)

    install_module(m_loc)
