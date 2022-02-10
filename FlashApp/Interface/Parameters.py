from enum import Enum
from ast import literal_eval

from PyQt5 import QtCore, QtWidgets, QtGui, sip
from PyQt5.QtCore import Qt

from FlashApi.Core.Node import *
from FlashApp.Interface.Node import *


class ParmType(Enum):
    """
    Enumeration to find list different parameter types
    """
    INT = 1
    INT2 = 2
    INT3 = 3
    FLOAT = 4
    FLOAT2 = 5
    FLOAT3 = 6
    STR = 7
    BOOL = 8
    LIST = 9
    DICT = 10


def GuessParmType(parm : Parameter) -> ParmType:
    """
    Guesses a parameter type from its value

    Args:
        parm (Parameter): parameter to guess type from

    Returns:
        ParmType: parameter type enum 
    """
    if type(parm.Value()) is int: return ParmType.INT 

    elif type(parm.Value()) is float: return ParmType.FLOAT
    
    elif type(parm.Value()) is str: return ParmType.STR

    elif type(parm.Value()) is bool: return ParmType.BOOL

    elif type(parm.Value()) is list:
        if len(parm.Value()) == 2:
            if type(parm.Value()[0]) is int:
                return ParmType.INT2
            elif type(parm.Value()[0]) is float:
                return ParmType.FLOAT2
        elif len(parm.Value()) == 3:
            if type(parm.Value()[0]) is int:
                return ParmType.INT3
            elif type(parm.Value()[0]) is float:
                return ParmType.FLOAT3
        else:
            return ParmType.LIST

    elif type(parm.Value()) is dict:
        return ParmType.DICT

    else:
        raise TypeError(f"Parameter type unknown (parm : {parm.ShortName()})")


class ParameterWidget(QtWidgets.QWidget):
    """
    """

    valueChanged = QtCore.pyqtSignal()

    def __init__(self, parameter : Parameter, parent=None):
        super(QtWidgets.QWidget, self).__init__(parent)

        self.parameter = parameter
        self.parmType = GuessParmType(self.parameter)

        masterLayout = QtWidgets.QHBoxLayout()

        self.parmLongNameLabel = QtWidgets.QLabel(self.parameter.LongName())
        self.parmLongNameLabel.setMinimumWidth(40)
        masterLayout.addWidget(self.parmLongNameLabel)

        if (self.parmType == ParmType.STR or 
            self.parmType == ParmType.INT or 
            self.parmType == ParmType.FLOAT):
            self.editBox1 = QtWidgets.QLineEdit()
            self.editBox1.setText(f"{self.parameter.Value()}")
            self.editBox1.editingFinished.connect(self.onValueChanged)
            masterLayout.addWidget(self.editBox1)

        if (self.parmType == ParmType.BOOL):
            self.editBox1 = QtWidgets.QCheckBox()
            self.editBox1.setChecked(self.parameter.Value())
            self.editBox1.stateChanged.connect(self.onValueChanged)
            masterLayout.addWidget(self.editBox1)

        elif (self.parmType == ParmType.INT2 or 
              self.parmType == ParmType.FLOAT2):
            self.editBox1 = QtWidgets.QLineEdit()
            self.editBox1.editingFinished.connect(self.onValueChanged)
            self.editBox1.setText(f"{self.parameter.Value()[0]}")
            masterLayout.addWidget(self.editBox1)
            
            self.editBox2 = QtWidgets.QLineEdit()
            self.editBox2.setText(f"{self.parameter.Value()[1]}")
            self.editBox2.editingFinished.connect(self.onValueChanged)
            masterLayout.addWidget(self.editBox2)
        
        elif (self.parmType == ParmType.INT3 or 
              self.parmType == ParmType.FLOAT3):
            self.editBox1 = QtWidgets.QLineEdit()
            self.editBox1.setText(f"{self.parameter.Value()[0]}")
            self.editBox1.editingFinished.connect(self.onValueChanged)
            masterLayout.addWidget(self.editBox1)
            
            self.editBox2 = QtWidgets.QLineEdit()
            self.editBox2.setText(f"{self.parameter.Value()[1]}")
            self.editBox2.editingFinished.connect(self.onValueChanged)
            masterLayout.addWidget(self.editBox2)
            
            self.editBox3 = QtWidgets.QLineEdit()
            self.editBox3.setText(f"{self.parameter.Value()[2]}")
            self.editBox3.editingFinished.connect(self.onValueChanged)
            masterLayout.addWidget(self.editBox3)

        self.setLayout(masterLayout)

    def onValueChanged(self) -> None:
        """
        Handles the change of a value
        """
        if (self.parmType == ParmType.STR):
            editBoxValue1 = self.editBox1.text()
            self.parameter.SetValue(editBoxValue1)

        elif (self.parmType == ParmType.BOOL):
            editBoxValue1 = self.editBox1.isChecked()
            self.parameter.SetValue(editBoxValue1)

        elif (self.parmType == ParmType.INT or
            self.parmType == ParmType.FLOAT):
            editBoxValue1 = literal_eval(f"{self.editBox1.text()}")

            self.parameter.SetValue(editBoxValue1)

        elif (self.parmType == ParmType.INT2 or 
              self.parmType == ParmType.FLOAT2):
            editBoxValue1 = literal_eval(f"{self.editBox1.text()}")
            editBoxValue2 = literal_eval(f"{self.editBox2.text()}")
            
            self.parameter.SetValue([editBoxValue1, editBoxValue2])
        
        elif (self.parmType == ParmType.INT3 or 
              self.parmType == ParmType.FLOAT3):
            editBoxValue1 = literal_eval(f"{self.editBox1.text()}")
            editBoxValue2 = literal_eval(f"{self.editBox2.text()}")
            editBoxValue3 = literal_eval(f"{self.editBox3.text()}")
            
            self.parameter.SetValue([editBoxValue1, editBoxValue2, editBoxValue3])

        self.valueChanged.emit()


class ParameterEditor(QtWidgets.QWidget):
    """
    """

    currentNodeChanged = QtCore.pyqtSignal()
    parameterChanged = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super(QtWidgets.QWidget, self).__init__(parent)

        self.setMinimumWidth(350)
        self.setMaximumWidth(350)

        self.masterLayout = QtWidgets.QVBoxLayout()
        self.masterLayout.setAlignment(Qt.AlignTop)
        self.masterLayout.setSpacing(0)

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

        for parm in self.node.GetParms():
            parmWidget = ParameterWidget(parm)
            parmWidget.valueChanged.connect(self.onParameterChange)
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

        print(node.getInternalNode().GetID())

        if not self.layout() is None: self.cleanInterface()
        self.buildInterface()

    def onParameterChange(self) -> None:
        """
        """
        self.parameterChanged.emit()