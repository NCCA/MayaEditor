"""Search-and-replace dialog overlay for the editor."""

from typing import TYPE_CHECKING

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QLineEdit, QPushButton, QToolButton

if TYPE_CHECKING:
    from .TextEdit import TextEdit


class FindDialog(QFrame):
    """Floating search / replace frame positioned over the parent editor."""

    def __init__(self, parent: "TextEdit") -> None:
        """Construct the FindDialog.

        Parameters
        ----------
        parent : TextEdit
            The editor this dialog is attached to.
        """
        super().__init__(parent)
        self.parent: "TextEdit" = parent
        self.setFrameShape(QFrame.Box)
        self.layout = QGridLayout()
        self.setLayout(self.layout)

        self.text_search = QLineEdit()
        self.text_search.setToolTip("search")
        self.layout.addWidget(self.text_search, 0, 0, 1, 2)
        self.text_search.textChanged.connect(self.parent.search_text)
        self.text_search.returnPressed.connect(self.return_pressed)

        self.items_found = QLabel("no results found")
        self.layout.addWidget(self.items_found, 0, 3)

        self.case_sensitive = QToolButton()
        self.case_sensitive.setCheckable(True)
        self.case_sensitive.setIcon(QIcon(":/icons/caseSensitive.png"))
        self.case_sensitive.setToolTip("match case")
        self.layout.addWidget(self.case_sensitive, 0, 4)

        self.whole_word = QToolButton()
        self.whole_word.setCheckable(True)
        self.whole_word.setIcon(QIcon(":/icons/wholeWord.png"))
        self.whole_word.setToolTip("match whole word")
        self.layout.addWidget(self.whole_word, 0, 5)

        self.hide_button = QToolButton()
        self.hide_button.setIcon(QIcon(":/icons/closeFind.png"))
        self.hide_button.setToolTip("hide")
        self.hide_button.clicked.connect(self.hide)
        self.layout.addWidget(self.hide_button, 0, 8)

        self.replace = QLineEdit()
        self.layout.addWidget(self.replace, 1, 0, 1, 2)
        self.replace.setToolTip("replace")
        self.replace.returnPressed.connect(self._replace_pressed)

        self.replace_button = QPushButton("Replace")
        self.replace_button.clicked.connect(self._replace_pressed)
        self.layout.addWidget(self.replace_button, 1, 3, 1, 1)

        self.replace_all_button = QPushButton("Replace All")
        self.replace_all_button.clicked.connect(self._replace_all_pressed)
        self.layout.addWidget(self.replace_all_button, 1, 4, 1, 1)

        self.show()
        self.hide()

    def return_pressed(self) -> None:
        """Trigger find_next on the parent editor when Return is pressed."""
        self.parent.find_next(self.text_search.text())

    def _replace_pressed(self) -> None:
        """Replace the current match with the replacement text."""
        self.parent.replace_current(self.text_search.text(), self.replace.text())

    def _replace_all_pressed(self) -> None:
        """Replace all occurrences of the search text with the replacement text."""
        self.parent.replace_all(self.text_search.text(), self.replace.text())
