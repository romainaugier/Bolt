from enum import Enum
from ast import literal_eval

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import Qt

from FlashApi.Core.Node import *
from FlashApp.Interface.Node import *


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

    def __init__(self, parent=None):
        super(QtWidgets.QWidget, self).__init__(parent)

        self.setMinimumWidth(350)
        self.setMaximumWidth(350)

        self.masterLayout = QtWidgets.QVBoxLayout()
        self.masterLayout.setAlignment(Qt.AlignTop)
        self.masterLayout.setSpacing(0)
        self.masterLayout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(self.masterLayout)

    def cleanLayout(self, layout : QtWidgets.QLayout) -> None:
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
                    self.cleanLayout(item.layout())

            # sip.delete(layout)

    def cleanInterface(self) -> None:
        """
        Clears the interface
        """
        self.cleanLayout(self.masterLayout)

    def buildInterface(self) -> None:
        """
        Build the interface for the given node
        """
        # layout = QtWidgets.QVBoxLayout()

        for plugName, plug in self.node.GetInputs().items():
            if plug.IsExposed():
                parmWidget = PlugWidget(plug)
                parmWidget.valueChanged.connect(self.onPlugChange)
                self.masterLayout.addWidget(parmWidget)

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

        if not self.layout() is None: self.cleanInterface()
        self.buildInterface()

    def onPlugChange(self) -> None:
        """
        """
        self.plugChanged.emit()