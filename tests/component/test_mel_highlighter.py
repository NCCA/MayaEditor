"""Component tests for MelHighlighter."""

import pytest
from PySide6.QtGui import QTextDocument

from MayaEditorCore.MelHighlighter import MelHighlighter


@pytest.mark.component
@pytest.mark.maya
class TestMelHighlighter:
    """Test suite for MEL syntax highlighter."""

    @pytest.fixture
    def document(self, qapp):
        """Provide a QTextDocument for highlighter testing."""
        return QTextDocument()

    @pytest.fixture
    def highlighter(self, document):
        """Provide a MelHighlighter instance."""
        return MelHighlighter(document)

    def test_highlighter_initializes_with_maya_commands(self, highlighter):
        """Test that highlighter loads Maya command list."""
        assert len(highlighter.mayaCmds) > 0
        assert "polySphere" in highlighter.mayaCmds
        assert "polyCube" in highlighter.mayaCmds

    def test_highlighter_has_mel_keywords(self, highlighter):
        """Test that MEL-specific keywords are defined."""
        mel_keywords = ["proc", "global", "string", "float", "int", "vector"]
        for keyword in mel_keywords:
            assert keyword in highlighter.keywords

    def test_proc_definition_pattern(self, highlighter):
        """Test that proc definition pattern exists."""
        patterns = [rule[0].pattern() for rule in highlighter.rules]
        # Should have a pattern for "proc procedureName"
        assert any("proc" in p for p in patterns)

    def test_comment_pattern(self, highlighter):
        """Test that MEL comment pattern exists."""
        patterns = [rule[0].pattern() for rule in highlighter.rules]
        # MEL comments start with //
        assert any("//" in p for p in patterns)

    def test_highlight_block_processes_mel_code(self, highlighter, document):
        """Test that highlightBlock processes MEL code without errors."""
        mel_code = 'proc string createCube() { return "cube"; }'
        document.setPlainText(mel_code)

        block = document.firstBlock()
        highlighter.highlightBlock(block.text())
