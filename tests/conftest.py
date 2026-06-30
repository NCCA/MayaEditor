"""Pytest configuration and fixtures for MayaEditor tests.

This module provides:
1. Maya standalone initialization (session scope)
2. QApplication fixture (session scope)
3. Test isolation fixtures (QSettings, temp directories)
4. Pytest markers for test categorization
"""

import os
import sys
import tempfile
from pathlib import Path
from typing import Generator

import pytest

# Add plug-ins to path BEFORE any imports
PROJECT_ROOT = Path(__file__).parent.parent
PLUGIN_PATH = PROJECT_ROOT / "plug-ins"
sys.path.insert(0, str(PLUGIN_PATH))


# =============================================================================
# Maya Path Detection
# =============================================================================

def find_latest_maya() -> Path:
    """Find the latest Maya installation on macOS.

    Returns
    -------
    Path
        Path to mayapy executable

    Raises
    ------
    RuntimeError
        If no Maya installation found or mayapy not found
    """
    import re

    maya_base = Path("/Applications/Autodesk")
    if not maya_base.exists():
        raise RuntimeError("Maya not found in /Applications/Autodesk")

    # Only match maya#### directories (like maya2026, maya2025)
    maya_dirs = [
        d for d in maya_base.glob("maya[0-9]*")
        if d.is_dir() and re.match(r'maya\d{4}', d.name)
    ]
    maya_dirs = sorted(maya_dirs, reverse=True)

    if not maya_dirs:
        raise RuntimeError("No Maya installations found")

    mayapy_path = maya_dirs[0] / "Maya.app/Contents/bin/mayapy"
    if not mayapy_path.exists():
        raise RuntimeError(f"mayapy not found at {mayapy_path}")

    return mayapy_path


# Store for use in other fixtures
try:
    MAYAPY_PATH = find_latest_maya()
except RuntimeError as e:
    MAYAPY_PATH = None
    print(f"Warning: {e}")


# =============================================================================
# Pytest Configuration
# =============================================================================

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "unit: Pure Python tests (no Qt, no Maya execution)"
    )
    config.addinivalue_line(
        "markers", "component: Qt widget tests (requires QApplication, may need Maya)"
    )
    config.addinivalue_line(
        "markers", "integration: Full system tests (requires Maya + Qt)"
    )
    config.addinivalue_line(
        "markers", "maya: Tests that execute Maya commands"
    )
    config.addinivalue_line(
        "markers", "slow: Slow-running tests"
    )


# =============================================================================
# Maya Standalone Initialization (Session Scope)
# =============================================================================

@pytest.fixture(scope="session", autouse=True)
def maya_standalone():
    """Initialize Maya standalone once per test session.

    This fixture:
    1. Sets Qt.AA_ShareOpenGLContexts attribute
    2. Initializes maya.standalone
    3. Yields control to tests
    4. Uninitializes Maya on teardown

    Scope: session (once for entire test run)
    Autouse: True (automatically applied to all tests)
    """
    from PySide6.QtCore import QCoreApplication, Qt

    # CRITICAL: Must set this BEFORE QApplication creation
    QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)

    # Initialize Maya standalone
    import maya.standalone
    maya.standalone.initialize(name="python")

    # Import maya.cmds to populate command list for highlighters
    import maya.cmds as cmds

    yield

    # Cleanup
    maya.standalone.uninitialize()


# =============================================================================
# Qt Application Fixture (Session Scope)
# =============================================================================

@pytest.fixture(scope="session")
def qapp(maya_standalone):
    """Provide a QApplication instance for the entire test session.

    This fixture depends on maya_standalone to ensure correct initialization
    order. Maya must be initialized before QApplication.

    Scope: session (one QApplication for all tests)
    """
    from PySide6.QtWidgets import QApplication

    # Check if QApplication already exists
    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    yield app

    # Note: QApplication cleanup happens automatically


# =============================================================================
# QSettings Isolation (Function Scope)
# =============================================================================

@pytest.fixture(scope="function")
def isolated_qsettings(tmp_path):
    """Provide isolated QSettings using IniFormat for test isolation.

    Each test gets its own settings file in a temp directory, preventing
    tests from interfering with each other or with the user's real settings.

    Returns
    -------
    QSettings
        QSettings instance configured with IniFormat
    """
    from PySide6.QtCore import QSettings

    # Create a temporary settings file
    settings_file = tmp_path / "test_settings.ini"

    # Use IniFormat for explicit file control
    settings = QSettings(str(settings_file), QSettings.IniFormat)

    yield settings

    # Cleanup: QSettings auto-syncs on destruction
    settings.sync()


# =============================================================================
# Temporary Directory Fixtures
# =============================================================================

@pytest.fixture(scope="function")
def temp_workspace_dir(tmp_path):
    """Provide a temporary directory for workspace test files.

    Returns
    -------
    Path
        Path object to temporary directory
    """
    workspace_dir = tmp_path / "workspaces"
    workspace_dir.mkdir()
    return workspace_dir


@pytest.fixture(scope="function")
def sample_workspace_data():
    """Provide sample workspace JSON data for testing.

    Returns
    -------
    dict
        Workspace data structure
    """
    return {
        "name": "Test Workspace",
        "files": [
            "/path/to/file1.py",
            "/path/to/file2.mel",
        ],
        "root": "/test/root",
    }


# =============================================================================
# Maya Command List Fixture
# =============================================================================

@pytest.fixture(scope="session")
def maya_commands(maya_standalone):
    """Provide Maya command list for highlighter tests.

    This fixture caches the Maya command list once per session since
    it's expensive to generate and doesn't change.

    Returns
    -------
    list
        Maya command names
    """
    import maya.cmds as cmds
    return cmds.help("[a-z]*", list=True, lng="Python")


# =============================================================================
# Sample Code Fixtures
# =============================================================================

@pytest.fixture
def sample_python_code():
    """Provide sample Python code for testing."""
    return '''import maya.cmds as cmds

class MyClass:
    def __init__(self):
        self.value = 42

    def create_sphere(self):
        """Create a sphere in Maya."""
        cmds.polySphere(name="test_sphere", radius=5)
        return True

def standalone_function():
    """A module-level function."""
    obj = MyClass()
    return obj.create_sphere()
'''


@pytest.fixture
def sample_mel_code():
    """Provide sample MEL code for testing."""
    return '''// MEL Script Example
proc string createCube() {
    string $cube[] = `polyCube -w 1 -h 1 -d 1`;
    return $cube[0];
}

global proc testScript() {
    string $result = createCube();
    print("Created: " + $result + "\\n");
}
'''


# =============================================================================
# Mock Dialog Parent Fixture
# =============================================================================

@pytest.fixture
def mock_dialog_parent(qapp):
    """Provide a mock parent widget for dialog tests.

    Returns
    -------
    QWidget
        A minimal parent widget
    """
    from PySide6.QtWidgets import QWidget

    parent = QWidget()
    yield parent
    parent.close()
    parent.deleteLater()


# =============================================================================
# Test File Creation Helpers
# =============================================================================

@pytest.fixture
def create_test_file(tmp_path):
    """Fixture factory for creating test files.

    Usage
    -----
    def test_something(create_test_file):
        file_path = create_test_file("test.py", "print('hello')")

    Returns
    -------
    callable
        Function that creates a file and returns its path
    """
    def _create(filename: str, content: str) -> Path:
        file_path = tmp_path / filename
        file_path.write_text(content)
        return file_path

    return _create
