"""Syntax highlighter for MEL source code."""

from typing import Any, List

import maya.cmds as cmds  # type: ignore

from .BaseHighlighter import BaseHighlighter  # type: ignore


class MelHighlighter(BaseHighlighter):
    keywords: List[str] = ["and", "as", "case", "catch", "continue", "do", "else", "exit", "false", "for", "from", "if", "in", "local", "not", "of", "off", "on", "or", "random", "return", "then", "throw", "to", "true", "try", "when", "where", "while", "with", "vector", "string", "float", "int", "array", "proc", "global"]
    operators: List[str] = ["=", "==", "!=", "<", "<=", "[^>]>", ">=", "\\+", "-", "\\*", "/", "//", "\\%", "\\*\\*", "\\+=", "-=", "\\*=", "/=", "\\%=", "\\^", "\\|", "\\&", "\\~", "[^>]>>", "<<"]
    braces: List[str] = ["\\{", "\\}", "\\(", "\\)", "\\[", "\\]"]
    mayaCmds: List[str] = cmds.help("[a-z]*", list=True)

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent, self.keywords, self.operators, self.braces, lambda: self.mayaCmds)
        self.rules += [(r"\bproc\b\s*(\w+)", 1, self.styles["deffunc"]), (r"//[^\n]*", 0, self.styles["comment"])]
