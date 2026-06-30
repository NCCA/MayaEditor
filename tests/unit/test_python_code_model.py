"""Unit tests for the AST-based code model logic in PythonTextEdit.

PythonTextEdit is a QWidget, which crashes Maya standalone when instantiated.
We borrow extract_classes_and_functions and generate_code_model onto a minimal
stub so the pure AST logic can be tested without a QApplication.
"""

import ast
import types
from unittest.mock import MagicMock

import pytest

from MayaEditorCore.PythonTextEdit import PythonTextEdit, class_model_data, code_model_data


class _StubEditor:
    """Minimal stub that supports the code-model methods without any Qt setup.

    extract_classes_and_functions only uses `self` for its own recursive call,
    so borrowing the unbound method onto a plain object is sufficient.
    """

    extract_classes_and_functions = PythonTextEdit.extract_classes_and_functions
    generate_code_model = PythonTextEdit.generate_code_model


def _make_stub(source: str) -> _StubEditor:
    """Return a stub whose generate_code_model reads from *source*."""
    stub = _StubEditor()
    stub.code_model = []
    mock_doc = MagicMock()
    mock_doc.toRawText.return_value = source
    stub.document = MagicMock(return_value=mock_doc)
    stub.code_model_changed = MagicMock()
    return stub


def _extract(source: str) -> list:
    """Parse *source* and run extract_classes_and_functions; return result list."""
    stub = _StubEditor()
    tree = ast.parse(source)
    result: list = []
    stub.extract_classes_and_functions(tree, result)
    return result


# ---------------------------------------------------------------------------
# extract_classes_and_functions — direct AST tests
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.maya
class TestExtractClassesAndFunctions:

    def test_empty_module_gives_empty_list(self):
        assert _extract("") == []

    def test_top_level_function(self):
        result = _extract("def foo():\n    pass\n")
        assert len(result) == 1
        assert isinstance(result[0], code_model_data)
        assert result[0].type == "function"
        assert result[0].name == "foo"
        assert result[0].line_number == 1

    def test_top_level_class(self):
        result = _extract("class MyClass:\n    pass\n")
        assert len(result) == 1
        assert isinstance(result[0], dict)
        key = next(iter(result[0]))
        assert isinstance(key, class_model_data)
        assert key.name == "MyClass"
        assert key.line_number == 1

    def test_class_method_labelled_method(self):
        result = _extract("class A:\n    def m(self):\n        pass\n")
        cls_entry = result[0]
        key = next(iter(cls_entry))
        methods = cls_entry[key]
        assert len(methods) == 1
        assert methods[0].type == "method"
        assert methods[0].name == "m"

    def test_multiple_methods_in_class(self):
        code = (
            "class A:\n"
            "    def __init__(self):\n"
            "        pass\n"
            "    def run(self):\n"
            "        pass\n"
        )
        result = _extract(code)
        key = next(iter(result[0]))
        methods = result[0][key]
        assert len(methods) == 2
        assert {m.name for m in methods} == {"__init__", "run"}

    def test_multiple_top_level_functions(self):
        result = _extract("def foo():\n    pass\n\ndef bar():\n    pass\n")
        assert len(result) == 2
        assert {e.name for e in result} == {"foo", "bar"}

    def test_class_and_function_at_top_level(self):
        code = "class A:\n    pass\n\ndef standalone():\n    pass\n"
        result = _extract(code)
        assert len(result) == 2
        kinds = {type(e).__name__ for e in result}
        assert "dict" in kinds
        assert "code_model_data" in kinds

    def test_nested_class(self):
        source = (
            "class Outer:\n"
            "    class Inner:\n"
            "        def inner_method(self):\n"
            "            pass\n"
        )
        result = _extract(source)
        outer_key = next(iter(result[0]))
        assert outer_key.name == "Outer"
        outer_children = result[0][outer_key]
        inner_key = next(iter(outer_children[0]))
        assert inner_key.name == "Inner"
        inner_methods = outer_children[0][inner_key]
        assert inner_methods[0].name == "inner_method"
        assert inner_methods[0].type == "method"

    def test_line_number_reflects_source_position(self):
        result = _extract("\n\ndef late():\n    pass\n")
        assert result[0].line_number == 3

    def test_class_line_number(self):
        result = _extract("\nclass Late:\n    pass\n")
        key = next(iter(result[0]))
        assert key.line_number == 2

    def test_imports_and_assignments_excluded(self):
        result = _extract("import os\nx = 1\ny = 'hello'\n")
        assert result == []

    def test_function_body_not_traversed(self):
        """Functions defined inside other functions should not appear at top level."""
        code = "def outer():\n    def inner():\n        pass\n"
        result = _extract(code)
        # Only outer should appear; inner is not visited because we only iterate
        # node_to_traverse.body (top-level nodes of each scope)
        assert len(result) == 1
        assert result[0].name == "outer"


# ---------------------------------------------------------------------------
# generate_code_model — tests via stub with mocked Qt document
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.maya
class TestGenerateCodeModel:

    def test_empty_source(self):
        stub = _make_stub("")
        stub.generate_code_model()
        assert stub.code_model == []

    def test_function_populates_model(self):
        stub = _make_stub("def foo():\n    pass\n")
        stub.generate_code_model()
        assert len(stub.code_model) == 1
        assert stub.code_model[0].name == "foo"

    def test_class_populates_model(self):
        stub = _make_stub("class MyClass:\n    pass\n")
        stub.generate_code_model()
        key = next(iter(stub.code_model[0]))
        assert key.name == "MyClass"

    def test_syntax_error_preserves_previous_model(self):
        """On SyntaxError, generate_code_model returns early without resetting."""
        stub = _make_stub("def foo():\n    pass\n")
        stub.generate_code_model()
        previous = list(stub.code_model)

        # Switch document to invalid Python
        stub.document.return_value.toRawText.return_value = "def (broken:\n"
        stub.generate_code_model()

        assert stub.code_model == previous

    def test_syntax_error_does_not_emit_signal(self):
        stub = _make_stub("def (broken:\n")
        stub.generate_code_model()
        stub.code_model_changed.emit.assert_not_called()

    def test_valid_code_emits_signal(self):
        stub = _make_stub("def foo():\n    pass\n")
        stub.generate_code_model()
        stub.code_model_changed.emit.assert_called()

    def test_second_call_resets_model(self):
        stub = _make_stub("def foo():\n    pass\ndef bar():\n    pass\n")
        stub.generate_code_model()
        assert len(stub.code_model) == 2

        stub.document.return_value.toRawText.return_value = "def only():\n    pass\n"
        stub.generate_code_model()
        assert len(stub.code_model) == 1
        assert stub.code_model[0].name == "only"

    def test_qt_paragraph_separator_handled(self):
        """Qt uses U+2029 as paragraph separator; generate_code_model replaces it."""
        # Source with Qt paragraph separators instead of \n
        source = "def foo():     pass "
        stub = _make_stub(source)
        stub.generate_code_model()
        assert len(stub.code_model) == 1
        assert stub.code_model[0].name == "foo"
