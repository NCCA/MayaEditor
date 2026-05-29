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
"""Code folding manager for the TextEdit editor."""

from typing import TYPE_CHECKING, Dict, Optional, Tuple

from PySide6.QtCore import QRect, Slot
from PySide6.QtGui import QTextBlock, QTextCursor

if TYPE_CHECKING:
    from .TextEdit import TextEdit


class CodeFoldingManager:
    """Manages code folding state and operations for a TextEdit editor.

    This class is owned by a TextEdit instance via ``editor.folding`` and
    handles all indent-based fold regions, toggle state, and visibility changes.

    Parameters
    ----------
    editor : TextEdit
        The parent text editor that this manager acts upon.
    """

    def __init__(self, editor: "TextEdit") -> None:
        """Initialise with the owning editor.

        Parameters
        ----------
        editor : TextEdit
            The text editor whose document and viewport will be manipulated.
        """
        self._editor = editor
        self.fold_states: Dict[int, bool] = {}

    def indent_level(self, block: "QTextBlock") -> int:
        """Return the indentation level (in characters) of the given block.

        Parameters
        ----------
        block : QTextBlock
            The text block to check.

        Returns
        -------
        int
            Number of leading whitespace characters, or -1 if the block is blank.
        """
        text = block.text()
        if not text.strip():
            return -1
        return len(text) - len(text.lstrip())

    def is_fold_start(self, block: "QTextBlock") -> bool:
        """Check whether the block is a foldable region start.

        A block is a fold start if it has at least one non-blank child at a
        deeper indentation level.
        """
        text = block.text().strip()
        if not text or text.startswith("#") or text.startswith("//"):
            return False
        level = self.indent_level(block)
        child = block.next()
        while child.isValid():
            if child.text().strip():
                return self.indent_level(child) > level
            child = child.next()
        return False

    def _fold_region(
        self, block: "QTextBlock"
    ) -> Optional[Tuple["QTextBlock", "QTextBlock"]]:
        """Return the (first, last) child block pair for a foldable block.

        Parameters
        ----------
        block : QTextBlock
            The potential fold-start block.

        Returns
        -------
        tuple of (QTextBlock, QTextBlock) or None
            The first and last child blocks, or None if not foldable.
        """
        if not self.is_fold_start(block):
            return None
        level = self.indent_level(block)
        first = None
        last = None
        child = block.next()
        while child.isValid():
            if child.text().strip():
                child_level = self.indent_level(child)
                if child_level <= level:
                    break
                if first is None:
                    first = child
                last = child
            child = child.next()
        if first is not None:
            return (first, last)
        return None

    @Slot(int)
    def toggle_fold(self, line_number: int) -> None:
        """Toggle the folded state of the code region at *line_number*.

        Parameters
        ----------
        line_number : int
            0-based block number in the document.
        """
        block = self._editor.document().findBlockByNumber(line_number)
        region = self._fold_region(block)
        if region is None:
            return

        first, last = region
        is_folded = self.fold_states.get(line_number, False)

        if is_folded:
            self.fold_states[line_number] = False
            child = first
            while True:
                child.setVisible(True)
                if child == last:
                    break
                child = child.next()
        else:
            self.fold_states[line_number] = True
            child = first
            while True:
                child.setVisible(False)
                if child == last:
                    break
                child = child.next()

        self._editor.document().markContentsDirty(
            0, self._editor.document().blockCount()
        )
        self._editor.update_line_number_area(
            QRect(0, 0, self._editor.line_number_area_width(), self._editor.height()),
            0,
        )

    def clear_folds(self) -> None:
        """Reset all fold states and make all blocks visible."""
        if not self.fold_states:
            return
        self.fold_states.clear()
        block = self._editor.document().begin()
        while block.isValid():
            if not block.isVisible():
                block.setVisible(True)
            block = block.next()
        self._editor.document().markContentsDirty(
            0, self._editor.document().blockCount()
        )
        self._editor.update_line_number_area(
            QRect(0, 0, self._editor.line_number_area_width(), self._editor.height()),
            0,
        )
