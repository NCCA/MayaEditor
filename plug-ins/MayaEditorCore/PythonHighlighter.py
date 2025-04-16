# Copyright (C) 2022  Jonathan Macey
# License: GNU GPL v3 or later

from typing import Any, Dict

import maya.cmds as cmds
from qtpy.QtCore import QRegularExpression, Qt
from qtpy.QtGui import *
from qtpy.QtWidgets import *

def _create_format(style_colour: str, style: str = "") -> QTextCharFormat:
    colour = QColor()
    colour.setNamedColor(style_colour)
    new_format = QTextCharFormat()
    new_format.setForeground(QBrush(colour))
    if "bold" in style:
        new_format.setFontWeight(QFont.Bold)
    if "italic" in style:
        new_format.setFontItalic(True)
    return new_format

def _create_format_rgb(style_colour: QColor, style: str = "") -> QTextCharFormat:
    new_format = QTextCharFormat()
    new_format.setForeground(QBrush(style_colour))
    if "bold" in style:
        new_format.setFontWeight(QFont.Bold)
    if "italic" in style:
        new_format.setFontItalic(True)
    return new_format

class PythonHighlighter(QSyntaxHighlighter):
    keywords = [
        "and", "assert", "break", "class", "continue", "def", "del", "elif", "else",
        "except", "exec", "finally", "for", "from", "global", "if", "import", "in",
        "is", "lambda", "not", "or", "pass", "print", "raise", "return", "try", "while",
        "yield", "None", "True", "False"
    ]

    operators = [
        "=", "==", "!=", "<", "<=", "[^>]>", ">=", "\\+", "-", "\\*", "/", "//", "\\%", "\\*\\*",
        "\\+=", "-=", "\\*=", "/=", "\\%=", "\\^", "\\|", "\\&", "\\~", "[^>]>>", "<<"
    ]

    braces = ["\\{", "\\}", "\\(", "\\)", "\\[", "\\]"]

    mayaCmds = cmds.help("[a-z]*", list=True, lng="Python")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.styles = {
            "keyword": _create_format_rgb(QColor(255, 166, 87)),
            "operator": _create_format_rgb(QColor(255, 166, 87)),
            "brace": _create_format("darkGray"),
            "defclass": _create_format_rgb(QColor(255, 166, 87)),
            "deffunc": _create_format_rgb(QColor(121, 192, 234)),
            "string": _create_format_rgb(QColor(165, 214, 255)),
            "string2": _create_format_rgb(QColor(165, 214, 255)),
            "comment": _create_format_rgb("Gray"),
            "self": _create_format_rgb(QColor(121, 192, 255)),
            "numbers": _create_format("GhostWhite"),
            "maya": _create_format("SpringGreen"),
        }

        self.tri_single = (QRegularExpression("'''"), 1, self.styles["string2"])
        self.tri_double = (QRegularExpression('"""'), 2, self.styles["string2"])

        rules = []
        rules += [(fr"\\b{w}\\b", 0, self.styles["keyword"]) for w in self.keywords]
        rules += [(o, 0, self.styles["operator"]) for o in self.operators]
        rules += [(b, 0, self.styles["brace"]) for b in self.braces]
        rules += [
            (r"\\bself\\b", 0, self.styles["self"]),
            (r'"[^"\\\\]*(\\\\.[^"\\\\]*)*"', 0, self.styles["string"]),
            (r"'[^'\\\\]*(\\\\.[^'\\\\]*)*'", 0, self.styles["string"]),
            (r"\\bdef\\b\\s*(\\w+)", 1, self.styles["deffunc"]),
            (r"\\bclass\\b\\s*(\\w+)", 1, self.styles["defclass"]),
            (r"#[^\\n]*", 0, self.styles["comment"]),
            (r"\\b[+-]?[0-9]+[lL]?\\b", 0, self.styles["numbers"]),
            (r"\\b[+-]?0[xX][0-9A-Fa-f]+[lL]?\\b", 0, self.styles["numbers"]),
            (r"\\b[+-]?[0-9]+(?:\\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\\b", 0, self.styles["numbers"]),
        ]

        self.rules = [(QRegularExpression(pat), index, fmt) for (pat, index, fmt) in rules]

    def highlightBlock(self, textBlock: str) -> None:
        for expr, nth, syFormat in self.rules:
            it = expr.globalMatch(textBlock)
            while it.hasNext():
                match = it.next()
                index = match.capturedStart(nth)
                length = len(match.captured(nth))
                self.setFormat(index, length, syFormat)

        self.setCurrentBlockState(0)

        in_multiline = self.match_multiline(textBlock, *self.tri_single)
        if not in_multiline:
            in_multiline = self.match_multiline(textBlock, *self.tri_double)

    def match_multiline(self, textBlock: str, delimiter: QRegularExpression, in_state, style):
        start_match = delimiter.match(textBlock)
        if self.previousBlockState() == in_state:
            start = 0
            add = 0
        elif start_match.hasMatch():
            start = start_match.capturedStart()
            add = start_match.capturedLength()
        else:
            return False

        while start >= 0:
            end_match = delimiter.match(textBlock, start + add)
            if end_match.hasMatch():
                end = end_match.capturedStart()
                length = end - start + add + end_match.capturedLength()
                self.setCurrentBlockState(0)
            else:
                self.setCurrentBlockState(in_state)
                length = len(textBlock) - start + add
            self.setFormat(start, length, style)
            next_match = delimiter.match(textBlock, start + length)
            if next_match.hasMatch():
                start = next_match.capturedStart()
                add = next_match.capturedLength()
            else:
                start = -1

        return self.currentBlockState() == in_state
