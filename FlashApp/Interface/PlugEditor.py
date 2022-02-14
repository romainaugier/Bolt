from ast import literal_eval

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import Qt

from FlashApi.Core.Node import *
from FlashApp.Interface.GNode import *
from FlashApp.Interface.Icons import *
from FlashApp.Interface.Widgets import *
from FlashApp.Interface.Utils import *
from FlashApp.Interface.Style import *


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
        self.parmLongNameLabel.setFont(QtGui.QFont("Helvetica", 8))
        self.parmLongNameLabel.setStyleSheet(QColorToStyleSheet(GetQColorFromPalette(ColorPalette.FOREGROUND)))
        self.parmLongNameLabel.setMinimumWidth(40)
        self.parmLongNameLabel.setMinimumHeight(23)
        self.labelSize = self.parmLongNameLabel.width()
        masterLayout.addWidget(self.parmLongNameLabel)

        masterLayout.addSpacing(10)

        if (self.plugType == PlugType.STR or 
            self.plugType == PlugType.INT or 
            self.plugType == PlugType.FLOAT):
            self.editBox1 = LineEdit()
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
            self.editBox1 = LineEdit()
            self.editBox1.editingFinished.connect(self.onValueChanged)
            self.editBox1.setText(f"{self.plug.GetData()[0]}")
            masterLayout.addWidget(self.editBox1)
            
            self.editBox2 = LineEdit()
            self.editBox2.setText(f"{self.plug.GetData()[1]}")
            self.editBox2.editingFinished.connect(self.onValueChanged)
            masterLayout.addWidget(self.editBox2)
        
        elif (self.plugType == PlugType.INT3 or 
              self.plugType == PlugType.FLOAT3):
            self.editBox1 = LineEdit()
            self.editBox1.setText(f"{self.plug.GetData()[0]}")
            self.editBox1.editingFinished.connect(self.onValueChanged)
            masterLayout.addWidget(self.editBox1)
            
            self.editBox2 = LineEdit()
            self.editBox2.setText(f"{self.plug.GetData()[1]}")
            self.editBox2.editingFinished.connect(self.onValueChanged)
            masterLayout.addWidget(self.editBox2)
            
            self.editBox3 = LineEdit()
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


class PlugListWidgetInstance(QtWidgets.QWidget):
    """
    Class used to design instance of plug widgets for the list widget
    (each instance is a list item)
    """

    valueChanged = QtCore.pyqtSignal()
    needToBeClosed = QtCore.pyqtSignal(int)

    def __init__(self, index : int, value, parent=None):
        super().__init__(parent)

        self.index = index

        masterLayout = QtWidgets.QHBoxLayout()

        masterLayout.setAlignment(Qt.AlignTop)
        masterLayout.setSpacing(0)
        masterLayout.setContentsMargins(0, 0, 0, 0)

        self.parmLongNameLabel = QtWidgets.QLabel(f"Item {index}")
        self.parmLongNameLabel.setFont(QtGui.QFont("Helvetica", 8))
        self.parmLongNameLabel.setStyleSheet(QColorToStyleSheet(GetQColorFromPalette(ColorPalette.FOREGROUND)))
        self.parmLongNameLabel.setMinimumWidth(40)
        self.parmLongNameLabel.setMinimumHeight(23)
        self.labelSize = self.parmLongNameLabel.width()
        masterLayout.addWidget(self.parmLongNameLabel)

        masterLayout.addSpacing(5)

        self.editBox = LineEdit()
        self.editBox.setText(f"{value}")
        self.editBox.editingFinished.connect(self.onValueChanged)
        masterLayout.addWidget(self.editBox)
        
        masterLayout.addSpacing(5)

        self.closeButton = QtWidgets.QPushButton("X")
        self.closeButton.setFixedSize(14, 14)
        self.closeButton.clicked.connect(self.closeWidget)
        masterLayout.addWidget(self.closeButton)

        self.setLayout(masterLayout)

    def onValueChanged(self) -> None:
        """
        """
        self.valueChanged.emit()

    def closeWidget(self) -> None:
        """
        """
        self.needToBeClosed.emit(self.index)

    def getValue(self):
        """
        """
        text = self.editBox.text()

        try:
            value = literal_eval(text)
        except:
            value = text

        return value


class PlugDictWidgetInstance(PlugListWidgetInstance):
    """
    """
    def __init__(self, index : int, key, value, parent=None):
            super().__init__(parent)

            self.index = index

            masterLayout = QtWidgets.QHBoxLayout()

            masterLayout.setAlignment(Qt.AlignTop)
            masterLayout.setSpacing(0)
            masterLayout.setContentsMargins(0, 0, 0, 0)

            self.keyLabel = QtWidgets.QLabel(f"{key}")
            self.keyLabel.setFont(QtGui.QFont("Helvetica", 8))
            self.keyLabel.setStyleSheet(QColorToStyleSheet(GetQColorFromPalette(ColorPalette.FOREGROUND)))
            self.keyLabel.setMinimumWidth(40)
            self.keyLabel.setMinimumHeight(23)
            self.labelSize = self.keyLabel.width()
            masterLayout.addWidget(self.keyLabel)

            masterLayout.addSpacing(5)

            self.editBox = LineEdit()
            self.editBox.setText(f"{value}")
            self.editBox.editingFinished.connect(self.onValueChanged)
            masterLayout.addWidget(self.editBox)
            
            masterLayout.addSpacing(5)

            self.closeButton = QtWidgets.QPushButton("X")
            self.closeButton.setFixedSize(14, 14)
            self.closeButton.clicked.connect(self.closeWidget)
            masterLayout.addWidget(self.closeButton)

            self.setLayout(masterLayout)


class PlugListWidget(QtWidgets.QWidget):
    """
    Class used to design an editor for list plugs
    """

    valueChanged = QtCore.pyqtSignal()
    interfaceChanged = QtCore.pyqtSignal()

    def __init__(self, plug : Plug, parent=None):
        super(QtWidgets.QWidget, self).__init__(parent)

        self.plug = plug
        self.plugType = plug.GetType()

        self.masterLayout = QtWidgets.QVBoxLayout()

        topLayout = QtWidgets.QHBoxLayout()

        topLayout.setAlignment(Qt.AlignTop)
        topLayout.setSpacing(0)
        topLayout.setContentsMargins(0, 0, 0, 0)

        self.parmLongNameLabel = QtWidgets.QLabel(self.plug.GetLongName())
        self.parmLongNameLabel.setFont(QtGui.QFont("Helvetica", 8))
        self.parmLongNameLabel.setStyleSheet(QColorToStyleSheet(GetQColorFromPalette(ColorPalette.FOREGROUND)))
        self.parmLongNameLabel.setMinimumWidth(40)
        self.parmLongNameLabel.setMinimumHeight(23)
        self.labelSize = self.parmLongNameLabel.width()
        topLayout.addWidget(self.parmLongNameLabel)

        topLayout.addStretch()

        self.addInstanceButton = QtWidgets.QPushButton("+")
        self.addInstanceButton.setFixedSize(20, 20)
        self.addInstanceButton.clicked.connect(self.addInstance)
        topLayout.addWidget(self.addInstanceButton)

        topLayout.addSpacing(2)

        self.removeInstanceButton = QtWidgets.QPushButton("-")
        self.removeInstanceButton.setFixedSize(20, 20)
        self.removeInstanceButton.clicked.connect(lambda : self.removeInstance())
        topLayout.addWidget(self.removeInstanceButton)

        self.masterLayout.addLayout(topLayout)

        self.instanceLayout = QtWidgets.QVBoxLayout()

        self.masterLayout.addLayout(self.instanceLayout)

        self.setLayout(self.masterLayout)

        for item in self.plug.GetData():
            self.addInstance(item)

    def addInstance(self, value = None) -> None:
        """
        """
        index = self.instanceLayout.count()

        newInstance = PlugListWidgetInstance(index, value)
        newInstance.valueChanged.connect(self.onValueChange)
        newInstance.needToBeClosed.connect(lambda: self.removeInstance(index))

        self.instanceLayout.addWidget(newInstance)

        self.interfaceChanged.emit()

        self.onValueChange()

    @QtCore.pyqtSlot(int)
    def removeInstance(self, index : int = None) -> None:
        """
        """
        if index is None:
            index = self.instanceLayout.count() - 1
        
        widget = self.instanceLayout.itemAt(index).widget()

        if widget is not None:
            widget.setParent(None)
        
        self.interfaceChanged.emit()

        self.onValueChange()

    def onValueChange(self) -> None:
        """
        """
        itemCount = self.instanceLayout.count()

        data = []

        for i in range(itemCount):
            widget = self.instanceLayout.itemAt(i).widget()

            if widget is not None:
                value = widget.getValue()
                data.append(value)

        self.plug.SetData(data)

        self.valueChanged.emit()


class PlugEditor(QtWidgets.QWidget):
    """
    """

    currentNodeChanged = QtCore.pyqtSignal()
    plugChanged = QtCore.pyqtSignal()
    resized = QtCore.pyqtSignal()

    def __init__(self, iconsLib : Icons, parent=None):
        super(QtWidgets.QWidget, self).__init__(parent)

        self.iconsLib = iconsLib

        self._width = 350

        self.setMinimumWidth(self._width)
        self.setMaximumWidth(self._width)

        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding
        )

        self.setAutoFillBackground(True)
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)

        self.masterLayout = QtWidgets.QVBoxLayout()
        self.masterLayout.setAlignment(Qt.AlignTop)
        
        topLayout = QtWidgets.QHBoxLayout()
        topLayout.setSpacing(0)
        topLayout.setContentsMargins(0, 0, 0, 0)

        self.nodeNameLabel = IconLabel(None, "None")
        topLayout.addWidget(self.nodeNameLabel)

        topLayout.addStretch()

        self.showButton = QtWidgets.QPushButton("")
        self.showButton.setIcon(self.iconsLib.GetIcon("arrow-down"))
        self.showButton.setMinimumSize(20, 20)
        self.showButton.setMaximumSize(20, 20)
        self.showButton.clicked.connect(self.showPlugsAndInfos)
        topLayout.addWidget(self.showButton)

        self.masterLayout.addLayout(topLayout)

        self.plugsLayout = QtWidgets.QVBoxLayout()
        self.plugsLayout.setAlignment(Qt.AlignTop)
        self.plugsLayout.setSpacing(0)
        self.plugsLayout.setContentsMargins(0, 0, 0, 0)
        self.plugsLayout.setSizeConstraint(QtWidgets.QLayout.SetFixedSize)

        self.plugsWidget = QtWidgets.QWidget()
        self.plugsWidget.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding
        )
        self.plugsWidget.setLayout(self.plugsLayout)
        self.masterLayout.addWidget(self.plugsWidget)

        self.setLayout(self.masterLayout)

        self.setStyleSheet("""
        QWidget {
            background-color: rgb(13, 14, 25);
        }

        QFrame {
            color: rgb(74, 82, 107);
        }

        QLabel {
            color: rgb(143, 144, 160);
            border-radius: 0px;
        }

        QLineEdit {
            color: rgba(234, 235, 255, 180);
            background-color: rgb(69, 74, 92);
            border: none;
            border-radius: 0px;
            selection-color: rgb(255, 255, 255);
            selection-background-color : rgb(64, 69, 102);
        }
        QPushButton {
            color: rgb(143, 144, 160);
            background-color: rgba(74, 82, 107, 63);
            height: 40;
            width: 40;
            qproperty-iconSize: 25px;
            border-radius: 4px;
        }

        QPushButton:hover:!pressed {
            color: rgb(143, 144, 160);
            background-color: rgba(74, 82, 107, 127);
        }
        """)

        self.resized.connect(self.adjust)

        self.adjust()

    def getWidth(self) -> float:
        """
        """
        return self._width

    def roundCorners(self) -> None:
        """
        """        
        radius = 10.0
        path = QtGui.QPainterPath()
        path.addRoundedRect(QtCore.QRectF(self.rect()), radius, radius)
        mask = QtGui.QRegion(path.toFillPolygon().toPolygon())
        self.setMask(mask)
        
    def adjust(self) -> None:
        """
        """
        QtCore.QTimer.singleShot(0, self.plugsWidget.adjustSize)
        QtCore.QTimer.singleShot(5, self.adjustSize)
        QtCore.QTimer.singleShot(10, self.updateGeometry)
        QtCore.QTimer.singleShot(15, self.roundCorners)

    def showPlugsAndInfos(self) -> None:
        """
        """
        if self.plugsWidget.isHidden():
            self.plugsWidget.show()
            self.showButton.setIcon(self.iconsLib.GetIcon("arrow-down"))
        else:
            self.plugsWidget.hide()
            self.showButton.setIcon(self.iconsLib.GetIcon("arrow-left"))

        self.resized.emit()

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

        plugCount = 0

        sep = QHLine()
        sep.setLineWidth(2)
        sep.setMinimumWidth(self._width - 20)
        sep.setColor(GetQColorFromPalette(ColorPalette.TEXT))
        self.plugsLayout.addWidget(sep)

        for plugName, plug in self.node.GetInputs().items():
            if plug.IsExposed():
                if plug.GetType() == PlugType.LIST:
                    plugWidget = PlugListWidget(plug)
                    plugWidget.interfaceChanged.connect(self.adjust)
                else:
                    plugWidget = PlugWidget(plug)

                plugWidget.valueChanged.connect(self.onPlugChange)
                self.plugsLayout.addWidget(plugWidget)

                plugCount += 1

        if plugCount == 0:
            infoLabel = QtWidgets.QLabel("No exposed plug available on this node")
            infoLabel.setFont(QtGui.QFont("Helvetica", 8))
            infoLabel.setStyleSheet(QColorToStyleSheet(GetQColorFromPalette(ColorPalette.FOREGROUND)))
            self.plugsLayout.addWidget(infoLabel)

    @QtCore.pyqtSlot(GNode)
    def setCurrentNode(self, node : GNode = None) -> None:
        """
        Sets the current node of the editor

        Args:
            node (Node): node to edit parameters. Defaults to None.
        """
        if node is not None:
            self.node = node.getInternalNode()
            self.currentNodeChanged.emit()

            self.nodeNameLabel.setText(self.node.GetName())
            self.nodeNameLabel.setIcon(node.getPixmap())

            if not self.layout() is None: self.cleanInterface()

            self.buildInterface()

        else:
            if not self.layout() is None: self.cleanInterface()
            self.nodeNameLabel.setText("None")
            self.nodeNameLabel.setIcon(None)

        self.resized.emit()

    def onPlugChange(self) -> None:
        """
        """
        self.plugChanged.emit()