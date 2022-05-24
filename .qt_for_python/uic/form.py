# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'form.ui'
##
## Created by: Qt User Interface Compiler version 6.2.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QDialog, QGridLayout, QGroupBox,
    QHeaderView, QPlainTextEdit, QSizePolicy, QSplitter,
    QTabWidget, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
    QWidget)

class Ui_editor_dialog(object):
    def setupUi(self, editor_dialog):
        if not editor_dialog.objectName():
            editor_dialog.setObjectName(u"editor_dialog")
        editor_dialog.resize(995, 705)
        self.main_grid_layout = QGridLayout(editor_dialog)
        self.main_grid_layout.setObjectName(u"main_grid_layout")
        self.output_window = QPlainTextEdit(editor_dialog)
        self.output_window.setObjectName(u"output_window")

        self.main_grid_layout.addWidget(self.output_window, 1, 0, 1, 1)

        self.splitter = QSplitter(editor_dialog)
        self.splitter.setObjectName(u"splitter")
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(2)
        sizePolicy.setHeightForWidth(self.splitter.sizePolicy().hasHeightForWidth())
        self.splitter.setSizePolicy(sizePolicy)
        self.splitter.setOrientation(Qt.Horizontal)
        self.groupBox = QGroupBox(self.splitter)
        self.groupBox.setObjectName(u"groupBox")
        sizePolicy1 = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(2)
        sizePolicy1.setHeightForWidth(self.groupBox.sizePolicy().hasHeightForWidth())
        self.groupBox.setSizePolicy(sizePolicy1)
        self.verticalLayout = QVBoxLayout(self.groupBox)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.open_files = QTreeWidget(self.groupBox)
        __qtreewidgetitem = QTreeWidgetItem()
        __qtreewidgetitem.setText(0, u"1");
        self.open_files.setHeaderItem(__qtreewidgetitem)
        self.open_files.setObjectName(u"open_files")
        sizePolicy2 = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(1)
        sizePolicy2.setHeightForWidth(self.open_files.sizePolicy().hasHeightForWidth())
        self.open_files.setSizePolicy(sizePolicy2)

        self.verticalLayout.addWidget(self.open_files)

        self.splitter.addWidget(self.groupBox)
        self.editor_tab = QTabWidget(self.splitter)
        self.editor_tab.setObjectName(u"editor_tab")
        sizePolicy3 = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sizePolicy3.setHorizontalStretch(1)
        sizePolicy3.setVerticalStretch(1)
        sizePolicy3.setHeightForWidth(self.editor_tab.sizePolicy().hasHeightForWidth())
        self.editor_tab.setSizePolicy(sizePolicy3)
        self.splitter.addWidget(self.editor_tab)

        self.main_grid_layout.addWidget(self.splitter, 0, 0, 1, 1)


        self.retranslateUi(editor_dialog)

        self.editor_tab.setCurrentIndex(-1)


        QMetaObject.connectSlotsByName(editor_dialog)
    # setupUi

    def retranslateUi(self, editor_dialog):
        editor_dialog.setWindowTitle(QCoreApplication.translate("editor_dialog", u"NCCA Editor", None))
        self.groupBox.setTitle(QCoreApplication.translate("editor_dialog", u"Files", None))
    # retranslateUi

