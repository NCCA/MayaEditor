"""Smoke test to verify Maya standalone initialization works."""

import pytest


@pytest.mark.unit
def test_maya_imports():
    """Test that Maya modules can be imported."""
    import maya.standalone
    import maya.cmds as cmds
    import maya.api.OpenMaya as OpenMaya

    assert maya.standalone is not None
    assert cmds is not None
    assert OpenMaya is not None


@pytest.mark.unit
def test_qapp_fixture(qapp):
    """Test that QApplication fixture works."""
    assert qapp is not None
    from PySide6.QtCore import QCoreApplication
    # In Maya standalone, we might get QGuiApplication instead of QApplication
    assert isinstance(qapp, QCoreApplication)


@pytest.mark.unit
def test_maya_commands_fixture(maya_commands):
    """Test that Maya commands are available."""
    assert maya_commands is not None
    assert isinstance(maya_commands, list)
    assert len(maya_commands) > 0
    assert "polySphere" in maya_commands
    assert "polyCube" in maya_commands


@pytest.mark.unit
def test_isolated_qsettings_fixture(isolated_qsettings):
    """Test that isolated QSettings fixture works."""
    from PySide6.QtCore import QSettings
    assert isolated_qsettings is not None
    assert isinstance(isolated_qsettings, QSettings)

    # Test write/read
    isolated_qsettings.setValue("test_key", "test_value")
    assert isolated_qsettings.value("test_key") == "test_value"
