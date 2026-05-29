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
"""Line number area widget rendered alongside the editor."""

from typing import TYPE_CHECKING

from PySide6.QtCore import QEvent, QSize, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QWidget

if TYPE_CHECKING:
    from .TextEdit import TextEdit

FOLD_CLICK_MARGIN = 14


class LineNumberArea(QWidget):
    """Widget that renders line numbers at the side of a TextEdit editor."""

    def __init__(self, editor: "TextEdit") -> None:
        """Create a new LineNumberArea for the given editor.

        Parameters
        ----------
        editor : TextEdit
            The editor to which this line number area belongs.
        """
        super().__init__(editor)
        self.code_editor: "TextEdit" = editor

    def sizeHint(self) -> QSize:
        """Return the preferred size of the line number area.

        Returns
        -------
        QSize
            Width calculated from the editor's line number area width.
        """
        return QSize(self.code_editor.line_number_area_width(), 0)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse clicks in the fold-icon margin to toggle code folds."""
        fold_start_x = self.code_editor.line_number_area_width() - FOLD_CLICK_MARGIN
        if event.button() == Qt.LeftButton and event.position().x() >= fold_start_x:
            block = self.code_editor.firstVisibleBlock()
            block_number = block.blockNumber()
            top = (
                self.code_editor.blockBoundingGeometry(block)
                .translated(self.code_editor.contentOffset())
                .top()
            )
            bottom = top + self.code_editor.blockBoundingRect(block).height()
            click_y = event.position().y()
            while block.isValid():
                if top <= click_y <= bottom:
                    if block.isVisible():
                        self.code_editor.folding.toggle_fold(block_number)
                    return
                block = block.next()
                top = bottom
                bottom = top + self.code_editor.blockBoundingRect(block).height()
                block_number += 1
        super().mousePressEvent(event)

    def paintEvent(self, event: QEvent) -> None:
        """Paint line numbers by delegating to the editor's paint handler.

        Parameters
        ----------
        event : QEvent
            The paint event to process.
        """
        self.code_editor.lineNumberAreaPaintEvent(event)
