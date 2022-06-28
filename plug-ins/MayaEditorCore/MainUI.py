# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'form.ui'
##
## Created by: Qt User Interface Compiler version 5.15.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *


class Ui_editor_dialog(object):
    def setupUi(self, editor_dialog):
        if not editor_dialog.objectName():
            editor_dialog.setObjectName("editor_dialog")
        editor_dialog.resize(995, 705)
        self.main_grid_layout = QGridLayout(editor_dialog)
        self.main_grid_layout.setObjectName("main_grid_layout")
        self.vertical_splitter = QSplitter(editor_dialog)
        self.vertical_splitter.setObjectName("vertical_splitter")
        self.vertical_splitter.setOrientation(Qt.Vertical)
        self.editor_splitter = QSplitter(self.vertical_splitter)
        self.editor_splitter.setObjectName("editor_splitter")
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(2)
        sizePolicy.setHeightForWidth(
            self.editor_splitter.sizePolicy().hasHeightForWidth()
        )
        self.editor_splitter.setSizePolicy(sizePolicy)
        self.editor_splitter.setOrientation(Qt.Horizontal)
        self.side_bar = QGroupBox(self.editor_splitter)
        self.side_bar.setObjectName("side_bar")
        sizePolicy1 = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(2)
        sizePolicy1.setHeightForWidth(self.side_bar.sizePolicy().hasHeightForWidth())
        self.side_bar.setSizePolicy(sizePolicy1)
        self.verticalLayout = QVBoxLayout(self.side_bar)
        self.verticalLayout.setObjectName("verticalLayout")
        self.sidebar_selector = QComboBox(self.side_bar)
        self.sidebar_selector.addItem("")
        self.sidebar_selector.addItem("")
        self.sidebar_selector.addItem("")
        self.sidebar_selector.setObjectName("sidebar_selector")

        self.verticalLayout.addWidget(self.sidebar_selector)

        self.sidebar_treeview = QTreeView(self.side_bar)
        self.sidebar_treeview.setObjectName("sidebar_treeview")
        sizePolicy2 = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(1)
        sizePolicy2.setHeightForWidth(
            self.sidebar_treeview.sizePolicy().hasHeightForWidth()
        )
        self.sidebar_treeview.setSizePolicy(sizePolicy2)

        self.verticalLayout.addWidget(self.sidebar_treeview)

        self.editor_splitter.addWidget(self.side_bar)
        self.editor_tab = QTabWidget(self.editor_splitter)
        self.editor_tab.setObjectName("editor_tab")
        sizePolicy3 = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sizePolicy3.setHorizontalStretch(1)
        sizePolicy3.setVerticalStretch(1)
        sizePolicy3.setHeightForWidth(self.editor_tab.sizePolicy().hasHeightForWidth())
        self.editor_tab.setSizePolicy(sizePolicy3)
        self.editor_tab.setDocumentMode(True)
        self.editor_tab.setTabsClosable(True)
        self.editor_tab.setMovable(True)
        self.editor_splitter.addWidget(self.editor_tab)
        self.vertical_splitter.addWidget(self.editor_splitter)
        self.output_window_group_box = QGroupBox(self.vertical_splitter)
        self.output_window_group_box.setObjectName("output_window_group_box")
        self.output_window_layout = QVBoxLayout(self.output_window_group_box)
        self.output_window_layout.setObjectName("output_window_layout")
        self.output_dock = QDockWidget(self.output_window_group_box)
        self.output_dock.setObjectName("output_dock")
        self.dockWidgetContents_2 = QWidget()
        self.dockWidgetContents_2.setObjectName("dockWidgetContents_2")
        self.output_dock.setWidget(self.dockWidgetContents_2)

        self.output_window_layout.addWidget(self.output_dock)

        self.vertical_splitter.addWidget(self.output_window_group_box)

        self.main_grid_layout.addWidget(self.vertical_splitter, 1, 0, 1, 1)

        self.dock_widget = QDockWidget(editor_dialog)
        self.dock_widget.setObjectName("dock_widget")
        self.dock_widget.setFloating(False)
        self.dock_widget.setFeatures(
            QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetMovable
        )
        self.dock_widget.setAllowedAreas(Qt.AllDockWidgetAreas)
        self.dockWidgetContents = QWidget()
        self.dockWidgetContents.setObjectName("dockWidgetContents")
        self.dock_widget.setWidget(self.dockWidgetContents)

        self.main_grid_layout.addWidget(self.dock_widget, 0, 0, 1, 1)

        self.retranslateUi(editor_dialog)

        self.editor_tab.setCurrentIndex(-1)

        QMetaObject.connectSlotsByName(editor_dialog)

    # setupUi

    def retranslateUi(self, editor_dialog):
        editor_dialog.setWindowTitle(
            QCoreApplication.translate("editor_dialog", "NCCA Editor", None)
        )
        self.side_bar.setTitle(
            QCoreApplication.translate("editor_dialog", "Files", None)
        )
        self.sidebar_selector.setItemText(
            0, QCoreApplication.translate("editor_dialog", "Workspace", None)
        )
        self.sidebar_selector.setItemText(
            1, QCoreApplication.translate("editor_dialog", "File System", None)
        )
        self.sidebar_selector.setItemText(
            2, QCoreApplication.translate("editor_dialog", "Code Outline", None)
        )

        self.output_window_group_box.setTitle(
            QCoreApplication.translate("editor_dialog", "Output Window", None)
        )
        self.dock_widget.setWindowTitle(
            QCoreApplication.translate("editor_dialog", "Script Controls", None)
        )

    # retranslateUi
