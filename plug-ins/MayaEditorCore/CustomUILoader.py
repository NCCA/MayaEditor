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
"""
This class is used to create a better loader from PySide so that  we can access the events better.

Modifed from here as need close events
https://stackoverflow.com/questions/27603350/how-do-i-load-children-from-ui-file-in-pyside/27610822#27610822
"""

from typing import Optional

from PySide2 import QtCore, QtGui, QtUiTools, QtWidgets


class UiLoader(QtUiTools.QUiLoader):
    """UiLoader class similar to the one in PyQt."""

    _baseinstance = None

    def createWidget(
        self, classname: str, parent: Optional[QtWidgets.QWidget] = None, name: str = ""
    ):
        """Create a new widget from classname.

        This is called when the widget is created from the load.
        Parameters :
        classname (str) : name of the class to create
        parent (QWidget) : the parent to associate the loaded widgets with
        name (str) : name of the widget

        Returns : a new widget

        """
        if parent is None and self._baseinstance is not None:
            widget = self._baseinstance
        else:
            widget = super(UiLoader, self).createWidget(classname, parent, name)
            if self._baseinstance is not None:
                setattr(self._baseinstance, name, widget)
        return widget

    def loadUi(self, uifile: str, baseinstance: Optional[QtWidgets.QWidget] = None):
        """Load a ui file and associate with a class.

        Load in a ui and allow the events to be added to the parent passed in, this replicates the functionality of the PyQt version.

        Parameters :
        uifile (str) : the full path of the file to read in
        baseinstance (QWidget) : parent to associate the class to
        Returns : a widget
        """
        self._baseinstance = baseinstance
        widget = self.load(uifile)
        QtCore.QMetaObject.connectSlotsByName(widget)
        return widget
