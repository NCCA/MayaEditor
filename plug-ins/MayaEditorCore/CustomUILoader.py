from typing import Optional

from PySide2 import QtCore, QtGui, QtUiTools, QtWidgets

"""
Modifed from here as need close events
https://stackoverflow.com/questions/27603350/how-do-i-load-children-from-ui-file-in-pyside/27610822#27610822
"""


class UiLoader(QtUiTools.QUiLoader):
    _baseinstance = None

    def createWidget(
        self, classname: str, parent: Optional[QtWidgets.QWidget] = None, name: str = ""
    ):
        if parent is None and self._baseinstance is not None:
            widget = self._baseinstance
        else:
            widget = super(UiLoader, self).createWidget(classname, parent, name)
            if self._baseinstance is not None:
                setattr(self._baseinstance, name, widget)
        return widget

    def loadUi(self, uifile: str, baseinstance: Optional[QtWidgets.QWidget] = None):
        self._baseinstance = baseinstance
        widget = self.load(uifile)
        QtCore.QMetaObject.connectSlotsByName(widget)
        return widget
