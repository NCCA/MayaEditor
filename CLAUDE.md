# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MayaEditor is a replacement for Maya's built-in Script Editor, written in Python 3 with PySide6. It provides a modern code editor experience with syntax highlighting, autocomplete, linting, and workspace management for both Python and MEL scripts within Autodesk Maya.

## Installation and Development Setup

### Installing the Plugin

The editor is installed via a Maya module file:

```bash
python3 ./installEditor.py
```

This script locates the Maya modules folder for your OS and generates `MayaEditor.mod`:
- **Linux**: `$HOME/maya`
- **Mac**: `$HOME/Library/Preferences/Autodesk/maya`
- **Windows**: `%HOMEPATH%\Documents\maya\`

### Loading in Maya

Load through Maya's Plugin Manager, or programmatically:

```python
import maya.cmds as cmds
cmds.MayaEditor()
```

### Running Standalone (for development)

For testing outside Maya's GUI:

```bash
./EditorStandalone.py
```

This uses `maya.standalone` and allows development without launching the full Maya application.

## Code Linting and Type Checking

### mypy

Configuration is in `mypy.ini`. Run type checking:

```bash
mypy plug-ins/MayaEditorCore/
```

Settings:
- `follow_imports=skip` - avoids Maya's internal type stubs
- `ignore_missing_imports = True` - necessary for Maya API imports

### Ruff

The editor has integrated Ruff linting (`RuffLinter.py`). The linter runs in a background QThread and provides real-time diagnostics in the editor. Configure the Ruff executable path through the Settings menu in the editor UI.

## Architecture

### Plugin Entry Point

**`plug-ins/MayaEditor.py`**: Maya plugin that registers the `MayaEditor` MPxCommand. This file:
- Handles hot-reload by deleting `sys.modules["MayaEditorCore"]`
- Maintains a global `MayaEditorMixinWindow` instance required by Maya's workspace control restoration
- Implements `MayaEditorUIScript()` for creating/restoring the dockable UI

### Core Package Structure

**`plug-ins/MayaEditorCore/`**: The main editor logic, structured as follows:

#### Main Dialog and UI
- **`EditorDialog.py`**: Core dialog implementation with three classes:
  - `EditorDialogCore`: Base QDialog with all editor functionality
  - `EditorDialog`: Adds `MayaQWidgetDockableMixin` for Maya docking
  - `EditorDialogStandalone`: Variant for standalone execution
- **`MainUI.py`**: Generated from `ui/form.ui` (Qt Designer file)
- **`EditorToolBar.py`**: Top toolbar with file operations and editor controls
- **`OutputToolBar.py`**: Toolbar for output window controls

#### Text Editors
- **`TextEdit.py`**: Base editor class extending `QPlainTextEdit`
  - Provides line numbers, zoom, find/replace, code folding
  - Foundation for all editor types
- **`PythonTextEdit.py`**: Python-specific editor
  - Jedi autocomplete integration
  - Python syntax highlighting
  - AST-based code model for sidebar navigation
  - Ruff linting integration
  - Executes code via `maya.utils.executeDeferred()`
- **`MelTextEdit.py`**: MEL-specific editor
  - MEL syntax highlighting
  - Executes MEL code via `maya.mel.eval()`

#### Syntax Highlighting
- **`BaseHighlighter.py`**: Base `QSyntaxHighlighter` class
  - Provides `_create_format()` methods for consistent styling
  - Wraps child highlighter rules in `QRegularExpression` objects
- **`PythonHighlighter.py`**: Python syntax rules (keywords, strings, comments)
- **`MelHighlighter.py`**: MEL syntax rules

#### Autocomplete and Linting
- **`JediCompleter.py`**: Jedi-based autocomplete popup
  - Runs completion queries in background threads
  - Custom `QListWidget` popup with Maya command integration
  - Gracefully handles missing Jedi installation
- **`RuffLinter.py`**: Background Python linting via Ruff
  - Runs in `QThread` to avoid blocking UI
  - Emits `diagnostics_ready` signal with lint results
  - Displays warnings/errors with colored underlines in editor

#### Supporting Components
- **`Workspace.py`**: Manages collections of files as JSON-based workspaces
- **`SettingsManager.py`**: QSettings wrapper for editor preferences (font, Ruff path, window geometry)
- **`OutputManager.py`**: Manages the output window for script execution results
- **`SidebarModels.py`**: Provides QAbstractItemModel for sidebar tree view (file system, code model)
- **`LineNumberArea.py`**: Line number margin widget
- **`CodeFoldingManager.py`**: Manages code folding state for collapsible regions
- **`FindDialog.py`**: Find/replace dialog
- **`CustomUILoader.py`**: Custom UI loading utilities

### UI Resources

- **`plug-ins/ui/form.ui`**: Qt Designer file defining the main dialog layout
- **`plug-ins/MayaEditor.qrc`**: Qt resource file listing icons
- **`plug-ins/MayaEditor.rcc`**: Compiled resource file (binary)

To regenerate resources after editing `.qrc`:

```bash
pyside6-rcc plug-ins/MayaEditor.qrc -o plug-ins/MayaEditor.rcc
```

To regenerate UI Python code after editing `.ui`:

```bash
pyside6-uic plug-ins/ui/form.ui -o plug-ins/MayaEditorCore/MainUI.py
```

## Key Design Patterns

### Hot Reload Support

The plugin supports hot-reload during development:
- `plug-ins/MayaEditor.py` deletes `sys.modules["MayaEditorCore"]` on load
- Global `MayaEditorMixinWindow` instance is preserved across reloads
- Workspace control restoration relies on returning the same window instance

### Thread Safety

Maya's command execution must occur on the main thread:
- Python execution uses `maya.utils.executeDeferred()`
- MEL execution uses `maya.mel.eval()` directly
- Autocomplete and linting run in background threads/QThreads
- Signals connect background results to main thread UI updates

### Signals and Slots

Heavy use of Qt signals for loose coupling:
- `update_output` / `update_output_html` - output window updates
- `update_fonts` - font changes propagate to all editors
- `toggle_line_numbers` - show/hide line numbers
- `diagnostics_ready` - linter results from background thread

### Inheritance Hierarchy

```
QPlainTextEdit
  └─ TextEdit (base with line numbers, folding, zoom)
      ├─ PythonTextEdit (+ Python highlighting, Jedi, Ruff, AST model)
      └─ MelTextEdit (+ MEL highlighting, MEL execution)

QDialog
  └─ EditorDialogCore (core functionality)
      ├─ EditorDialog (+ MayaQWidgetDockableMixin for docking)
      └─ EditorDialogStandalone (standalone variant)
```

## Common Development Patterns

### Adding a New Editor Feature

1. Implement in `TextEdit.py` if common to all editors
2. Override in `PythonTextEdit.py` or `MelTextEdit.py` for language-specific behavior
3. Connect via signals if the feature needs to communicate with `EditorDialog`

### Modifying the UI Layout

1. Edit `plug-ins/ui/form.ui` in Qt Designer
2. Regenerate `MainUI.py`: `pyside6-uic plug-ins/ui/form.ui -o plug-ins/MayaEditorCore/MainUI.py`
3. Update `EditorDialog.py` to wire new widgets

### Adding Icons

1. Add image files to `plug-ins/icons/`
2. Update `plug-ins/MayaEditor.qrc` to include new files
3. Regenerate: `pyside6-rcc plug-ins/MayaEditor.qrc -o plug-ins/MayaEditor.rcc`
4. Access via `QIcon(":/icons/filename.png")`

## Dependencies

- **PySide6**: Qt 6 bindings for Python
- **Maya API**: `maya.cmds`, `maya.api.OpenMaya`, `maya.api.OpenMayaUI`, `maya.mel`
- **Jedi** (optional): Python autocomplete
- **Ruff** (optional): Python linting

## Testing

Currently no automated test suite exists (noted in TODO.md). Manual testing:

1. Test in Maya: Load plugin, create/open files, execute code
2. Test standalone: Run `./EditorStandalone.py`
3. Test hot-reload: Modify code, reload plugin in Maya

## Known Issues and Limitations

- No automated tests (TODO item)
- Autocomplete popup visibility issues on some platforms (see `FIXES_SUMMARY.md`)
- Workspace/UI/Loading logic could be refactored (TODO item)
- File modification detection and auto-reload not yet implemented

## Code Style

- Type hints throughout (enforced by mypy)
- Docstrings use NumPy/Google style
- Ruff-compliant formatting
- Logger usage instead of print statements
- PEP 8 naming conventions
