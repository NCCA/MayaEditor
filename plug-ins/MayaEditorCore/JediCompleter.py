#!/usr/bin/env python3
"""Custom Jedi autocomplete popup for MayaEditor."""

from __future__ import annotations

import sys
import signal
import threading
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt, Signal  # type: ignore[import-not-found]
from PySide6.QtGui import QKeyEvent  # type: ignore[import-not-found]
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QWidget  # type: ignore[import-not-found]

try:
    from jedi import Interpreter, Project, Script  # type: ignore

    _JEDI_AVAILABLE = True
except Exception:
    Script = None  # type: ignore
    Project = None  # type: ignore
    Interpreter = None  # type: ignore
    _JEDI_AVAILABLE = False

# Cache the Jedi project to avoid recreating it every time
_jedi_project = None
_EXEC_TIMEOUT_SECONDS = 2


def _get_jedi_project() -> Optional[Any]:
    """Get or create a Jedi project configured with Maya's sys.path."""
    global _jedi_project
    if _jedi_project is None and _JEDI_AVAILABLE and Project is not None:
        # Create a project with Maya's current sys.path
        # This allows Jedi to find Maya modules
        _jedi_project = Project(path=".", added_sys_path=sys.path)

    return _jedi_project


def _exec_code_with_timeout(code: str, namespace: Dict[str, Any]) -> Dict[str, Any]:
    """Execute code with a short timeout guard.

    Uses SIGALRM when available and safe, otherwise falls back to a watchdog
    thread so completion lookup never blocks indefinitely.
    """
    if not code.strip():
        return namespace

    can_use_signal = (
        sys.platform != "darwin"
        and threading.current_thread() is threading.main_thread()
        and hasattr(signal, "SIGALRM")
    )

    if can_use_signal:
        def _handle_timeout(signum, frame) -> None:  # type: ignore[no-untyped-def]
            raise TimeoutError("exec timed out")

        previous_handler = signal.getsignal(signal.SIGALRM)
        try:
            signal.signal(signal.SIGALRM, _handle_timeout)
            signal.alarm(_EXEC_TIMEOUT_SECONDS)
            exec(code, namespace)
            return namespace
        except TimeoutError:
            return {}
        except Exception:
            return {}
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, previous_handler)

    finished = threading.Event()
    result: Dict[str, Any] = {}

    def _runner() -> None:
        try:
            exec(code, namespace)
            result.update(namespace)
        except Exception:
            result.clear()
        finally:
            finished.set()

    worker = threading.Thread(target=_runner, daemon=True)
    worker.start()
    worker.join(_EXEC_TIMEOUT_SECONDS)

    if not finished.is_set():
        return {}

    return result or namespace


class JediCompletionPopup(QListWidget):
    """Custom autocomplete popup using Jedi for Python code completion.

    This is a simpler alternative to QCompleter that gives us full control
    over the popup behavior in Maya's environment.
    """

    completion_selected = Signal(str)  # Emitted when user selects a completion

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize the completion popup.

        Parameters
        ----------
        parent : QWidget, optional
            Parent widget (typically the text editor)
        """
        super().__init__(parent)

        # Configure as a popup window
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setFocusPolicy(Qt.NoFocus)

        # Dark mode styling
        self.setStyleSheet("""
            QListWidget {
                background-color: #2b2b2b;
                color: #d4d4d4;
                border: 2px solid #007acc;
                selection-background-color: #007acc;
                selection-color: #ffffff;
                font-size: 12px;
                padding: 2px;
            }
            QListWidget::item {
                padding: 4px 8px;
                border-bottom: 1px solid #3c3c3c;
            }
            QListWidget::item:hover {
                background-color: #3c3c3c;
            }
        """)

        # Set size constraints
        self.setMinimumWidth(200)
        self.setMaximumWidth(400)
        self.setMaximumHeight(300)

        # Connect selection signal
        self.itemClicked.connect(self._on_item_clicked)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        """Handle item selection from the popup.

        Parameters
        ----------
        item : QListWidgetItem
            The selected item
        """
        text = item.text()
        self.completion_selected.emit(text)
        self.hide()

    def show_completions(self, editor: QWidget, completions: List[str]) -> None:
        """Show the completion popup with the given items.

        Parameters
        ----------
        editor : QWidget
            The text editor widget
        completions : List[str]
            List of completion strings to display
        """
        if not completions:
            self.hide()
            return

        # Clear and populate
        self.clear()
        for comp in completions[:50]:  # Limit to 50 items for performance
            self.addItem(comp)

        # Select first item
        if self.count() > 0:
            self.setCurrentRow(0)

        # Calculate position below cursor
        cursor_rect = editor.cursorRect()
        global_pos = editor.mapToGlobal(cursor_rect.bottomLeft())

        # Adjust size based on content
        self.adjustSize()

        # Position the popup
        self.move(global_pos)

        # Show it
        self.show()
        self.raise_()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle key events in the popup.

        Parameters
        ----------
        event : QKeyEvent
            The key event
        """
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            # Accept current selection
            current_item = self.currentItem()
            if current_item:
                self._on_item_clicked(current_item)
            event.accept()
        elif event.key() == Qt.Key_Escape:
            # Cancel
            self.hide()
            event.accept()
        elif event.key() in (Qt.Key_Up, Qt.Key_Down):
            # Navigate
            super().keyPressEvent(event)
        else:
            # Send other keys back to the editor
            self.hide()
            if self.parent():
                self.parent().keyPressEvent(event)


def get_jedi_completions(source: str, line: int, col: int, filename: str = "") -> List[str]:
    """Get completions from Jedi.

    Parameters
    ----------
    source : str
        The source code
    line : int
        Line number (1-based)
    col : int
        Column number (0-based)
    filename : str, optional
        Filename for context

    Returns
    -------
    List[str]
        List of completion strings
    """
    if not _JEDI_AVAILABLE or Script is None:
        return []

    try:
        # Get the project configured with Maya's sys.path
        project = _get_jedi_project()

        # Get current line for context
        context_lines = source.split("\n")
        if line - 1 < len(context_lines):
            current_line = context_lines[line - 1]
        else:
            current_line = ""

        combined_namespace: Dict[str, Any] = {}

        # Execute the code up to the cursor to get real runtime context
        # This allows Jedi to see actual imported modules
        try:
            # Create a namespace and execute imports
            namespace: Dict[str, Any] = {}

            # Execute all lines before the current line to populate namespace
            lines_before = context_lines[: line - 1]
            code_before = "\n".join(lines_before)

            if code_before.strip():
                namespace = _exec_code_with_timeout(code_before, namespace)

            # Add Maya's main namespace as well
            import __main__

            combined_namespace = {**__main__.__dict__, **namespace}

            # Use Interpreter mode with executed namespace
            assert Interpreter is not None
            interpreter = Interpreter(source, namespaces=[combined_namespace], project=project)
            completions = interpreter.complete(line, col)
        except Exception:
            # Fallback to Script mode
            assert Script is not None
            script = Script(source, path=filename, project=project)
            completions = script.complete(line, col)

        # Fallback: If Jedi returns few/no completions but we're completing on a module,
        # use dir() directly (better for dynamically generated modules like maya.cmds)
        if len(completions) < 10 and current_line and "." in current_line:
            # Check if we're completing on a known object
            parts = current_line.split(".")
            if len(parts) >= 2:
                obj_name = parts[0].strip()
                if obj_name in combined_namespace:
                    obj = combined_namespace[obj_name]
                    # If it's a module or has many attributes, use dir()
                    if hasattr(obj, "__name__") or len(dir(obj)) > 50:
                        # Get all attributes
                        all_attrs = dir(obj)

                        # Filter to callables (functions) and non-private
                        callables = []
                        non_callables = []
                        for attr in all_attrs:
                            if attr.startswith("_"):
                                continue
                            try:
                                attr_obj = getattr(obj, attr)
                                if callable(attr_obj):
                                    callables.append(attr)
                                else:
                                    non_callables.append(attr)
                            except:
                                # If we can't get it, skip it
                                pass

                        # Prefer callables but include non-callables too
                        direct_completions = callables + non_callables

                        # If user has typed something after the dot, filter by prefix
                        if len(parts) > 1 and parts[-1].strip():
                            prefix = parts[-1].strip()
                            direct_completions = [c for c in direct_completions if c.startswith(prefix)]

                        if len(direct_completions) > len(completions):
                            return direct_completions

        names = []
        for c in completions:
            nm = getattr(c, "name", None) or getattr(c, "complete", None)
            if isinstance(nm, str) and nm not in names:
                # Filter out private/dunder unless explicitly typed
                if nm.startswith("__") and current_line and not current_line.strip().endswith("__"):
                    continue
                names.append(nm)

        return names
    except Exception:
        # Silently fail
        return []
