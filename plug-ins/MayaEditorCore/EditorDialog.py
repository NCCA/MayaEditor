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
"""Core Editor Dialog for the NCCA Maya Editor.

This is the main dialog class where all child widgets are created and managed.
It can work standalone or as a Maya dockable plugin mixin.
"""

from pathlib import Path
from typing import Any, Optional

import maya.api.OpenMaya as OpenMaya
import maya.cmds as cmds
import maya.OpenMayaUI as omui
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin

from PySide6.QtCore import QDir, QSettings, QSize, Qt, Signal, Slot
from PySide6.QtGui import (
    QAction,
    QCloseEvent,
    QFont,
    QIcon,
    QKeyEvent,
    QKeySequence,
)
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QInputDialog,
    QLineEdit,
    QMenu,
    QMenuBar,
    QMessageBox,
)

from shiboken6 import wrapInstance  # type: ignore

from .EditorToolBar import EditorToolBar
from .MainUI import Ui_editor_dialog
from .MelTextEdit import MelTextEdit
from .OutputManager import OutputManager
from .OutputToolBar import OutputToolBar
from .PythonTextEdit import PythonTextEdit
from .SettingsManager import SettingsManager
from .SidebarModels import SideBarModels
from .TextEdit import TextEdit
from .Workspace import Workspace


def get_main_window() -> Any:
    """Return the Maya main window as a QDialog for parenting.

    Returns
    -------
    QDialog
        The Maya main window wrapped as a QWidget.
    """
    window = omui.MQtUtil.mainWindow()
    return wrapInstance(int(window), QDialog)


class EditorDialogCore(QDialog):
    """Base editor dialog class.

    Inherit from this for either a standalone editor or a Maya dockable mixin.
    Loads the UI from generated code and creates all sub-widgets.

    Signals
    -------
    update_output : Signal(str)
        Emitted with plain text for the output window.
    update_output_html : Signal(str)
        Emitted with HTML text for the output window.
    update_fonts : Signal(QFont)
        Emitted when the editor font changes.
    toggle_line_numbers : Signal(bool)
        Emitted to toggle line number visibility.
    """

    update_output = Signal(str)
    update_output_html = Signal(str)
    update_fonts = Signal(QFont)
    toggle_line_numbers = Signal(bool)
    editor_name: str = "NCCA_Script_Editor"

    def __init__(self, parent: Optional[Any] = None) -> None:
        """Construct the EditorDialogCore.

        Parameters
        ----------
        parent : QWidget or None
            Parent widget. None uses ``get_main_window()`` in Maya.
        """
        super().__init__(parent=parent)
        self.setObjectName(self.__class__.editor_name)

        self.callback_id: int = OpenMaya.MCommandMessage.addCommandOutputCallback(
            self.message_callback, ""
        )
        self.settings_manager = SettingsManager(self, QSettings("NCCA", "NCCA_Maya_Editor"))
        self.file_system_root: str = QDir.currentPath()
        self.root_path: str = cmds.moduleInfo(path=True, moduleName="MayaEditor")
        self.python_icon = QIcon(":/icons/python.png")
        self.mel_icon = QIcon(":/icons/mel.png")
        self.text_icon = QIcon(":/icons/text.png")

        self.ui = Ui_editor_dialog()
        self.ui.setupUi(self)
        self.setWindowFlags(Qt.Tool)

        self.workspace = Workspace()
        self.output_manager = OutputManager(self)
        self.output_manager.create()
        self.create_tool_bar()
        self.create_menu_bar()

        self.sidebar_models = SideBarModels(self, root_path=self.root_path, editor_tab=self.ui.editor_tab)
        self.ui.sidebar_treeview.setModel(self.sidebar_models.active_model)
        self.ui.sidebar_selector.currentIndexChanged.connect(self.change_active_model)
        self._autocomplete_enabled = True

        self.ui.editor_tab.tabCloseRequested.connect(self.tab_close_requested)
        self.ui.editor_tab.currentChanged.connect(
            self.sidebar_models.code_model_needs_update
        )
        self.ui.editor_tab.currentChanged.connect(self._on_active_tab_changed)
        self.ui.sidebar_treeview.setHeaderHidden(True)
        self.ui.sidebar_treeview.clicked.connect(self.sidebar_view_changed)

        self.update_output.connect(self.output_manager.output_window.append_plain_text)
        self.update_output_html.connect(self.output_manager.output_window.append_html)

        self.load_settings()
        self.create_live_editors()
        self.update_fonts.emit(self.font)
        self.update_window_title()

    @property
    def settings(self) -> QSettings:
        """Expose the underlying QSettings for backward-compatible access."""
        return self.settings_manager._settings

    def update_window_title(self) -> None:
        """Set the window title to include the current workspace name."""
        name = self.workspace.workspace_name
        if name:
            self.setWindowTitle(f"NCCA Editor - {name}")
        else:
            self.setWindowTitle("NCCA Editor")
        if hasattr(self, "tool_bar"):
            self.tool_bar.update_workspace_label(name)

    def load_settings(self) -> None:
        """Load editor settings — delegates to :class:`SettingsManager`."""
        self.settings_manager.load()

    def save_settings(self) -> None:
        """Save current editor settings — delegates to :class:`SettingsManager`."""
        self.settings_manager.save()

    def change_font(self) -> None:
        """Show a font dialog and apply the selected font — delegates to :class:`SettingsManager`."""
        self.settings_manager.change_font()

    def debug(self, message: str) -> None:
        """Append a debug message to the output window.

        Parameters
        ----------
        message : str
            The debug message text.
        """
        self.output_manager.output_window.appendHtml(
            f'<b><p style="color:yellow">Debug :</p></b><p>{message}</p>'
        )

    def message_callback(self, message: str, mtype: int, client_data: Any) -> None:
        """Callback for Maya command output to route messages to the output window.

        Parameters
        ----------
        message : str
            The message text.
        mtype : int
            The message type constant from OpenMaya.MCommandMessage.
        client_data : Any
            Unused client data.
        """
        colour = "white"
        message_prefix = ""
        if mtype == OpenMaya.MCommandMessage.kHistory:
            colour = "lightblue"
            message_prefix = "History : "
        elif mtype == OpenMaya.MCommandMessage.kDisplay:
            colour = "yellow"
        elif mtype == OpenMaya.MCommandMessage.kInfo:
            colour = "white"
            message_prefix = "Info : "
        elif mtype == OpenMaya.MCommandMessage.kWarning:
            colour = "green"
            message_prefix = "Warning : "
        elif mtype == OpenMaya.MCommandMessage.kError:
            colour = "red"
            message_prefix = "Error : "
        elif mtype == OpenMaya.MCommandMessage.kResult:
            colour = "lightblue"
            message_prefix = "Result :"

        html = f'<p style="color:{colour}"><pre>{message_prefix}{message}</pre></p>'
        self.update_output_html.emit(html)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Save settings and clean up on dialog close.

        Parameters
        ----------
        event : QCloseEvent
            The close event.
        """
        OpenMaya.MMessage.removeCallback(self.callback_id)
        self.save_settings()
        self.workspace.close()
        super().closeEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle Escape key to close the dialog.

        Parameters
        ----------
        event : QKeyEvent
            The key event.
        """
        if event.key() == Qt.Key_Escape:
            return
        super().keyPressEvent(event)

    def create_menu_bar(self) -> None:
        """Create the menu bar with File, Workspace and Settings menus."""
        self.menu_bar = QMenuBar()

        file_menu = QMenu("&File")
        self.menu_bar.addMenu(file_menu)

        open_action = QAction("&Open", self)
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)

        new_python_action = QAction("&New Python File", self)
        new_python_action.triggered.connect(self.new_python_file)
        file_menu.addAction(new_python_action)

        new_mel_action = QAction("New &MEL File", self)
        new_mel_action.triggered.connect(self.new_mel_file)
        file_menu.addAction(new_mel_action)

        workspace_menu = QMenu("&Workspace")
        new_workspace = QAction("New Workspace", self)
        new_workspace.triggered.connect(self.new_workspace)
        workspace_menu.addAction(new_workspace)

        open_workspace = QAction("Open Workspace", self)
        open_workspace.triggered.connect(self.open_workspace)
        workspace_menu.addAction(open_workspace)

        save_workspace = QAction("Save Workspace", self)
        save_workspace.triggered.connect(self.save_workspace)
        workspace_menu.addAction(save_workspace)

        close_workspace = QAction("Close Workspace", self)
        close_workspace.triggered.connect(self.close_workspace)
        workspace_menu.addAction(close_workspace)

        workspace_menu.addSeparator()

        rename_workspace = QAction("Rename Workspace...", self)
        rename_workspace.triggered.connect(self.rename_workspace)
        workspace_menu.addAction(rename_workspace)

        self.menu_bar.addMenu(workspace_menu)

        settings_menu = QMenu("&Settings")

        change_font_action = QAction("Change Font", self)
        settings_menu.addAction(change_font_action)
        change_font_action.triggered.connect(self.change_font)

        set_root_action = QAction("Set Workspace Root...", self)
        settings_menu.addAction(set_root_action)
        set_root_action.triggered.connect(self.set_workspace_root)

        set_ruff_action = QAction("Set Ruff Executable...", self)
        settings_menu.addAction(set_ruff_action)
        set_ruff_action.triggered.connect(self.set_ruff_executable)

        show_line_numbers_action = QAction("Show Line Numbers", self)
        settings_menu.addAction(show_line_numbers_action)
        show_line_numbers_action.toggled.connect(self.show_line_numbers)
        show_line_numbers_action.setCheckable(True)
        show_line_numbers_action.setChecked(True)

        show_output_window_action = QAction("Show Output Window", self)
        settings_menu.addAction(show_output_window_action)
        show_output_window_action.toggled.connect(
            lambda state: self.ui.output_window_group_box.setVisible(state)
        )
        show_output_window_action.setCheckable(True)
        show_output_window_action.setChecked(True)
        show_output_window_action.setShortcut(
            QKeySequence(Qt.ControlModifier | Qt.Key_1)
        )

        show_sidebar_action = QAction("Show Sidebar", self)
        settings_menu.addAction(show_sidebar_action)
        show_sidebar_action.toggled.connect(
            lambda state: self.ui.side_bar.setVisible(state)
        )
        show_sidebar_action.setCheckable(True)
        show_sidebar_action.setChecked(True)
        show_sidebar_action.setShortcut(QKeySequence(Qt.ControlModifier | Qt.Key_0))

        self.menu_bar.addMenu(settings_menu)
        self.ui.main_grid_layout.setMenuBar(self.menu_bar)

    def set_workspace_root(self) -> None:
        """Open a directory dialog to set the file-system sidebar root."""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Workspace Root", self.file_system_root
        )
        if directory:
            self.file_system_root = directory
            self.sidebar_models.file_system_model.setRootPath(directory)
            if self.ui.sidebar_selector.currentIndex() == 1:
                self.ui.sidebar_treeview.setRootIndex(
                    self.sidebar_models.file_system_model.index(directory)
                )
            if self.workspace.file_name:
                self.workspace.root = directory
                self.workspace.is_saved = False

    def set_ruff_executable(self) -> None:
        """Set the ruff executable path — delegates to :class:`SettingsManager`."""
        self.settings_manager.set_ruff_executable()

    def open_file(self) -> None:
        """Show a file-open dialog and load the selected file into a new tab."""
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Select File to Open",
            "",
            "Mel / Python (*.py *.mel, *.*)",
        )
        if file_name and file_name not in self.workspace.files:
            self.create_editor_and_load_files(file_name)
            self.workspace.add_file(file_name)

    def new_python_file(self) -> None:
        """Create a new untitled Python file tab."""
        editor = PythonTextEdit(
            code="",
            filename="untitled.py",
            read_only=False,
            show_line_numbers=True,
            live=False,
            parent=self,
        )
        if self.settings_manager._ruff_executable:
            editor._linter.set_executable(self.settings_manager._ruff_executable)
        self.connect_editor_slots(editor)
        self.ui.editor_tab.insertTab(0, editor, "untitled.py")
        self.ui.editor_tab.setCurrentIndex(0)
        self.ui.editor_tab.widget(0).setFocus()

    def new_mel_file(self) -> None:
        """Create a new untitled MEL file tab."""
        editor = MelTextEdit(
            code="",
            filename="untitled.mel",
            read_only=False,
            show_line_numbers=True,
            live=False,
            parent=self,
        )
        self.connect_editor_slots(editor)
        self.ui.editor_tab.insertTab(0, editor, self.mel_icon, "untitled.mel")
        self.ui.editor_tab.setCurrentIndex(0)
        self.ui.editor_tab.widget(0).setFocus()

    def create_tool_bar(self) -> None:
        """Create the editor and output toolbars."""
        self.tool_bar = EditorToolBar(self)
        self.tool_bar.rename_workspace_requested.connect(self.rename_workspace)
        self.tool_bar.file_open_requested.connect(self.create_editor_and_load_files)
        self.ui.dock_widget.setWidget(self.tool_bar)
        self.output_tool_bar = OutputToolBar(self)
        self.output_tool_bar.autocomplete_toggled.connect(self._on_autocomplete_toggled)
        self.output_tool_bar.help_toggled.connect(self.output_manager.help_frame.setVisible)
        self.output_tool_bar.lint_toggled.connect(self.output_manager.lint_panel.setVisible)
        self.ui.output_dock.setWidget(self.output_tool_bar)

    def tab_close_requested(self, index: int) -> None:
        """Handle a tab close request with optional save prompt.

        Parameters
        ----------
        index : int
            Index of the tab being closed.
        """
        tab = self.ui.editor_tab
        editor = tab.widget(index)
        file_name = tab.tabText(index)

        if file_name in ("Python live_window", "Mel live_window"):
            return

        if not editor.needs_saving:
            tab.removeTab(index)
            self.remove_from_open_files(file_name)
        else:
            msg_box = QMessageBox()
            msg_box.setWindowTitle("Warning!")
            msg_box.setText("File has been Modified")
            msg_box.setInformativeText("Do you want to save your changes?")
            msg_box.setStandardButtons(
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
            )
            msg_box.setDefaultButton(QMessageBox.Save)
            ret = msg_box.exec()
            if ret == QMessageBox.Save:
                saved = editor.save_file()
                if saved:
                    tab.removeTab(index)
                    self.remove_from_open_files(file_name)
            elif ret == QMessageBox.Discard:
                tab.removeTab(index)
                self.remove_from_open_files(file_name)

    def new_workspace(self) -> None:
        """Create a new workspace, saving the current one if needed."""
        if not self.workspace.is_saved:
            self.save_workspace()
        tab = self.ui.editor_tab
        tab.clear()
        self.workspace.new()
        self.update_window_title()
        if self.ui.sidebar_treeview.model():
            self.ui.sidebar_treeview.model().clear()
        self.create_live_editors()

    def save_workspace(self) -> None:
        """Save the current workspace, prompting for a location only when new."""
        if self.workspace.file_name:
            self.workspace.save(self.workspace.file_name)
        else:
            file_name, _ = QFileDialog.getSaveFileName(
                self,
                "Select Workspace Name",
                "untitled.workspace",
                "Workspace (*.workspace)",
            )
            if file_name:
                self.workspace.file_name = file_name
                self.workspace.save(file_name)

    def close_workspace(self) -> None:
        """Close the current workspace and reset the editor."""
        tab = self.ui.editor_tab
        tab.clear()
        if self.ui.sidebar_treeview:
            self.ui.sidebar_treeview.clear()
        self.create_live_editors()
        self.update_window_title()

    def rename_workspace(self) -> None:
        """Prompt the user to rename the current workspace."""
        text, ok = QInputDialog.getText(
            self,
            "Rename Workspace",
            "Workspace Name:",
            QLineEdit.EchoMode.Normal,
            self.workspace.workspace_name,
        )
        if ok and text:
            self.workspace.workspace_name = text
            self.workspace.is_saved = False
            self.update_window_title()

    def show_line_numbers(self, state: bool) -> None:
        """Toggle line number visibility in all editors.

        Parameters
        ----------
        state : bool
            True to show line numbers.
        """
        self.toggle_line_numbers.emit(state)

    def open_workspace(self) -> None:
        """Open a workspace from file, prompting to save the current one first."""
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Select Workspace Name",
            "untitled.workspace",
            "Workspace (*.workspace)",
        )
        if file_name:
            self.settings.setValue("workspace", file_name)
            self.load_workspace_to_editor(file_name)

    def create_editor_and_load_files(self, code_file_name: str) -> None:
        """Create an editor tab for the given file and load its contents.

        Parameters
        ----------
        code_file_name : str
            Full path to the file to load.
        """
        tab = self.ui.editor_tab
        path = Path(code_file_name)
        if not path.is_file():
            self.output_manager.output_window.appendHtml(
                f'<b><p style="color:red">Error :</p></b><p>'
                f"Problem loading file {code_file_name} from project "
                f"perhaps it has been removed</p>"
            )
            return

        with open(code_file_name, "r") as code_file:
            short_name = path.name
            if path.suffix == ".py":
                editor = PythonTextEdit(
                    code=code_file.read(),
                    filename=code_file_name,
                    live=False,
                    show_line_numbers=True,
                    read_only=False,
                    parent=tab,
                )
                icon = self.python_icon
            elif path.suffix == ".mel":
                editor = MelTextEdit(
                    code=code_file.read(),
                    filename=code_file_name,
                    live=False,
                    show_line_numbers=True,
                    read_only=False,
                    parent=tab,
                )
                icon = self.mel_icon
            else:
                editor = TextEdit(
                    code=code_file.read(),
                    filename=code_file_name,
                    show_line_numbers=True,
                    read_only=False,
                    parent=tab,
                )
                icon = self.text_icon
                editor.set_editor_fonts(self.font)

            if path.suffix == ".py" and self.settings_manager._ruff_executable:
                editor._linter.set_executable(self.settings_manager._ruff_executable)

            if path.suffix in (".mel", ".py"):
                self.tool_bar.add_to_active_file_list(short_name)
                editor.code_model_changed.connect(
                    self.sidebar_models.code_model_needs_update
                )

            self.workspace.add_file(code_file_name)
            self.connect_editor_slots(editor)
            tab_index = tab.addTab(editor, icon, short_name)
            tab.setTabsClosable(True)
            tab.setCurrentIndex(tab_index)
            self.sidebar_models.append_to_workspace(short_name, icon)
            self.update_fonts.emit(self.font)

    def load_workspace_to_editor(self, file_name: str) -> None:
        """Load workspace data and create editor tabs for each file.

        Parameters
        ----------
        file_name : str
            Full path to the workspace file.
        """
        if self.workspace.load(file_name):
            for code_file_name in self.workspace.files:
                self.create_editor_and_load_files(code_file_name)
            if self.workspace.root:
                self.file_system_root = self.workspace.root
                self.sidebar_models.file_system_model.setRootPath(self.workspace.root)
                if self.ui.sidebar_selector.currentIndex() == 1:
                    self.ui.sidebar_treeview.setRootIndex(
                        self.sidebar_models.file_system_model.index(self.workspace.root)
                    )
        self.workspace.is_saved = True
        self.update_window_title()

    @Slot()
    def tool_bar_run_clicked(self) -> None:
        """Execute the code in the currently active editor tab."""
        self.ui.editor_tab.currentWidget().execute_code()

    @Slot(int)
    def tool_bar_goto_changed(self, line: int) -> None:
        """Go to a specific line in the active editor.

        Parameters
        ----------
        line : int
            1-based line number.
        """
        self.ui.editor_tab.currentWidget().goto_line(line - 1)

    @Slot()
    def tool_bar_run_project_clicked(self) -> None:
        """Execute the file selected in the run-project combo box."""
        file_to_run = self.tool_bar.active_project_file.currentText()
        tab = self.ui.editor_tab
        index = 0
        for t in range(tab.count()):
            if file_to_run == tab.tabText(t):
                index = t
                break
        tab.widget(index).execute_code()

    def sidebar_view_changed(self, index: Any) -> None:
        """Handle clicks in the sidebar tree view.

        Parameters
        ----------
        index : QModelIndex
            The model index that was clicked.
        """
        selector_index = self.ui.sidebar_selector.currentIndex()
        if selector_index == 0:
            item = self.sidebar_models.workspace.itemFromIndex(index)
            text = item.text()
            tab = self.ui.editor_tab
            tab_index = 0
            for t in range(tab.count()):
                if text == tab.tabText(t):
                    tab_index = t
                    break
            tab.setCurrentIndex(tab_index)
        elif selector_index == 1:
            path = self.sidebar_models.file_system_model.filePath(index)
            self.create_editor_and_load_files(path)
        elif selector_index == 2:
            item = self.sidebar_models.code_system_model.itemFromIndex(index)
            self.ui.editor_tab.currentWidget().goto_line(item.data())

    def remove_from_open_files(self, filename: str) -> None:
        """Remove a filename from the sidebar, toolbar, and workspace.

        Parameters
        ----------
        filename : str
            The filename to remove.
        """
        self.sidebar_models.remove_from_workspace(filename)
        self.tool_bar.remove_from_active_file_list(filename)
        self.workspace.remove_file(filename)

    def create_live_editors(self) -> None:
        """Create the live Python and MEL editor tabs for interactive use."""
        editor = PythonTextEdit(
            code="",
            filename="live_window",
            live=True,
            read_only=False,
            parent=self.ui.editor_tab,
        )
        if self.settings_manager._ruff_executable:
            editor._linter.set_executable(self.settings_manager._ruff_executable)
        self.connect_editor_slots(editor)
        self.ui.editor_tab.insertTab(0, editor, self.python_icon, "Python live_window")
        self.ui.editor_tab.setCurrentIndex(0)
        self.ui.editor_tab.widget(0).setFocus()
        self.sidebar_models.append_to_workspace("Python live_window", self.python_icon)

        editor = MelTextEdit(
            code="",
            filename="live_window",
            live=True,
            read_only=False,
            show_line_numbers=True,
            parent=self.ui.editor_tab,
        )
        self.connect_editor_slots(editor)
        self.ui.editor_tab.insertTab(0, editor, self.mel_icon, "Mel live_window")
        self.ui.editor_tab.setCurrentIndex(0)
        self.ui.editor_tab.widget(0).setFocus()
        self.sidebar_models.append_to_workspace("Mel live_window", self.mel_icon)

    # ---------------------------------------------------------------------------
    # Forwarding properties — widgets live on OutputManager; these keep
    # OutputToolBar working unchanged until Task 10 updates its references.
    # ---------------------------------------------------------------------------

    @property
    def output_window(self) -> TextEdit:
        """Output window widget (owned by :class:`OutputManager`)."""
        return self.output_manager.output_window

    @property
    def help_frame(self):  # type: ignore[return]
        """Help panel frame (owned by :class:`OutputManager`)."""
        return self.output_manager.help_frame

    @property
    def lint_panel(self):  # type: ignore[return]
        """Lint results panel (owned by :class:`OutputManager`)."""
        return self.output_manager.lint_panel

    def connect_editor_slots(self, editor: TextEdit) -> None:
        """Connect the standard signals for an editor widget.

        Parameters
        ----------
        editor : TextEdit
            The editor widget to wire up.
        """
        editor.update_output.connect(self.output_manager.output_window.append_plain_text)
        editor.update_output_html.connect(self.output_manager.output_window.append_html)
        editor.draw_line.connect(self.output_manager.output_window.append_line)
        editor.add_file_to_workspace.connect(self.workspace.add_file)
        self.update_fonts.connect(editor.set_editor_fonts)
        self.toggle_line_numbers.connect(editor.toggle_line_number)
        if isinstance(editor, PythonTextEdit):
            editor.setAutoCompletion(self._autocomplete_enabled)
        # Wire lint results to the lint panel for Python editors
        if isinstance(editor, PythonTextEdit):
            editor.lint_results_changed.connect(self._on_editor_lint_results)

    @Slot(bool)
    def _on_autocomplete_toggled(self, checked: bool) -> None:
        """Apply the autocomplete state to all open Python editors."""
        self._autocomplete_enabled = checked
        tab = self.ui.editor_tab
        for index in range(tab.count()):
            editor = tab.widget(index)
            if isinstance(editor, PythonTextEdit):
                editor.setAutoCompletion(checked)

    @Slot(int)
    def _on_active_tab_changed(self, _index: int) -> None:
        """Clear the lint panel when switching tabs.

        The panel will be repopulated once the newly active editor's linter
        fires (or immediately if the editor already has cached results).
        """
        self.output_manager.lint_panel.setRowCount(0)
        editor = self.ui.editor_tab.currentWidget()
        if isinstance(editor, PythonTextEdit) and editor._diagnostics:
            self.output_manager.update_lint_panel(editor._diagnostics)

    @Slot(list)
    def _on_editor_lint_results(self, diagnostics: list) -> None:
        """Update the lint panel only when the signal comes from the active tab.

        Parameters
        ----------
        diagnostics : list[Diagnostic]
            Diagnostics from the editor that emitted ``lint_results_changed``.
        """
        # sender() returns the PythonTextEdit that emitted the signal
        sending_editor = self.sender()
        active_editor = self.ui.editor_tab.currentWidget()
        if sending_editor is active_editor:
            self.output_manager.update_lint_panel(diagnostics)

    @Slot(int)
    def change_active_model(self, index: int) -> None:
        """Switch the active sidebar model.

        Parameters
        ----------
        index : int
            0 = workspace, 1 = file-system, 2 = code outline.
        """
        self.sidebar_models.change_active_model(index)
        if index == 0:
            self.ui.sidebar_treeview.setModel(self.sidebar_models.workspace)
            self.ui.sidebar_treeview.setHeaderHidden(True)
        elif index == 1:
            self.ui.sidebar_treeview.setModel(self.sidebar_models.file_system_model)
            self.ui.sidebar_treeview.setHeaderHidden(False)
            self.ui.sidebar_treeview.setRootIndex(
                self.sidebar_models.file_system_model.index(self.file_system_root)
            )
        elif index == 2:
            self.ui.sidebar_treeview.setModel(self.sidebar_models.code_system_model)
            self.sidebar_models.generate_code_model()
            self.ui.sidebar_treeview.setHeaderHidden(True)


class EditorDialog(MayaQWidgetDockableMixin, EditorDialogCore):
    """Maya dockable editor dialog. Uses MayaQWidgetDockableMixin for docking."""

    def __init__(self) -> None:
        """Construct and show the dockable editor."""
        super().__init__()
        self.show(dockable=True)


class EditorDialogStandalone(EditorDialogCore):
    """Standalone (non-Maya) editor dialog."""

    def __init__(self) -> None:
        """Construct and show the standalone editor."""
        EditorDialogCore.__init__(self)
        self.show()

    def load_settings(self) -> None:
        """Override load_settings for standalone mode.

        QSettings.value() is unreliable in Maya standalone due to PySide6 enum
        dispatch bugs. Restore splitter state safely and fall back to hardcoded
        font defaults rather than crashing.
        """
        try:
            splitter_settings = self.settings.value("splitter")
            self.ui.editor_splitter.restoreState(splitter_settings)
        except Exception:
            pass
        try:
            splitter_settings = self.settings.value("vertical_splitter")
            self.ui.vertical_splitter.restoreState(splitter_settings)
        except Exception:
            pass
        try:
            self.resize(self.settings.value("size", QSize(1024, 720)))
        except Exception:
            self.resize(QSize(1024, 720))
        try:
            workspace = self.settings.value("workspace")
            if workspace:
                self.load_workspace_to_editor(workspace)
        except Exception:
            pass
        try:
            root = self.settings.value("file_system_root")
            if root:
                self.file_system_root = str(root)
        except Exception:
            pass

        self.font = QFont("Courier New", 12, 50, False)
        self.update_fonts.emit(self.font)
