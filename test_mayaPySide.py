#!/Applications/Autodesk/maya2025/Maya.app/Contents/bin/mayapy
"""Test script for Maya PySide6 dialog integration."""

from __future__ import annotations

import sys
from typing import Optional

from qtpy import QtWidgets


class SimpleDialog(QtWidgets.QDialog):
    """A minimal test dialog to verify Maya PySide6 integration."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        """Construct the SimpleDialog.

        Parameters
        ----------
        parent : QWidget or None
            Optional parent widget.
        """
        super(SimpleDialog, self).__init__(parent)
        self.setWindowTitle("Simple Dialog")
        self.setMinimumWidth(200)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    dialog = SimpleDialog()
    dialog.show()
    app.exec()
