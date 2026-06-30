"""Unit tests for Workspace class (pure Python, no Qt dialogs)."""

import json
import pytest
from pathlib import Path

# Import Workspace - now works with lazy-loaded highlighters
from MayaEditorCore.Workspace import Workspace


@pytest.mark.unit
class TestWorkspace:
    """Test suite for Workspace class."""

    def test_init_creates_empty_workspace(self):
        """Test that Workspace initializes with empty state."""
        workspace = Workspace()

        assert workspace.workspace_name == ""
        assert workspace.files == []
        assert workspace.is_saved is True
        assert workspace.file_name == ""
        assert workspace.root == ""

    def test_add_file_appends_to_list(self):
        """Test adding a file to workspace."""
        workspace = Workspace()
        test_file = "/path/to/test.py"

        workspace.add_file(test_file)

        assert test_file in workspace.files
        assert workspace.is_saved is False

    def test_add_file_prevents_duplicates(self):
        """Test that adding same file twice doesn't create duplicates."""
        workspace = Workspace()
        test_file = "/path/to/test.py"

        workspace.add_file(test_file)
        workspace.add_file(test_file)

        assert workspace.files.count(test_file) == 1

    def test_remove_file_by_partial_match(self):
        """Test removing a file by partial name match."""
        workspace = Workspace()
        test_file = "/path/to/test.py"
        workspace.add_file(test_file)

        workspace.remove_file("test.py")

        assert test_file not in workspace.files

    def test_remove_file_updates_saved_state(self):
        """Test that removing a file marks workspace as unsaved."""
        workspace = Workspace()
        test_file = "/path/to/test.py"
        workspace.add_file(test_file)
        workspace.is_saved = True  # Manually mark as saved

        workspace.remove_file("test.py")

        assert workspace.is_saved is False

    def test_save_creates_json_file(self, temp_workspace_dir):
        """Test saving workspace to JSON file."""
        workspace = Workspace()
        workspace.workspace_name = "Test Workspace"
        workspace.files = ["/path/to/file1.py", "/path/to/file2.mel"]
        workspace.root = "/test/root"

        save_path = temp_workspace_dir / "test.workspace"
        workspace.save(str(save_path))

        assert save_path.exists()
        assert workspace.is_saved is True

        # Verify JSON structure
        with open(save_path) as f:
            data = json.load(f)

        assert data["name"] == "Test Workspace"
        assert len(data["files"]) == 2
        assert data["root"] == "/test/root"

    def test_save_creates_valid_json_format(self, temp_workspace_dir):
        """Test that saved JSON is properly formatted."""
        workspace = Workspace()
        workspace.workspace_name = "Format Test"
        workspace.files = ["/file1.py"]
        workspace.root = "/root"

        save_path = temp_workspace_dir / "format_test.workspace"
        workspace.save(str(save_path))

        # Verify JSON can be loaded and is formatted
        with open(save_path) as f:
            content = f.read()
            # Should have indentation (workspace.save uses indent=4)
            assert "    " in content
            data = json.loads(content)

        assert data is not None

    def test_load_reads_workspace_file(self, temp_workspace_dir, sample_workspace_data):
        """Test loading workspace from JSON file."""
        # Create test workspace file
        workspace_file = temp_workspace_dir / "test.workspace"
        with open(workspace_file, "w") as f:
            json.dump(sample_workspace_data, f)

        workspace = Workspace()
        result = workspace.load(str(workspace_file))

        assert result is True
        assert workspace.workspace_name == "Test Workspace"
        assert len(workspace.files) == 2
        assert workspace.root == "/test/root"
        assert workspace.file_name == str(workspace_file)

    def test_load_handles_missing_file(self):
        """Test loading non-existent workspace returns False."""
        workspace = Workspace()
        result = workspace.load("/nonexistent/file.workspace")

        assert result is False
        assert workspace.files == []

    def test_load_handles_malformed_json(self, temp_workspace_dir, caplog):
        """Test loading malformed JSON returns False gracefully."""
        import logging
        bad_file = temp_workspace_dir / "bad.workspace"
        bad_file.write_text("{invalid json")

        workspace = Workspace()
        with caplog.at_level(logging.WARNING, logger="MayaEditorCore.Workspace"):
            result = workspace.load(str(bad_file))

        assert result is False
        assert workspace.files == []
        assert any("workspace" in r.message.lower() for r in caplog.records)

    def test_load_handles_missing_root_field(self, temp_workspace_dir):
        """Test loading workspace without 'root' field (legacy format)."""
        legacy_data = {
            "name": "Legacy Workspace",
            "files": ["/path/to/file.py"],
        }
        workspace_file = temp_workspace_dir / "legacy.workspace"
        with open(workspace_file, "w") as f:
            json.dump(legacy_data, f)

        workspace = Workspace()
        result = workspace.load(str(workspace_file))

        assert result is True
        assert workspace.workspace_name == "Legacy Workspace"
        assert workspace.root == ""  # Default value

    def test_load_clears_previous_files(self, temp_workspace_dir, sample_workspace_data):
        """Test that loading a workspace clears previously loaded files."""
        workspace = Workspace()
        workspace.files = ["/old/file1.py", "/old/file2.py"]

        workspace_file = temp_workspace_dir / "new.workspace"
        with open(workspace_file, "w") as f:
            json.dump(sample_workspace_data, f)

        workspace.load(str(workspace_file))

        # Should only have files from the loaded workspace
        assert len(workspace.files) == 2
        assert "/old/file1.py" not in workspace.files
        assert "/path/to/file1.py" in workspace.files
