"""Search-and-replace dialog overlay for the editor."""

from typing import TYPE_CHECKING

from PySide6.QtCore import Signal  # type: ignore
from PySide6.QtGui import QIcon  # type: ignore
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QLineEdit, QPushButton, QToolButton  # type: ignore

if TYPE_CHECKING:
    from .TextEdit import TextEdit  # type: ignore


class FindDialog(QFrame):
    """Floating search / replace frame positioned over the parent editor."""

    find_next_requested = Signal(str)
    replace_requested = Signal(str, str)
    replace_all_requested = Signal(str, str)

    def __init__(self, parent: "TextEdit") -> None:
        """Construct the FindDialog.

        Parameters
        ----------
        parent : TextEdit
            The editor this dialog is attached to.
        """
        super().__init__(parent)
        self.setFrameShape(QFrame.Box)
        self.layout = QGridLayout()
        self.setLayout(self.layout)

        self.find_next_requested.connect(parent.find_next)
        self.replace_requested.connect(parent.replace_current)
        self.replace_all_requested.connect(parent.replace_all)

        self.text_search = QLineEdit()
        self.text_search.setToolTip("search")
        self.layout.addWidget(self.text_search, 0, 0, 1, 2)
        self.text_search.textChanged.connect(parent.search_text)
        self.text_search.returnPressed.connect(self.return_pressed)

        self.items_found = QLabel("no results found")
        self.layout.addWidget(self.items_found, 0, 3)

        self.case_sensitive = QToolButton()
        self.case_sensitive.setCheckable(True)
        case_sensitive_icon = QIcon(":/icons/caseSensitive.png")
        if case_sensitive_icon.isNull():
            case_sensitive_icon = QIcon.fromTheme("format-text-bold")
        self.case_sensitive.setIcon(case_sensitive_icon)
        if case_sensitive_icon.isNull():
            self.case_sensitive.setText("Aa")
        self.case_sensitive.setToolTip("match case")
        self.layout.addWidget(self.case_sensitive, 0, 4)

        self.whole_word = QToolButton()
        self.whole_word.setCheckable(True)
        whole_word_icon = QIcon(":/icons/wholeWord.png")
        if whole_word_icon.isNull():
            whole_word_icon = QIcon.fromTheme("edit-select-all")
        self.whole_word.setIcon(whole_word_icon)
        if whole_word_icon.isNull():
            self.whole_word.setText("W")
        self.whole_word.setToolTip("match whole word")
        self.layout.addWidget(self.whole_word, 0, 5)

        self.hide_button = QToolButton()
        close_find_icon = QIcon(":/icons/closeFind.png")
        if close_find_icon.isNull():
            close_find_icon = QIcon.fromTheme("window-close")
        self.hide_button.setIcon(close_find_icon)
        if close_find_icon.isNull():
            self.hide_button.setText("×")
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
        self.find_next_requested.emit(self.text_search.text())

    def _replace_pressed(self) -> None:
        """Replace the current match with the replacement text."""
        self.replace_requested.emit(self.text_search.text(), self.replace.text())

    def _replace_all_pressed(self) -> None:
        """Replace all occurrences of the search text with the replacement text."""
        self.replace_all_requested.emit(self.text_search.text(), self.replace.text())
