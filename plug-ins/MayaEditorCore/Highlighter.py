import re
import sys

import maya.cmds as cmds
from PySide2.QtCore import QRegExp, Qt
from PySide2.QtGui import *
from PySide2.QtWidgets import *


def _create_format(style_colour, style=""):
    colour = QColor()
    colour.setNamedColor(style_colour)

    new_format = QTextCharFormat()
    new_format.setForeground(colour)
    if "bold" in style:
        new_format.setFontWeight(QFont.Bold)
    if "italic" in style:
        new_format.setFontItalic(True)

    return new_format


class Highlighter(QSyntaxHighlighter):
    # Python keywords
    keywords = [
        "and",
        "assert",
        "break",
        "class",
        "continue",
        "def",
        "del",
        "elif",
        "else",
        "except",
        "exec",
        "finally",
        "for",
        "from",
        "global",
        "if",
        "import",
        "in",
        "is",
        "lambda",
        "not",
        "or",
        "pass",
        "print",
        "raise",
        "return",
        "try",
        "while",
        "yield",
        "None",
        "True",
        "False",
    ]

    # Python operators
    operators = [
        "=",
        # Comparison
        "==",
        "!=",
        "<",
        "<=",
        "[^>]>",
        ">=",
        # Arithmetic
        "\+",
        "-",
        "\*",
        "/",
        "//",
        "\%",
        "\*\*",
        # In-place
        "\+=",
        "-=",
        "\*=",
        "/=",
        "\%=",
        # Bitwise
        "\^",
        "\|",
        "\&",
        "\~",
        "[^>]>>",
        "<<",
    ]

    # Python braces
    braces = [
        "\{",
        "\}",
        "\(",
        "\)",
        "\[",
        "\]",
    ]

    mayaCmds = cmds.help("[a-z]*", list=True, lng="Python")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.styles = {
            "keyword": _create_format("DeepSkyBlue"),
            "operator": _create_format("DeepPink "),
            "brace": _create_format("darkGray"),
            "defclass": _create_format("MistyRose"),
            "string": _create_format("red"),
            "string2": _create_format("yellow"),
            "comment": _create_format("Gray"),
            "self": _create_format("Plum"),
            "numbers": _create_format("GhostWhite"),
            "maya": _create_format("SpringGreen"),
        }
        self.tri_single = (QRegExp("'''"), 1, self.styles["string2"])
        self.tri_double = (QRegExp('"""'), 2, self.styles["string2"])

        rules = []
        # Keyword, operator, and brace rules
        rules += [
            (r"\b%s\b" % w, 0, self.styles["keyword"]) for w in Highlighter.keywords
        ]
        # rules += [(r'.%s.' % w, 0, self.styles['maya'])
        #          for w in PythonHighlighter.mayaCmds]
        rules += [
            (r"%s" % o, 0, self.styles["operator"]) for o in Highlighter.operators
        ]
        rules += [(r"%s" % b, 0, self.styles["brace"]) for b in Highlighter.braces]

        # All other rules
        rules += [
            # 'self'
            (r"\bself\b", 0, self.styles["self"]),
            # Double-quoted string, possibly containing escape sequences
            (r'"[^"\\]*(\\.[^"\\]*)*"', 0, self.styles["string"]),
            # Single-quoted string, possibly containing escape sequences
            (r"'[^'\\]*(\\.[^'\\]*)*'", 0, self.styles["string"]),
            # 'def' followed by an identifier
            (r"\bdef\b\s*(\w+)", 1, self.styles["defclass"]),
            # 'class' followed by an identifier
            (r"\bclass\b\s*(\w+)", 1, self.styles["defclass"]),
            # From '#' until a newline
            (r"#[^\n]*", 0, self.styles["comment"]),
            # Numeric literals
            (r"\b[+-]?[0-9]+[lL]?\b", 0, self.styles["numbers"]),
            (r"\b[+-]?0[xX][0-9A-Fa-f]+[lL]?\b", 0, self.styles["numbers"]),
            (
                r"\b[+-]?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\b",
                0,
                self.styles["numbers"],
            ),
        ]

        # Build a qt.QRegExp for each pattern
        self.rules = [(QRegExp(pat), index, fmt) for (pat, index, fmt) in rules]

    def highlightBlock(self, textBlock):
        """Apply syntax highlighting to the given block of text."""
        data = self.currentBlockUserData()
        if data:
            try:
                if data["type"] == TextBlock.TYPE_MESSAGE:
                    self.setFormat(0, len(textBlock), _create_format("grey"))
                    return
                if data["type"] == TextBlock.TYPE_OUTPUT_MSG:
                    self.setFormat(0, len(textBlock), _create_format("red"))
                    return
                if data["type"] not in TextBlock.CODE_TYPES:
                    return
            except:
                pass

        # Do other syntax syFormatting
        for expr, nth, syFormat in self.rules:
            index = expr.indexIn(textBlock, 0)

            while index >= 0:
                # We actually want the index of the nth match
                index = expr.pos(nth)
                length = len(expr.cap(nth))

                self.setFormat(index, length, syFormat)
                index = expr.indexIn(textBlock, index + length)

        self.setCurrentBlockState(0)

        # Do multi-line strings
        in_multiline = self.match_multiline(textBlock, *self.tri_single)
        if not in_multiline:
            in_multiline = self.match_multiline(textBlock, *self.tri_double)

    def match_multiline(self, textBlock, delimiter, in_state, style):
        """Do highlighting of multi-line strings. ``delimiter`` should be a
        ``qt.QRegExp`` for triple-single-quotes or triple-double-quotes, and
        ``in_state`` should be a unique integer to represent the corresponding
        state changes when inside those strings. Returns True if we're still
        inside a multi-line string when this function is finished.
        """
        # If inside triple-single quotes, start at 0
        if self.previousBlockState() == in_state:
            start = 0
            add = 0
        # Otherwise, look for the delimiter on this line
        else:
            start = delimiter.indexIn(textBlock)
            # Move past this match
            add = delimiter.matchedLength()

        # As long as there's a delimiter match on this line...
        while start >= 0:
            # Look for the ending delimiter
            end = delimiter.indexIn(textBlock, start + add)
            # Ending delimiter on this line?
            if end >= add:
                length = end - start + add + delimiter.matchedLength()
                self.setCurrentBlockState(0)
            # No; multi-line string
            else:
                self.setCurrentBlockState(in_state)
                length = textBlock.length() - start + add
            # Apply syFormatting
            self.setFormat(start, length, style)
            # Look for the next match
            start = delimiter.indexIn(textBlock, start + length)

        # Return True if still inside a multi-line string, False otherwise
        if self.currentBlockState() == in_state:
            return True
        else:
            return False
