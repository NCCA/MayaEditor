"""Component tests for BaseHighlighter."""

import pytest
from PySide6.QtGui import QColor, QTextCharFormat, QFont, QTextDocument

from MayaEditorCore.BaseHighlighter import BaseHighlighter


@pytest.mark.component
class TestBaseHighlighter:
    """Test suite for BaseHighlighter."""

    @pytest.fixture
    def highlighter(self, qapp):
        """Create a minimal BaseHighlighter instance."""
        doc = QTextDocument()
        keywords = ["test", "keyword"]
        operators = ["=", "=="]
        braces = ["\\{", "\\}"]
        maya_commands_func = lambda: ["polySphere", "polyCube"]

        return BaseHighlighter(doc, keywords, operators, braces, maya_commands_func)

    def test_create_format_with_color_name(self, highlighter):
        """Test _create_format with named color."""
        fmt = highlighter._create_format("#FF0000", "")

        assert isinstance(fmt, QTextCharFormat)
        assert fmt.foreground().color() == QColor("#FF0000")

    def test_create_format_with_bold_style(self, highlighter):
        """Test _create_format with bold style."""
        fmt = highlighter._create_format("#000000", "bold")

        assert fmt.fontWeight() == QFont.Bold

    def test_create_format_with_italic_style(self, highlighter):
        """Test _create_format with italic style."""
        fmt = highlighter._create_format("#000000", "italic")

        assert fmt.fontItalic() is True

    def test_create_format_rgb_with_qcolor(self, highlighter):
        """Test _create_format_rgb with QColor."""
        color = QColor(255, 0, 0)
        fmt = highlighter._create_format_rgb(color, "bold")

        assert fmt.foreground().color() == color
        assert fmt.fontWeight() == QFont.Bold

    def test_styles_dictionary_created(self, highlighter):
        """Test that styles dictionary is created."""
        assert isinstance(highlighter.styles, dict)
        assert len(highlighter.styles) > 0
        # Should have common style keys
        assert "keyword" in highlighter.styles
        assert "operator" in highlighter.styles
