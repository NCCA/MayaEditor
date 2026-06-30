"""Syntax highlighter for MEL source code."""

from typing import Any, List

import maya.cmds as cmds  # type: ignore

from PySide6.QtCore import QRegularExpression  # type: ignore

from .BaseHighlighter import BaseHighlighter  # type: ignore


class MelHighlighter(BaseHighlighter):
    keywords: List[str] = [
        "and",
        "as",
        "case",
        "catch",
        "continue",
        "do",
        "else",
        "exit",
        "false",
        "for",
        "from",
        "if",
        "in",
        "local",
        "not",
        "of",
        "off",
        "on",
        "or",
        "random",
        "return",
        "then",
        "throw",
        "to",
        "true",
        "try",
        "when",
        "where",
        "while",
        "with",
        "vector",
        "string",
        "float",
        "int",
        "array",
        "proc",
        "global",
    ]
    operators: List[str] = [
        "=",
        "==",
        "!=",
        "<",
        "<=",
        "[^>]>",
        ">=",
        "\\+",
        "-",
        "\\*",
        "/",
        "//",
        "\\%",
        "\\*\\*",
        "\\+=",
        "-=",
        "\\*=",
        "/=",
        "\\%=",
        "\\^",
        "\\|",
        "\\&",
        "\\~",
        "[^>]>>",
        "<<",
    ]
    braces: List[str] = ["\\{", "\\}", "\\(", "\\)", "\\[", "\\]"]
    _mayaCmds: List[str] | None = None  # Cached Maya commands

    @property
    def mayaCmds(self) -> List[str]:
        """Lazy-load Maya commands list on first access.

        This avoids calling cmds.help() at class definition time,
        which would fail before Maya standalone is initialized.
        """
        if MelHighlighter._mayaCmds is None:
            MelHighlighter._mayaCmds = cmds.help("[a-z]*", list=True)
        return MelHighlighter._mayaCmds

    @mayaCmds.setter
    def mayaCmds(self, value: List[str]) -> None:
        """Set Maya commands list (used by BaseHighlighter)."""
        MelHighlighter._mayaCmds = value

    def __init__(self, parent: Any = None) -> None:
        super().__init__(
            parent, self.keywords, self.operators, self.braces, lambda: self.mayaCmds
        )
        self.rules += [
            (QRegularExpression(r"\bproc\b\s*(\w+)"), 1, self.styles["deffunc"]),
            (QRegularExpression(r"//[^\n]*"), 0, self.styles["comment"]),
        ]
