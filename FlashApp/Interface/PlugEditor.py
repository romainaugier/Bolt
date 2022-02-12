from enum import Enum
from ast import literal_eval

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import Qt

from FlashApi.Core.Node import *
from FlashApp.Interface.Node import *
from FlashApp.Interface.Icons import *


def CleanLayout(layout : QtWidgets.QLayout) -> None:
    """
    Deletes widgets and layouts recursively

    Args:
        layout (QtWidgets.QLayout): layout to clear
    """
    if layout.count() > 0:
        while layout.count():
            item = layout.itemAt(0)
            widget = item.widget()

            if widget is not None:
                widget.setParent(None)
            else:
                CleanLayout(item.layout())


class IconLabel(QtWidgets.QWidget):
    """
    """

    IconSize = QtCore.QSize(20, 20)
    HSpacing = 10

    def __init__(self, pixmap : QtGui.QPixmap, text : str, finalStretch : bool = True):
        """
        """
        super(QtWidgets.QWidget, self).__init__()

        self.mainLayout = QtWidgets.QHBoxLayout()
        self.mainLayout.setSpacing(0)
        self.mainLayout.setAlignment(Qt.AlignLeft)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(self.mainLayout)
        
        if pixmap is not None:
            self.icon = QtWidgets.QLabel()
            self.mainLayout.addWidget(self.icon)
            self.icon.setPixmap(pixmap.scaled(self.IconSize))
            self.spacer = QtWidgets.QSpacerItem(self.HSpacing, 0)
            self.mainLayout.addSpacerItem(self.spacer)
        else:
            self.icon = None
            self.spacer = None

        self.text = QtWidgets.QLabel(text)
        self.text.setFont(QtGui.QFont("Helvetica", 14))
        self.text.setStyleSheet("color: rgb(143, 144, 160)")
        self.mainLayout.addWidget(self.text)

    def setText(self, text : str) -> None:
        """
        """
        self.text.setText(text)

    def setIcon(self, pixmap = QtGui.QPixmap) -> None:
        """
        """
        text = self.text.text()

        self.text.setParent(None)

        if self.icon is not None:
            self.icon.setParent(None)

        if self.spacer is not None:
            self.mainLayout.removeItem(self.spacer)

        if pixmap is not None:
            self.icon = QtWidgets.QLabel()
            self.mainLayout.addWidget(self.icon)
            self.icon.setPixmap(pixmap.scaled(self.IconSize))
            self.spacer = QtWidgets.QSpacerItem(self.HSpacing, 0)
            self.mainLayout.addSpacerItem(self.spacer)
        else:
            self.icon = None
            self.spacer = None

        self.text = QtWidgets.QLabel(text)
        self.text.setFont(QtGui.QFont("Helvetica", 14))
        self.text.setStyleSheet("color: rgb(143, 144, 160)")
        self.mainLayout.addWidget(self.text)


class PlugWidget(QtWidgets.QWidget):
    """
    """

    valueChanged = QtCore.pyqtSignal()

    def __init__(self, plug : Plug, parent=None):
        super(QtWidgets.QWidget, self).__init__(parent)

        self.plug = plug
        self.plugType = plug.GetType()

        masterLayout = QtWidgets.QHBoxLayout()

        masterLayout.setAlignment(Qt.AlignTop)
        masterLayout.setSpacing(0)
        masterLayout.setContentsMargins(0, 0, 0, 0)

        self.parmLongNameLabel = QtWidgets.QLabel(self.plug.GetLongName())
        self.parmLongNameLabel.setMinimumWidth(40)
        self.parmLongNameLabel.setMinimumHeight(23)
        masterLayout.addWidget(self.parmLongNameLabel)

        masterLayout.addSpacing(20)

        if (self.plugType == PlugType.STR or 
            self.plugType == PlugType.INT or 
            self.plugType == PlugType.FLOAT):
            self.editBox1 = QtWidgets.QLineEdit()
            self.editBox1.setText(f"{self.plug.GetData()}")
            self.editBox1.editingFinished.connect(self.onValueChanged)
            masterLayout.addWidget(self.editBox1)

        if (self.plugType == PlugType.BOOL):
            self.editBox1 = QtWidgets.QCheckBox()
            self.editBox1.setChecked(self.plug.GetData())
            self.editBox1.stateChanged.connect(self.onValueChanged)
            masterLayout.addWidget(self.editBox1)

        elif (self.plugType == PlugType.INT2 or 
              self.plugType == PlugType.FLOAT2):
            self.editBox1 = QtWidgets.QLineEdit()
            self.editBox1.editingFinished.connect(self.onValueChanged)
            self.editBox1.setText(f"{self.plug.GetData()[0]}")
            masterLayout.addWidget(self.editBox1)
            
            self.editBox2 = QtWidgets.QLineEdit()
            self.editBox2.setText(f"{self.plug.GetData()[1]}")
            self.editBox2.editingFinished.connect(self.onValueChanged)
            masterLayout.addWidget(self.editBox2)
        
        elif (self.plugType == PlugType.INT3 or 
              self.plugType == PlugType.FLOAT3):
            self.editBox1 = QtWidgets.QLineEdit()
            self.editBox1.setText(f"{self.plug.GetData()[0]}")
            self.editBox1.editingFinished.connect(self.onValueChanged)
            masterLayout.addWidget(self.editBox1)
            
            self.editBox2 = QtWidgets.QLineEdit()
            self.editBox2.setText(f"{self.plug.GetData()[1]}")
            self.editBox2.editingFinished.connect(self.onValueChanged)
            masterLayout.addWidget(self.editBox2)
            
            self.editBox3 = QtWidgets.QLineEdit()
            self.editBox3.setText(f"{self.plug.GetData()[2]}")
            self.editBox3.editingFinished.connect(self.onValueChanged)
            masterLayout.addWidget(self.editBox3)

        self.setLayout(masterLayout)

    def onValueChanged(self) -> None:
        """
        Handles the change of a value
        """
        if (self.plugType == PlugType.STR):
            editBoxValue1 = self.editBox1.text()
            self.plug.SetData(editBoxValue1)

        elif (self.plugType == PlugType.BOOL):
            editBoxValue1 = self.editBox1.isChecked()
            self.plug.SetData(editBoxValue1)

        elif (self.plugType == PlugType.INT or
            self.plugType == PlugType.FLOAT):
            editBoxValue1 = literal_eval(f"{self.editBox1.text()}")

            self.plug.SetData(editBoxValue1)

        elif (self.plugType == PlugType.INT2 or 
              self.plugType == PlugType.FLOAT2):
            editBoxValue1 = literal_eval(f"{self.editBox1.text()}")
            editBoxValue2 = literal_eval(f"{self.editBox2.text()}")
            
            self.plug.SetData([editBoxValue1, editBoxValue2])
        
        elif (self.plugType == PlugType.INT3 or 
              self.plugType == PlugType.FLOAT3):
            editBoxValue1 = literal_eval(f"{self.editBox1.text()}")
            editBoxValue2 = literal_eval(f"{self.editBox2.text()}")
            editBoxValue3 = literal_eval(f"{self.editBox3.text()}")
            
            self.plug.SetData([editBoxValue1, editBoxValue2, editBoxValue3])

        self.valueChanged.emit()


class PlugEditor(QtWidgets.QWidget):
    """
    """

    currentNodeChanged = QtCore.pyqtSignal()
    plugChanged = QtCore.pyqtSignal()

    def __init__(self, iconsLib = Icons, parent=None):
        super(QtWidgets.QWidget, self).__init__(parent)

        self.iconsLib = iconsLib

        self._width = 350

        self.setMinimumWidth(self._width)
        self.setMaximumWidth(self._width)

        self.masterLayout = QtWidgets.QVBoxLayout()
        self.masterLayout.setAlignment(Qt.AlignTop)

        self.nodeNameLabel = IconLabel(None, "None")
        self.masterLayout.addWidget(self.nodeNameLabel)

        self.plugsLayout = QtWidgets.QVBoxLayout()
        self.plugsLayout.setAlignment(Qt.AlignTop)
        self.plugsLayout.setSpacing(0)
        self.plugsLayout.setContentsMargins(0, 0, 0, 0)
        self.masterLayout.addLayout(self.plugsLayout)

        self.setLayout(self.masterLayout)

    def getWidth(self) -> float:
        """
        """
        return self._width

    def cleanInterface(self) -> None:
        """
        Clears the interface
        """
        CleanLayout(self.plugsLayout)

    def buildInterface(self) -> None:
        """
        Build the interface for the given node
        """
        # layout = QtWidgets.QVBoxLayout()

        for plugName, plug in self.node.GetInputs().items():
            if plug.IsExposed():
                parmWidget = PlugWidget(plug)
                parmWidget.valueChanged.connect(self.onPlugChange)
                self.plugsLayout.addWidget(parmWidget)

        # self.setLayout(layout)

    @QtCore.pyqtSlot(GNode)
    def setCurrentNode(self, node : GNode) -> None:
        """
        Sets the current node of the editor

        Args:
            node (Node): node to edit parameters
        """
        self.node = node.getInternalNode()
        self.currentNodeChanged.emit()

        self.nodeNameLabel.setText(self.node.GetName())
        self.nodeNameLabel.setIcon(node.getPixmap())

        if not self.layout() is None: self.cleanInterface()
        self.buildInterface()

    def onPlugChange(self) -> None:
        """
        """
        self.plugChanged.emit()