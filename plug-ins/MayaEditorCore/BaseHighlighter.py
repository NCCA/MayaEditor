"""Shared syntax highlighter base for MayaEditor."""

from typing import Any, Callable, Dict, Sequence, Tuple

from PySide6.QtCore import QRegularExpression  # type: ignore
from PySide6.QtGui import QBrush, QColor, QFont, QSyntaxHighlighter, QTextCharFormat  # type: ignore


class BaseHighlighter(QSyntaxHighlighter):
    def _create_format(self, style_colour: str, style: str = "") -> QTextCharFormat:
        fmt = QTextCharFormat(); colour = QColor(); colour.setNamedColor(style_colour); fmt.setForeground(QBrush(colour)); fmt.setFontWeight(QFont.Bold) if "bold" in style else None; fmt.setFontItalic(True) if "italic" in style else None; return fmt

    def _create_format_rgb(self, style_colour: QColor, style: str = "") -> QTextCharFormat:
        fmt = QTextCharFormat(); fmt.setForeground(QBrush(style_colour)); fmt.setFontWeight(QFont.Bold) if "bold" in style else None; fmt.setFontItalic(True) if "italic" in style else None; return fmt

    def __init__(self, parent: Any, keywords: Sequence[str], operators: Sequence[str], braces: Sequence[str], maya_commands_func: Callable[[], Sequence[str]]) -> None:
        super().__init__(parent)
        self.styles: Dict[str, QTextCharFormat] = {"keyword": self._create_format_rgb(QColor(255, 166, 87)), "operator": self._create_format_rgb(QColor(255, 166, 87)), "brace": self._create_format("darkGray"), "defclass": self._create_format_rgb(QColor(255, 166, 87)), "deffunc": self._create_format_rgb(QColor(121, 192, 234)), "string": self._create_format_rgb(QColor(165, 214, 255)), "string2": self._create_format_rgb(QColor(165, 214, 255)), "comment": self._create_format_rgb(QColor("Gray")), "self": self._create_format_rgb(QColor(121, 192, 255)), "numbers": self._create_format("GhostWhite"), "maya": self._create_format("SpringGreen")}
        self.tri_single: Tuple[QRegularExpression, int, QTextCharFormat] = (QRegularExpression("'''") , 1, self.styles["string2"])
        self.tri_double: Tuple[QRegularExpression, int, QTextCharFormat] = (QRegularExpression('"""'), 2, self.styles["string2"])
        self.mayaCmds = list(maya_commands_func())
        rules = [(rf"\b{w}\b", 0, self.styles["keyword"]) for w in keywords] + [(rf"{o}", 0, self.styles["operator"]) for o in operators] + [(rf"{b}", 0, self.styles["brace"]) for b in braces] + [(r"\bself\b", 0, self.styles["self"]), (r'"[^"\\]*(\\.[^"\\]*)*"', 0, self.styles["string"]), (r"'[^'\\]*(\\.[^'\\]*)*'", 0, self.styles["string"]), (r"\b[+-]?[0-9]+[lL]?\b", 0, self.styles["numbers"]), (r"\b[+-]?0[xX][0-9A-Fa-f]+[lL]?\b", 0, self.styles["numbers"]), (r"\b[+-]?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\b", 0, self.styles["numbers"])]
        self.rules = [(QRegularExpression(pattern), index, fmt) for pattern, index, fmt in rules]

    def highlightBlock(self, textBlock: str) -> None:
        for expr, nth, syFormat in self.rules:
            match = expr.match(textBlock)
            while match.hasMatch():
                index = match.capturedStart(nth)
                length = len(match.captured(nth))
                self.setFormat(index, length, syFormat)
                match = expr.match(textBlock, index + length)
        self.setCurrentBlockState(0)
        if not self.match_multiline(textBlock, *self.tri_single):
            self.match_multiline(textBlock, *self.tri_double)

    def match_multiline(self, textBlock: str, delimiter: QRegularExpression, in_state: int, style: QTextCharFormat) -> bool:
        if self.previousBlockState() == in_state: start = 0; add = 0
        else:
            match = delimiter.match(textBlock)
            if not match.hasMatch(): start = -1; add = 0
            else: start = match.capturedStart(); add = match.capturedLength()
        while start >= 0:
            end_match = delimiter.match(textBlock, start + add)
            if end_match.hasMatch(): end = end_match.capturedStart(); length = end - start + add + end_match.capturedLength(); self.setCurrentBlockState(0)
            else: self.setCurrentBlockState(in_state); length = len(textBlock) - start + add
            self.setFormat(start, length, style)
            next_match = delimiter.match(textBlock, start + length)
            if not next_match.hasMatch(): break
            start = next_match.capturedStart(); add = next_match.capturedLength()
        return bool(self.currentBlockState() == in_state)
