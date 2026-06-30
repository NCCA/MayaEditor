"""Unit tests for SettingsManager (with QSettings mocking)."""

import pytest
from unittest.mock import Mock
from PySide6.QtCore import QSettings, QSize
from PySide6.QtGui import QFont

# Import SettingsManager - now works with lazy-loaded highlighters
from MayaEditorCore.SettingsManager import SettingsManager


@pytest.mark.unit
class TestSettingsManager:
    """Test suite for SettingsManager."""

    @pytest.fixture
    def mock_dialog(self):
        """Create a mock EditorDialog for testing."""
        dialog = Mock()
        dialog.ui = Mock()
        dialog.ui.editor_splitter = Mock()
        dialog.ui.editor_splitter.saveState.return_value = b""
        dialog.ui.vertical_splitter = Mock()
        dialog.ui.vertical_splitter.saveState.return_value = b""
        dialog.ui.editor_tab = Mock()
        dialog.font = QFont("Courier New", 12)
        dialog.update_fonts = Mock()
        dialog.update_fonts.emit = Mock()
        dialog.workspace = Mock()
        dialog.workspace.file_name = ""
        dialog.file_system_root = "/test/root"
        dialog.resize = Mock()
        dialog.load_workspace_to_editor = Mock()
        dialog.size = Mock(return_value=QSize(1024, 768))
        return dialog

    def test_init_stores_dialog_and_settings(self, mock_dialog, isolated_qsettings):
        """Test SettingsManager initialization."""
        manager = SettingsManager(mock_dialog, isolated_qsettings)

        assert manager._dialog == mock_dialog
        assert manager._settings == isolated_qsettings
        assert manager._ruff_executable == ""

    def test_save_stores_splitter_state(self, mock_dialog, isolated_qsettings):
        """Test saving splitter states."""
        manager = SettingsManager(mock_dialog, isolated_qsettings)
        mock_dialog.ui.editor_splitter.saveState.return_value = b"splitter_data"
        mock_dialog.ui.vertical_splitter.saveState.return_value = b"vertical_data"

        manager.save()

        assert isolated_qsettings.value("splitter") == b"splitter_data"
        assert isolated_qsettings.value("vertical_splitter") == b"vertical_data"

    def test_save_stores_window_size(self, mock_dialog, isolated_qsettings):
        """Test saving window size."""
        manager = SettingsManager(mock_dialog, isolated_qsettings)
        mock_dialog.size.return_value = QSize(1280, 800)

        manager.save()

        saved_size = isolated_qsettings.value("size")
        assert saved_size.width() == 1280
        assert saved_size.height() == 800

    def test_save_stores_font_settings(self, mock_dialog, isolated_qsettings):
        """Test saving font configuration."""
        manager = SettingsManager(mock_dialog, isolated_qsettings)
        test_font = QFont("Monaco", 14, QFont.Bold, italic=True)
        mock_dialog.font = test_font

        manager.save()

        isolated_qsettings.beginGroup("Font")
        assert isolated_qsettings.value("font-name") == "Monaco"
        assert isolated_qsettings.value("font-size") == 14
        assert isolated_qsettings.value("font-italic") is True
        isolated_qsettings.endGroup()

    def test_save_stores_ruff_executable(self, mock_dialog, isolated_qsettings):
        """Test saving ruff executable path."""
        manager = SettingsManager(mock_dialog, isolated_qsettings)
        manager._ruff_executable = "/usr/local/bin/ruff"

        manager.save()

        assert isolated_qsettings.value("ruff_executable") == "/usr/local/bin/ruff"

    def test_save_stores_workspace_filename(self, mock_dialog, isolated_qsettings):
        """Test saving workspace filename."""
        manager = SettingsManager(mock_dialog, isolated_qsettings)
        mock_dialog.workspace.file_name = "/path/to/workspace.workspace"

        manager.save()

        assert isolated_qsettings.value("workspace") == "/path/to/workspace.workspace"

    def test_load_restores_window_size(self, mock_dialog, isolated_qsettings):
        """Test loading window size."""
        # Pre-populate settings
        isolated_qsettings.setValue("size", QSize(1400, 900))

        manager = SettingsManager(mock_dialog, isolated_qsettings)
        manager.load()

        mock_dialog.resize.assert_called_once()
        call_args = mock_dialog.resize.call_args[0][0]
        assert call_args.width() == 1400
        assert call_args.height() == 900

    def test_load_uses_default_size_when_missing(self, mock_dialog, isolated_qsettings):
        """Test default window size when no saved size exists."""
        manager = SettingsManager(mock_dialog, isolated_qsettings)
        manager.load()

        # Should resize to default (1024, 720)
        mock_dialog.resize.assert_called()
        call_args = mock_dialog.resize.call_args[0][0]
        assert call_args.width() == 1024
        assert call_args.height() == 720

    def test_load_restores_font_settings(self, mock_dialog, isolated_qsettings, qapp):
        """Test loading font configuration."""
        # Pre-populate font settings
        isolated_qsettings.beginGroup("Font")
        isolated_qsettings.setValue("font-name", "Monaco")
        isolated_qsettings.setValue("font-size", 14)
        isolated_qsettings.setValue("font-weight", 75)  # Bold
        isolated_qsettings.setValue("font-italic", True)
        isolated_qsettings.endGroup()

        manager = SettingsManager(mock_dialog, isolated_qsettings)
        manager.load()

        # Check font was set on dialog
        assert mock_dialog.font.family() == "Monaco"
        assert mock_dialog.font.pointSize() == 14
        assert mock_dialog.font.italic() is True
        mock_dialog.update_fonts.emit.assert_called_once()

    def test_load_restores_ruff_executable(self, mock_dialog, isolated_qsettings):
        """Test loading ruff executable path."""
        isolated_qsettings.setValue("ruff_executable", "/custom/path/ruff")

        manager = SettingsManager(mock_dialog, isolated_qsettings)
        manager.load()

        assert manager._ruff_executable == "/custom/path/ruff"

    def test_load_handles_corrupt_settings_gracefully(self, mock_dialog, isolated_qsettings):
        """Test that corrupt settings don't crash the load process."""
        # Create intentionally problematic settings
        isolated_qsettings.setValue("size", "invalid_size_data")

        manager = SettingsManager(mock_dialog, isolated_qsettings)
        # Should not raise exception
        manager.load()

        # Should fall back to default size
        mock_dialog.resize.assert_called()

    def test_load_handles_missing_font_gracefully(self, mock_dialog, isolated_qsettings):
        """Test default font when font settings are missing."""
        manager = SettingsManager(mock_dialog, isolated_qsettings)
        manager.load()

        # Should have set a font (even if defaults)
        assert mock_dialog.font is not None
        assert mock_dialog.font.family() == "Courier New"  # Default
        assert mock_dialog.font.pointSize() == 12  # Default
