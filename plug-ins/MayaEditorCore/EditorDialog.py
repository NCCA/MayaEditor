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
"""Editor Dialog Class for the NCCA Maya Editor.

This is the core Dialog class where all other elements are created and controlled. This can work stand alone as well as part of a plugin.
"""
import os
import socket
import sys
from pathlib import Path
from typing import Any

import maya.api.OpenMaya as OpenMaya
import maya.api.OpenMayaUI as OpenMayaUI
import maya.cmds as cmds
import maya.OpenMayaUI as omui
from maya import utils
from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtUiTools import *
from PySide2.QtWidgets import *

# Note this is from Maya not pyside so type hints not generated
from shiboken2 import wrapInstance  # type: ignore

from .CustomUILoader import UiLoader
from .EditorToolBar import EditorToolBar
from .MelTextEdit import MelTextEdit
from .OutputToolBar import OutputToolBar
from .PythonTextEdit import PythonTextEdit
from .SidebarModels import SideBarModels
from .TextEdit import TextEdit
from .Workspace import Workspace


def get_main_window() -> Any:
    """Return the maya main window for parenting.

    Grab the maya main window
    Returns : QWidget of the MayaMainWindow
    """
    window = omui.MQtUtil.mainWindow()
    return wrapInstance(int(window), QWidget)


class EditorDialog(QDialog):
    """Editor Dialog window main class.

    Inherits from QDialog and loads the ui from files.
    """

    update_output = Signal(str)
    update_output_html = Signal(str)
    update_fonts = Signal(QFont)
    toggle_line_numbers = Signal(bool)

    def __init__(self, parent=None):
        """Construct the class.

        Parameters :
        parent (QWidget) : the Maya parent window Note this is set to None so we can use the get_main_window() function in maya
        If we run standalone we need to pass in a main window instance (see the EditorStandalone.py module)
        """
        # do this here so we can run standalone or in maya
        if parent is None:
            parent = get_main_window()

        super().__init__(parent)
        # Register the callback to filter the outputs to out output window
        self.callback_id = OpenMaya.MCommandMessage.addCommandOutputCallback(
            self.message_callback, ""
        )
        # Load setting first as required by other elements
        self.settings = QSettings("NCCA", "NCCA_Maya_Editor")
        # Next the UI as again required for other things
        self.root_path = cmds.moduleInfo(path=True, moduleName="MayaEditor")
        UiLoader().loadUi(self.root_path + "/plug-ins/ui/form.ui", self)
        # load icons
        self.python_icon = QIcon(self.root_path + "/plug-ins/icons/python.png")
        self.mel_icon = QIcon(self.root_path + "/plug-ins/icons/mel.png")
        self.text_icon = QIcon(self.root_path + "/plug-ins/icons/text.png")

        # This should make the window stay on top
        self.setWindowFlags(Qt.Tool)
        # as other things may depend on this create early
        self.create_output_window()
        self.create_tool_bar()
        self.create_menu_bar()
        self.sidebar_models = SideBarModels(self)
        self.sidebar_treeview.setModel(self.sidebar_models.active_model)
        self.sidebar_selector.currentIndexChanged.connect(self.change_active_model)
        # connect tab close event
        self.editor_tab.tabCloseRequested.connect(self.tab_close_requested)
        # setup file view sidebar
        self.sidebar_treeview.setHeaderHidden(True)
        self.sidebar_treeview.clicked.connect(self.file_view_changed)
        # create workspace
        self.workspace = Workspace()
        # connect output window signals
        self.update_output.connect(self.output_window.append_plain_text)
        self.update_output_html.connect(self.output_window.append_html)
        # Finally load in settings and create live editors
        self.load_settings()
        self.create_live_editors()
        self.update_fonts.emit(self.font)
        self.show()

    def load_settings(self) -> None:
        """Load in the setting from QSettings for the editor."""
        splitter_settings = self.settings.value("splitter")
        self.editor_splitter.restoreState(splitter_settings)  # type: ignore

        splitter_settings = self.settings.value("vertical_splitter")
        self.vertical_splitter.restoreState(splitter_settings)  # type: ignore
        sz = self.settings.value(
            "size",
        )
        self.resize(self.settings.value("size", QSize(1024, 720)))
        workspace = self.settings.value("workspace")
        self.load_workspace_to_editor(workspace)

        self.settings.beginGroup("Font")
        name = self.settings.value("font-name", type=str)
        size = self.settings.value("font-size", type=int)
        weight = self.settings.value("font-weight", type=int)
        italic = self.settings.value("font-italic", type=bool)
        self.settings.endGroup()

        self.font = QFont(name, size, weight, italic)
        self.update_fonts.emit(self.font)

    def save_settings(self) -> None:
        self.settings.setValue("splitter", self.editor_splitter.saveState())  # type: ignore
        self.settings.setValue("vertical_splitter", self.vertical_splitter.saveState())  # type: ignore
        self.settings.setValue("size", self.size())
        self.settings.setValue("workspace", self.workspace.file_name)
        self.settings.beginGroup("Font")

        self.settings.setValue("font-name", self.font.family())
        self.settings.setValue("font-size", self.font.pointSize())
        self.settings.setValue("font-weight", self.font.weight())
        self.settings.setValue("font-italic", self.font.italic())
        self.settings.endGroup()

    def change_font(self) -> None:
        """Popup a change font dialog and set all editor fonts"""
        (ok, font) = QFontDialog.getFont(self)
        if ok:
            self.font = font
            self.update_fonts.emit(self.font)

    def debug(self, message: str) -> None:
        self.output_window.appendHtml(
            f'<b><p style="color:yellow">Debug :</p></b><p>{message}</p>'
        )

    def message_callback(self, message: str, mtype, client_data) -> None:
        """Use to put maya output to the output window.
        Parameters :
        message (str) : the message to print
        mtype (int) : type of message
        client_data : not used
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

        # this moves to the end so we don't get double new lines etc
        # self.output_window.moveCursor(QTextCursor.End)
        html = f'<p style="color:{colour}"><pre>{message_prefix}{message}</pre></p>'
        self.update_output_html.emit(html)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Event called when the Dialog closeEvent is  triggered.

        We ensure that the setting are saved to the default settings.
        Parameters :
        event (QCloseEvent) : event passed in to close
        """
        OpenMaya.MMessage.removeCallback(self.callback_id)
        self.save_settings()
        self.workspace.close()
        super(EditorDialog, self).closeEvent(event)

    def create_menu_bar(self) -> None:
        """Create the menubar for the editor."""
        self.menu_bar = QMenuBar()
        file_menu = QMenu("&File")
        self.menu_bar.addMenu(file_menu)
        open_action = QAction("&Open", self)
        open_action.triggered.connect(self.open_file)  # type: ignore
        file_menu.addAction(open_action)

        new_action = QAction("&New", self)
        new_action.triggered.connect(self.new_file)  # type: ignore
        file_menu.addAction(new_action)

        workspace_menu = QMenu("&Workspace")
        new_workspace = QAction("New Workspace", self)
        new_workspace.triggered.connect(self.new_workspace)  # type: ignore
        workspace_menu.addAction(new_workspace)
        # open workspace
        open_workspace = QAction("Open Workspace", self)
        open_workspace.triggered.connect(self.open_workspace)  # type: ignore
        workspace_menu.addAction(open_workspace)
        # save workspace
        save_workspace = QAction("Save Workspace", self)
        save_workspace.triggered.connect(self.save_workspace)  # type: ignore
        workspace_menu.addAction(save_workspace)
        # close workspace
        close_workspace = QAction("Close Workspace", self)
        close_workspace.triggered.connect(self.close_workspace)  # type: ignore
        workspace_menu.addAction(close_workspace)

        self.menu_bar.addMenu(workspace_menu)

        settings_menu = QMenu("&Settings")
        # Add settings Menu

        # add font action
        # font_menu = QMenu("&Font", self)
        change_font_action = QAction("Change Font", self)
        settings_menu.addAction(change_font_action)
        change_font_action.triggered.connect(self.change_font)

        # show line numbers
        show_line_numbers_action = QAction("Show Line Numbers", self)
        settings_menu.addAction(show_line_numbers_action)
        show_line_numbers_action.toggled.connect(self.show_line_numbers)
        show_line_numbers_action.setCheckable(True)
        show_line_numbers_action.setChecked(True)

        # Menu to main menu bar
        self.menu_bar.addMenu(settings_menu)

        self.main_grid_layout.setMenuBar(self.menu_bar)  # type: ignore

    def open_file(self) -> None:
        """Open a new file and add to the tabs."""
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Select File to Open",
            "",
            ("Mel / Python (*.py *.mel, *.*)"),
        )
        self.create_editor_and_load_files(file_name)
        # add this file to current workspace
        self.workspace.add_file(file_name)

    def new_file(self) -> None:
        """Create a new file tab."""
        editor = PythonTextEdit(
            code="",
            filename="untitled.py",
            read_only=False,
            show_line_numbers=True,
            live=False,
        )
        self.editor_tab.insertTab(0, editor, "untitled.py")  # type: ignore
        self.editor_tab.setCurrentIndex(0)
        self.editor_tab.widget(0).setFocus()

    def create_tool_bar(self) -> None:
        """Create the toolbar."""
        self.tool_bar = EditorToolBar(self)  # QToolBar(self)
        # Add to main dialog
        self.dock_widget.setWidget(self.tool_bar)  # type: ignore
        self.output_tool_bar = OutputToolBar(self)  # QToolBar(self)
        # Add to main dialog
        self.output_dock.setWidget(self.output_tool_bar)  # type: ignore

    def tab_close_requested(self, index: int) -> None:
        """Slot called when a tab close is pressed.

        logic to see if we need to save or not is included here for ease.
        Parameters :
        index (int) : index of the tab where the close was requested.
        """
        tab: QTabWidget = self.editor_tab  # type: ignore
        editor: PythonTextEdit = tab.widget(index)  # type: ignore
        file_name = tab.tabText(index)
        # don't close live editors
        if file_name in ["Python live_window", "Mel live_window"]:
            return
        if editor.needs_saving is not True:
            tab.removeTab(index)
            self.remove_from_open_files(file_name)
        # need to check if we want to save or discard
        else:
            msg_box = QMessageBox()
            msg_box.setWindowTitle("Warning!")
            msg_box.setText("File has been Modified")
            msg_box.setInformativeText("Do you want to save your changes?")
            msg_box.setStandardButtons(
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
            )
            msg_box.setDefaultButton(QMessageBox.Save)
            ret = msg_box.exec_()
            if ret == QMessageBox.Save:
                saved = editor.save_file()
                if saved:
                    tab.removeTab(index)
                    self.remove_from_open_files(file_name)
                else:
                    return
            elif ret == QMessageBox.Discard:
                tab.removeTab(index)
                self.remove_from_open_files(file_name)
            elif ret == QMessageBox.Cancel:
                pass

    def new_workspace(self) -> None:
        """Create a new workspace.

        Logic checks to ensure the previous workspace is saved or not.
        """
        if self.workspace.is_saved is not True:
            self.save_workspace()
        tab = self.editor_tab  # type: ignore
        tab.clear()
        self.workspace.new()
        self.sidebar_treeview.clear()
        self.create_live_editors()

    def save_workspace(self) -> None:
        """Save current workspace."""
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Select Workspace Name",
            "untitled.workspace",
            ("Workspace (*.workspace)"),
        )
        if file_name is not None:
            self.workspace.save(file_name)

    def close_workspace(self) -> None:
        """Close the current workspace."""
        # if not self.workspace.is_saved :
        #     self.save_workspace()

        tab = self.editor_tab  # type: ignore
        tab.clear()
        self.sidebar_treeview.clear()
        self.create_live_editors()

    def show_line_numbers(self, state):
        self.toggle_line_numbers.emit(state)

    def open_workspace(self) -> None:
        """Open a new workspace.

        There is logic to ensure that the current one is saved or not.
        """
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Select Workspace Name",
            "untitled.workspace",
            ("Workspace (*.workspace)"),
        )
        if file_name is not None:
            self.settings.setValue("workspace", file_name)
            self.load_workspace_to_editor(file_name)

    def create_editor_and_load_files(self, code_file_name: str) -> None:
        """This method creates new editors and links the different elements.

        Parameters.
            code_file_name (str) : full path to the file to load will be truncated to short name for the tabs be getting the last name / extension

        """
        path = Path(code_file_name)
        if path.is_file():
            with open(code_file_name, "r") as code_file:
                short_name = str(Path(code_file_name).name)
                if path.suffix == ".py":
                    editor = PythonTextEdit(
                        code=code_file.read(),
                        filename=code_file_name,
                        live=False,
                        show_line_numbers=True,
                        read_only=False,
                    )
                    icon = self.python_icon
                elif path.suffix == ".mel":
                    editor = MelTextEdit(
                        code=code_file.read(),
                        filename=code_file_name,
                        live=False,
                        show_line_numbers=True,
                        read_only=False,
                    )
                    icon = self.mel_icon
                else:
                    editor = TextEdit(
                        code=code_file.read(),
                        filename=code_file_name,
                        show_line_numbers=True,
                        read_only=False,
                    )
                    icon = self.text_icon
                    editor.set_editor_fonts(self.font)

                # Add to the active files to run
                if path.suffix in (".mel", ".py"):
                    self.tool_bar.add_to_active_file_list(short_name)

                self.workspace.add_file(code_file_name)
                # self.update_fonts.connect(editor.set_editor_fonts)
                self.connect_editor_slots(editor)
                # add to the tab
                tab = self.editor_tab
                tab_index = tab.addTab(editor, icon, short_name)  # type: ignore
                tab.setTabsClosable(True)
                tab.setCurrentIndex(tab_index)
                # add to the file view and run menu
                self.sidebar_models.append_to_workspace(short_name)
                self.update_fonts.emit(self.font)

        else:
            self.output_window.appendHtml(
                f'<b><p style="color:red">Error :</p></b><p>Problem loading  file {code_file_name} from project perhaps it has been removed</p>'
            )

    def load_workspace_to_editor(self, file_name: str) -> None:
        """Load in the actual workspace data to the editor tab.
        This is called to load and create each new PythonTextEdit into the tabs
        Parameters :
        file_name (str) : full path to the editor file to load
        """
        if self.workspace.load(file_name):
            for code_file_name in self.workspace.files:
                self.create_editor_and_load_files(code_file_name)
        # as same code is used for loading new files on initial ws load we set this to true
        self.workspace.is_saved = True

    @Slot()
    def tool_bar_run_clicked(self):
        """Slot used by the Toolbar run button."""
        self.editor_tab.currentWidget().execute_code()

    @Slot(int)
    def tool_bar_goto_changed(self, line: int):
        """Slot used by the Toolbar goto dial."""
        # Note we subtract 1 as the line is defaulting to the correct range
        self.editor_tab.currentWidget().goto_line(line - 1)

    @Slot()
    def tool_bar_run_project_clicked(self):
        """Slot called when run project clicked."""
        pass
        file_to_run = self.tool_bar.active_project_file.currentText()
        # first find the index of the active tab
        tab = self.editor_tab  # type: ignore
        index = 0
        for t in range(0, tab.count() + 1):
            if file_to_run == tab.tabText(t):
                index = t
                break
        self.editor_tab.widget(index).execute_code()

    def file_view_changed(self, index):
        """Update the editor tab based on the new item."""
        selector_index = self.sidebar_selector.currentIndex()
        if selector_index == 0:
            item = self.sidebar_models.workspace.itemFromIndex(index)  # item.text(0)
            text = item.text()
            # first find the index of the active tab
            tab = self.editor_tab  # type: ignore
            index = 0
            for t in range(0, tab.count() + 1):
                if text == tab.tabText(t):
                    index = t
                    break
            tab.setCurrentIndex(t)
        elif selector_index == 1:  # file system view
            path = self.sidebar_models.file_system_model.filePath(index)
            self.create_editor_and_load_files(path)

    def remove_from_open_files(self, filename: str) -> None:
        """Remove filename from sidebar.
        Parameters :
        filename (str) : the name to search for and remove
        """
        self.sidebar_models.remove_from_workspace(filename)
        self.tool_bar.remove_from_active_file_list(filename)
        # remove from workspace
        self.workspace.remove_file(filename)

    def create_live_editors(self) -> None:
        editor = PythonTextEdit(
            code="", filename="live_window", live=True, read_only=False, parent=self
        )
        self.connect_editor_slots(editor)

        self.editor_tab.insertTab(0, editor, self.python_icon, "Python live_window")  # type: ignore
        self.editor_tab.setCurrentIndex(0)
        self.editor_tab.widget(0).setFocus()
        self.sidebar_models.append_to_workspace("Python live_window")
        # add the Mel live window
        editor = MelTextEdit(
            code="",
            filename="live_window",
            live=True,
            read_only=False,
            show_line_numbers=True,
            parent=self,
        )
        self.connect_editor_slots(editor)
        self.editor_tab.insertTab(0, editor, self.mel_icon, "Mel live_window")  # type: ignore
        # self.editor_tab.setTabsClosable(False)
        self.editor_tab.setCurrentIndex(0)
        self.editor_tab.widget(0).setFocus()
        self.sidebar_models.append_to_workspace("Mel live_window")

    def create_output_window(self) -> None:
        self.output_window = TextEdit(
            parent=self, read_only=True, show_line_numbers=False
        )
        self.update_fonts.connect(self.output_window.set_editor_fonts)
        self.update_fonts.emit(self.font)
        #  create a splitter for the help / output
        self.output_splitter = QSplitter()
        self.output_splitter.addWidget(self.output_window)
        # add the help section and wire up
        self.help_frame = QFrame()
        UiLoader().loadUi(
            self.root_path + "/plug-ins/ui/helpwidget.ui", self.help_frame
        )
        frame_layout = self.help_frame.grid_layout
        self.help_output_window = TextEdit(
            parent=self.help_frame, read_only=True, show_line_numbers=False
        )
        frame_layout.addWidget(self.help_output_window, 1, 0, 2, 2)
        #        self.help_frame.addWidget(0, 1, , 2, TextEdit())
        self.output_splitter.addWidget(self.help_frame)
        self.output_window_layout.addWidget(self.output_splitter)
        self.maya_cmds = cmds.help("[a-z]*", list=True, lng="Python")
        for c in self.maya_cmds:
            self.help_frame.help_items.addItem(c)
        self.help_frame.help_items.currentIndexChanged.connect(self.run_maya_help)
        self.help_frame.search_help.returnPressed.connect(self.search_maya_help)

    @Slot(int)
    def run_maya_help(self, index: int) -> None:
        command = self.help_frame.help_items.currentText()
        output = cmds.help(command)
        output = output.strip("\n")
        self.help_output_window.clear()
        self.help_output_window.appendPlainText(output)

    @Slot(int)
    def search_maya_help(self) -> None:
        help_text = self.help_frame.search_help.text()
        if help_text in self.maya_cmds:
            output = cmds.help(help_text)
            output = output.strip("\n")
            self.help_output_window.clear()
            self.help_output_window.appendPlainText(output)

    def connect_editor_slots(self, editor):
        editor.update_output.connect(self.output_window.append_plain_text)
        editor.update_output_html.connect(self.output_window.append_html)
        editor.draw_line.connect(self.output_window.append_line)
        self.update_fonts.connect(editor.set_editor_fonts)
        self.toggle_line_numbers.connect(editor.toggle_line_number)

    @Slot(int)
    def change_active_model(self, index):
        self.sidebar_models.change_active_model(index)
        if index == 0:  # workspace files
            self.sidebar_treeview.setModel(self.sidebar_models.workspace)
            self.sidebar_treeview.setHeaderHidden(True)
        elif index == 1:  # filesystem mode

            self.sidebar_treeview.setModel(self.sidebar_models.file_system_model)
            self.sidebar_treeview.setHeaderHidden(False)

            self.sidebar_treeview.setRootIndex(
                self.sidebar_models.file_system_model.index(QDir.currentPath())
            )
