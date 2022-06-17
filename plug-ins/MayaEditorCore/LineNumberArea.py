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

from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import QWidget


# Based on the Qt Editor Demo
class LineNumberArea(QWidget):
    """Simple LineNumberArea class to render line numbers at the side of our editor."""

    def __init__(self, editor):
        """Create a new LineNumberArea for our Editor.

        Parameters :
        editor (TextEdit) : The editor to add line numbers to
        """
        super().__init__(editor)
        self.code_editor = editor

    def sizeHint(self) -> QSize:
        """Get the current size of the area.

        Returns (QSize) : the sizeHint for the area
        """
        return QSize(self.code_editor.line_number_area_width(), 0)

    def paintEvent(self, event: QEvent) -> None:
        """Override the paint event to allow number drawing."""
        self.code_editor.lineNumberAreaPaintEvent(event)

