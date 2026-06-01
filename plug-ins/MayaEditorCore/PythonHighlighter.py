"""Syntax highlighter for Python source code."""

from typing import Any, List

import maya.cmds as cmds  # type: ignore

from PySide6.QtCore import QRegularExpression  # type: ignore

from .BaseHighlighter import BaseHighlighter  # type: ignore


class PythonHighlighter(BaseHighlighter):
    keywords: List[str] = ["and", "assert", "break", "class", "continue", "def", "del", "elif", "else", "except", "exec", "finally", "for", "from", "global", "if", "import", "in", "is", "lambda", "not", "or", "pass", "print", "raise", "return", "try", "while", "yield", "None", "True", "False"]
    operators: List[str] = ["=", "==", "!=", "<", "<=", "[^>]>", ">=", "\\+", "-", "\\*", "/", "//", "\\%", "\\*\\*", "\\+=", "-=", "\\*=", "/=", "\\%=", "\\^", "\\|", "\\&", "\\~", "[^>]>>", "<<"]
    braces: List[str] = ["\\{", "\\}", "\\(", "\\)", "\\[", "\\]"]
    mayaCmds: List[str] = cmds.help("[a-z]*", list=True, lng="Python")

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent, self.keywords, self.operators, self.braces, lambda: self.mayaCmds)
        self.rules += [(QRegularExpression(r"\bdef\b\s*(\w+)"), 1, self.styles["deffunc"]), (QRegularExpression(r"\bclass\b\s*(\w+)"), 1, self.styles["defclass"]), (QRegularExpression(r"#[^\n]*"), 0, self.styles["comment"])]
