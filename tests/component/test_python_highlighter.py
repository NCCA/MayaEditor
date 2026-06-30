"""Component tests for PythonHighlighter (requires Maya for command list)."""

import pytest
from PySide6.QtGui import QTextDocument
from PySide6.QtCore import QRegularExpression

from MayaEditorCore.PythonHighlighter import PythonHighlighter


@pytest.mark.component
@pytest.mark.maya
class TestPythonHighlighter:
    """Test suite for Python syntax highlighter."""

    @pytest.fixture
    def document(self, qapp):
        """Provide a QTextDocument for highlighter testing."""
        return QTextDocument()

    @pytest.fixture
    def highlighter(self, document):
        """Provide a PythonHighlighter instance."""
        return PythonHighlighter(document)

    def test_highlighter_initializes_with_maya_commands(self, highlighter, maya_commands):
        """Test that highlighter loads Maya command list."""
        # The highlighter should have loaded Maya commands
        assert len(highlighter.mayaCmds) > 0
        assert "polySphere" in highlighter.mayaCmds
        assert "polyCube" in highlighter.mayaCmds
        assert "polyPlane" in highlighter.mayaCmds

    def test_highlighter_has_keyword_rules(self, highlighter):
        """Test that Python keywords are in highlighter rules."""
        # Check that keyword style exists
        keyword_style = highlighter.styles.get("keyword")
        assert keyword_style is not None

        # Rules should include patterns for keywords
        patterns = [rule[0].pattern() for rule in highlighter.rules]
        assert any("\\bdef\\b" in p for p in patterns)
        assert any("\\bclass\\b" in p for p in patterns)
        assert any("\\bif\\b" in p for p in patterns)

    def test_highlighter_has_comment_rules(self, highlighter):
        """Test that comment highlighting is configured."""
        patterns = [rule[0].pattern() for rule in highlighter.rules]
        assert any("#" in p for p in patterns)

    def test_highlighter_has_string_rules(self, highlighter):
        """Test that string highlighting is configured."""
        string_style = highlighter.styles.get("string")
        assert string_style is not None

    def test_highlight_block_processes_text(self, highlighter, document):
        """Test that highlightBlock processes text without errors."""
        test_code = "def test_function():\n    return True"
        document.setPlainText(test_code)

        # Should process without raising exceptions
        block = document.firstBlock()
        highlighter.highlightBlock(block.text())

    def test_maya_command_highlighting(self, highlighter):
        """Test that Maya commands are recognized."""
        # Maya commands should be in the highlighter's command list
        assert "polySphere" in highlighter.mayaCmds
        assert "polyCube" in highlighter.mayaCmds

        # The highlighter passes maya commands to BaseHighlighter
        # which should create rules for them
        assert len(highlighter.mayaCmds) > 100  # Maya has hundreds of commands

    def test_function_definition_pattern(self, highlighter):
        """Test that function definition pattern exists."""
        patterns = [rule[0].pattern() for rule in highlighter.rules]
        # Should have a pattern for "def function_name"
        assert any("def" in p and "\\w+" in p for p in patterns)

    def test_class_definition_pattern(self, highlighter):
        """Test that class definition pattern exists."""
        patterns = [rule[0].pattern() for rule in highlighter.rules]
        # Should have a pattern for "class ClassName"
        assert any("class" in p and "\\w+" in p for p in patterns)

    def test_styles_dictionary_complete(self, highlighter):
        """Test that all required styles are defined."""
        required_styles = [
            "keyword",
            "operator",
            "brace",
            "defclass",
            "deffunc",
            "string",
            "comment",
            "numbers",
        ]
        for style_name in required_styles:
            assert style_name in highlighter.styles, f"Missing style: {style_name}"
