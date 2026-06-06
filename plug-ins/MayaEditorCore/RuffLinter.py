# Copyright (C) 2022  Jonathan Macey
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
#  any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""Ruff-based Python linter running in a background QThread.

Usage
-----
Create one :class:`RuffLinter` per editor widget and call :meth:`RuffLinter.lint`
whenever the source changes.  Connect :attr:`RuffLinter.diagnostics_ready` to
receive the results on the Qt main thread.

    linter = RuffLinter(ruff_executable="ruff")
    linter.diagnostics_ready.connect(my_slot)
    linter.lint(source_text, "my_file.py")
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from collections import namedtuple
from typing import List, Optional

from PySide6.QtCore import QMutex, QObject, QThread, Signal, Slot

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public data type
# ---------------------------------------------------------------------------

Diagnostic = namedtuple(
    "Diagnostic",
    ["row", "col", "end_row", "end_col", "code", "message", "severity"],
)
"""A single lint diagnostic.

Attributes
----------
row : int
    1-based line number.
col : int
    1-based column number.
end_row : int
    1-based end line number (same as *row* when ruff does not supply it).
end_col : int
    1-based end column number.
code : str
    Rule code, e.g. ``"E501"``.
message : str
    Human-readable description.
severity : str
    ``"error"`` or ``"warning"``.
"""

# Ruff rule prefixes whose violations are treated as errors; everything else
# is a warning so the user can visually distinguish them.
_ERROR_PREFIXES = ("E", "F")


def _severity_for_code(code: str) -> str:
    """Map a ruff rule code to ``\"error\"`` or ``\"warning\"``.

    Parameters
    ----------
    code : str
        The ruff rule code (e.g. ``\"E501\"``).

    Returns
    -------
    str
        ``\"error\"`` if the code starts with an error prefix, else ``\"warning\"``.
    """
    for prefix in _ERROR_PREFIXES:
        if code.startswith(prefix):
            return "error"
    return "warning"


# ---------------------------------------------------------------------------
# Worker — runs in a dedicated QThread
# ---------------------------------------------------------------------------


class _RuffWorker(QObject):
    """Internal worker that runs ``ruff check`` as a subprocess.

    Do **not** instantiate this directly; use :class:`RuffLinter` instead.
    """

    diagnostics_ready = Signal(list)  # List[Diagnostic]
    _ruff_missing_warned: bool = False

    def __init__(self, ruff_executable: str, parent: Optional[QObject] = None) -> None:
        """Construct the worker.

        Parameters
        ----------
        ruff_executable : str
            Path to the ruff binary.
        parent : QObject or None
            Qt parent for lifetime management.
        """
        super().__init__(parent)
        self._ruff_exe = ruff_executable
        self._pending_source: Optional[str] = None
        self._pending_filename: str = "untitled.py"
        self._mutex = QMutex()

    @Slot(str)
    def set_executable(self, path: str) -> None:
        """Update the ruff executable path (called on the worker thread).

        Also resets the missing-warned flag so a newly configured path is
        tried even if a previous run already failed.

        Parameters
        ----------
        path : str
            Absolute path to the ruff binary.
        """
        self._ruff_exe = path
        _RuffWorker._ruff_missing_warned = False

    # Called from main thread via queued connection
    @Slot(str, str)
    def run_lint(self, source: str, filename: str) -> None:
        """Execute ``ruff check`` on *source* and emit results."""
        exe = self._ruff_exe or shutil.which("ruff") or "ruff"

        try:
            result = subprocess.run(
                [
                    exe,
                    "check",
                    "--output-format",
                    "json",
                    "--stdin-filename",
                    filename,
                    "-",
                ],
                input=source,
                capture_output=True,
                text=True,
                timeout=10,
            )
        except FileNotFoundError:
            if not _RuffWorker._ruff_missing_warned:
                _RuffWorker._ruff_missing_warned = True
                # Emit empty list — caller will display a one-time warning via
                # the diagnostics_ready signal carrying an empty list.
                logger.warning("ruff not found on PATH — linting disabled. Install ruff: pip install ruff")
            self.diagnostics_ready.emit([])
            return
        except subprocess.TimeoutExpired:
            self.diagnostics_ready.emit([])
            return

        diagnostics: List[Diagnostic] = []
        if result.stdout:
            try:
                items = json.loads(result.stdout)
                for item in items:
                    loc = item.get("location", {})
                    end_loc = item.get("end_location", loc)
                    code = item.get("code") or "?"
                    diagnostics.append(
                        Diagnostic(
                            row=loc.get("row", 1),
                            col=loc.get("column", 1),
                            end_row=end_loc.get("row", loc.get("row", 1)),
                            end_col=end_loc.get("column", loc.get("column", 1)),
                            code=code,
                            message=item.get("message", ""),
                            severity=_severity_for_code(code),
                        )
                    )
            except (json.JSONDecodeError, KeyError):
                logger.debug("Failed to parse ruff JSON output", exc_info=True)

        self.diagnostics_ready.emit(diagnostics)


# ---------------------------------------------------------------------------
# Public facade
# ---------------------------------------------------------------------------


class RuffLinter(QObject):
    """Facade that owns a background :class:`QThread` and exposes a simple API.

    Parameters
    ----------
    ruff_executable : str
        Path to the ``ruff`` binary.  If empty or ``None``, ``shutil.which``
        is used to locate it on ``PATH``.
    parent : QObject or None
        Qt parent for lifetime management.
    """

    diagnostics_ready = Signal(list)  # List[Diagnostic]

    # Internal signals — all cross-thread calls go through these so Qt
    # delivers them on the worker thread via queued connections.
    _request_lint = Signal(str, str)
    _request_set_exe = Signal(str)

    def __init__(
        self,
        ruff_executable: str = "",
        parent: Optional[QObject] = None,
    ) -> None:
        """Construct the RuffLinter facade and start the background thread.

        Parameters
        ----------
        ruff_executable : str
            Path to the ruff binary. If empty, ``shutil.which`` is used.
        parent : QObject or None
            Qt parent for lifetime management.
        """
        super().__init__(parent)

        self._thread = QThread(self)
        self._worker = _RuffWorker(ruff_executable)
        self._worker.moveToThread(self._thread)

        # Wire signals (auto-queued because worker is on a different thread)
        self._request_lint.connect(self._worker.run_lint)
        self._request_set_exe.connect(self._worker.set_executable)
        self._worker.diagnostics_ready.connect(self.diagnostics_ready)

        self._thread.start()

    def set_executable(self, path: str) -> None:
        """Update the ruff binary path on the worker thread.

        Safe to call from the main thread at any time.

        Parameters
        ----------
        path : str
            Absolute path to the ruff binary.
        """
        self._request_set_exe.emit(path)

    def lint(self, source: str, filename: str = "untitled.py") -> None:
        """Request a lint run for *source*.

        This method is safe to call from the Qt main thread.  The actual
        subprocess is executed in the background thread.

        Parameters
        ----------
        source : str
            The full Python source text to lint.
        filename : str
            A filename hint passed to ruff via ``--stdin-filename``.  This
            controls which ruff rules apply and how paths appear in output.
        """
        self._request_lint.emit(source, filename)

    def stop(self) -> None:
        """Stop the background thread gracefully.

        Call this in the owning widget's ``closeEvent`` or when the editor
        tab is removed to avoid orphaned threads.
        """
        self._thread.quit()
        self._thread.wait(2000)
