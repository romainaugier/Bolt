from ast import literal_eval

from PyQt5 import QtCore, QtWidgets

from FlashApi.Utils.String import Increment
from FlashApp.Interface.PlugEditor import *

class AttributeEditor(QtWidgets.QWidget):
    """
    Interface to edit the main attributes of a node
    """
    def __init__(self, nodeToEditAsDict : dict, parent = None):
        """
        """
        super().__init__(parent=parent)
        
        masterLayout = QtWidgets.QVBoxLayout()
        
        self.savePathWidget = LabeledLineEdit("Save Path", "")
        self.savePathWidget.getLabel().setMinimumWidth(60)
        self.savePathWidget.getLineEdit().setMinimumWidth(200)
        masterLayout.addWidget(self.savePathWidget)
        
        self.nameWidget = LabeledLineEdit("Name", "")
        self.nameWidget.getLabel().setMinimumWidth(60)
        self.nameWidget.getLineEdit().setMinimumWidth(200)
        masterLayout.addWidget(self.nameWidget)
        
        self.iconWidget = LabeledLineEdit("Icon", "")
        self.iconWidget.getLabel().setMinimumWidth(60)
        self.iconWidget.getLineEdit().setMinimumWidth(200)
        masterLayout.addWidget(self.iconWidget)
        
        self.categoryWidget = LabeledLineEdit("Category", "")
        self.categoryWidget.getLabel().setMinimumWidth(60)
        self.categoryWidget.getLineEdit().setMinimumWidth(200)
        masterLayout.addWidget(self.categoryWidget)
        
        self.setNodeToEdit(nodeToEditAsDict)
        
        self.setLayout(masterLayout)
        
    def setNodeToEdit(self, nodeToEditAsDict : dict) -> None:
        """
        """
        name = nodeToEditAsDict["name"]
        icon = nodeToEditAsDict["iconPath"]
        category = nodeToEditAsDict["category"]
        savePath = nodeToEditAsDict["definitionPath"]
            
        self.savePathWidget.getLineEdit().setText(savePath)
        self.nameWidget.getLineEdit().setText(name)
        self.iconWidget.getLineEdit().setText(icon)
        self.categoryWidget.getLineEdit().setText(category)
        
    def getSavePath(self) -> str:
        """
        """
        return self.savePathWidget.getLineEdit().text()
        
    def getName(self) -> str:
        """
        """
        return self.nameWidget.getLineEdit().text()
    
    def getIcon(self) -> str:
        """
        """
        return self.iconWidget.getLineEdit().text()
    
    def getCategory(self) -> str:
        """
        """
        return self.categoryWidget.getLineEdit().text()

    def cleanup(self) -> None:
        """
        """
        pass
    
    
class PlugValueWidget(QtWidgets.QWidget):
    """
    """

    valueChanged = QtCore.pyqtSignal(object)

    def __init__(self, plugType : int, data = None, parent=None):
        super(QtWidgets.QWidget, self).__init__(parent)

        self.plugType = plugType
        
        if data is None: 
            data = ""
            
            if self.plugType == PlugType.INT2 or self.plugType == PlugType.FLOAT2:
                data = ["", ""]
            elif self.plugType == PlugType.INT3 or self.plugType == PlugType.FLOAT3:
                data = ["", "", ""]
            elif self.plugType == PlugType.BOOL:
                data = False

        self.masterLayout = QtWidgets.QHBoxLayout()

        self.masterLayout.setAlignment(Qt.AlignTop)
        self.masterLayout.setSpacing(0)
        self.masterLayout.setContentsMargins(0, 0, 0, 0)

        self.masterLayout.addSpacing(10)

        self.setLayout(self.masterLayout)

        self.setData(plugType, data)
        
    def setData(self, plugType : PlugType, data = None) -> None:
        """
        """
        self.plugType = plugType
        
        if data is None: 
            data = ""
            
            if self.plugType == PlugType.INT2 or self.plugType == PlugType.FLOAT2:
                data = ["", ""]
            elif self.plugType == PlugType.INT3 or self.plugType == PlugType.FLOAT3:
                data = ["", "", ""]
            elif self.plugType == PlugType.BOOL:
                data = False
        
        if not type(data) is list and (self.plugType == PlugType.INT2 or self.plugType == PlugType.FLOAT2):
            data = ["", ""]
        elif not type(data) is list and (self.plugType == PlugType.INT3 or self.plugType == PlugType.FLOAT3):
            data = ["", "", ""]
        elif not type(data) is bool and self.plugType == PlugType.BOOL:
            data = False
        
        if self.masterLayout is not None:
            while self.masterLayout.count():
                item = self.masterLayout.itemAt(0)
                
                if isinstance(item, QtWidgets.QWidgetItem):
                    item.widget().setParent(None)
                    # item.widget().close()
                elif isinstance(item, QtWidgets.QSpacerItem):
                    self.masterLayout.removeItem(item)

        if (self.plugType == PlugType.STR or 
            self.plugType == PlugType.INT or 
            self.plugType == PlugType.FLOAT):
            self.editBox1 = LineEdit()
            self.editBox1.setText(f"{data}")
            self.editBox1.editingFinished.connect(self.onValueChanged)
            self.masterLayout.addWidget(self.editBox1)

        if (self.plugType == PlugType.BOOL):
            self.masterLayout.addStretch()
            self.editBox1 = QtWidgets.QCheckBox()
            self.editBox1.setChecked(data)
            self.editBox1.stateChanged.connect(self.onValueChanged)
            self.masterLayout.addWidget(self.editBox1)

        elif (self.plugType == PlugType.INT2 or 
              self.plugType == PlugType.FLOAT2):
            self.editBox1 = LineEdit()
            self.editBox1.editingFinished.connect(self.onValueChanged)
            self.editBox1.setText(f"{data[0]}")
            self.masterLayout.addWidget(self.editBox1)

            self.masterLayout.addSpacing(5)
            
            self.editBox2 = LineEdit()
            self.editBox2.setText(f"{data[1]}")
            self.editBox2.editingFinished.connect(self.onValueChanged)
            self.masterLayout.addWidget(self.editBox2)
        
        elif (self.plugType == PlugType.INT3 or 
              self.plugType == PlugType.FLOAT3):
            self.editBox1 = LineEdit()
            self.editBox1.setText(f"{data[0]}")
            self.editBox1.editingFinished.connect(self.onValueChanged)
            self.masterLayout.addWidget(self.editBox1)
            
            self.masterLayout.addSpacing(5)
            
            self.editBox2 = LineEdit()
            self.editBox2.setText(f"{data[1]}")
            self.editBox2.editingFinished.connect(self.onValueChanged)
            self.masterLayout.addWidget(self.editBox2)
            
            self.masterLayout.addSpacing(5)
            
            self.editBox3 = LineEdit()
            self.editBox3.setText(f"{data[2]}")
            self.editBox3.editingFinished.connect(self.onValueChanged)
            self.masterLayout.addWidget(self.editBox3)

    def onValueChanged(self) -> None:
        """
        Handles the change of a value
        """
        if (self.plugType == PlugType.STR):
            editBoxValue1 = self.editBox1.text()
            self.valueChanged.emit(editBoxValue1)

        elif (self.plugType == PlugType.BOOL):
            editBoxValue1 = self.editBox1.isChecked()
            self.valueChanged.emit(editBoxValue1)

        elif (self.plugType == PlugType.INT or
            self.plugType == PlugType.FLOAT):
            try:
                editBoxValue1 = literal_eval(f"{self.editBox1.text()}")

                self.valueChanged.emit(editBoxValue1)
            except:
                self.valueChanged.emit(0)

        elif (self.plugType == PlugType.INT2 or 
              self.plugType == PlugType.FLOAT2):
            try:
                editBoxValue1 = literal_eval(f"{self.editBox1.text()}")
                editBoxValue2 = literal_eval(f"{self.editBox2.text()}")
                
                self.valueChanged.emit([editBoxValue1, editBoxValue2])
            except:
                self.valueChanged.emit([0, 0])
        
        elif (self.plugType == PlugType.INT3 or 
              self.plugType == PlugType.FLOAT3):
            try:
                editBoxValue1 = literal_eval(f"{self.editBox1.text()}")
                editBoxValue2 = literal_eval(f"{self.editBox2.text()}")
                editBoxValue3 = literal_eval(f"{self.editBox3.text()}")
                
                self.valueChanged.emit([editBoxValue1, editBoxValue2, editBoxValue3])
            except:
                self.valueChanged.emit([0, 0, 0])
        
    def getValue(self):
        """
        """
        if (self.plugType == PlugType.STR):
            editBoxValue1 = self.editBox1.text()
            return editBoxValue1

        elif (self.plugType == PlugType.BOOL):
            editBoxValue1 = self.editBox1.isChecked()
            return editBoxValue1

        elif (self.plugType == PlugType.INT or
            self.plugType == PlugType.FLOAT):
            try:
                editBoxValue1 = literal_eval(f"{self.editBox1.text()}")
                return editBoxValue1
            except:
                return 0

        elif (self.plugType == PlugType.INT2 or 
              self.plugType == PlugType.FLOAT2):
            try:
                editBoxValue1 = literal_eval(f"{self.editBox1.text()}")
                editBoxValue2 = literal_eval(f"{self.editBox2.text()}")
                return [editBoxValue1, editBoxValue2]
            except:
                return [0, 0]
        
        elif (self.plugType == PlugType.INT3 or 
              self.plugType == PlugType.FLOAT3):
            try:
                editBoxValue1 = literal_eval(f"{self.editBox1.text()}")
                editBoxValue2 = literal_eval(f"{self.editBox2.text()}")
                editBoxValue3 = literal_eval(f"{self.editBox3.text()}")
                return [editBoxValue1, editBoxValue2, editBoxValue3]
            except:
                return [0, 0, 0]
    
    
class PlugPropertiesEditor(QtWidgets.QWidget):
    """
    Interface to edit the properties of a plug
    """
    
    plugDataChanged = QtCore.pyqtSignal(dict)
    
    def __init__(self, plugData : dict = None, parent = None):
        """
        """
        super().__init__(parent=parent)
        
        masterLayout = QtWidgets.QVBoxLayout()
        masterLayout.setAlignment(QtCore.Qt.AlignTop)
        
        self.longNameWidget = LabeledLineEdit("Long Name", "")
        self.longNameWidget.getLineEdit().editingFinished.connect(self.dataChanged)
        masterLayout.addWidget(self.longNameWidget)
        
        self.typeWidget = LabeledComboBox("Type")
        self.typeWidget.getComboBox().addItems(["INT","INT2","INT3",
                                                "FLOAT","FLOAT2","FLOAT3",
                                                "STR","BOOL",
                                                "LIST","DICT","CUSTOM"])
        self.typeWidget.getComboBox().setMinimumWidth(100)
        self.typeWidget.getComboBox().currentIndexChanged.connect(lambda: (self.dataChanged(), self.updateValueWidget()))
        masterLayout.addWidget(self.typeWidget)
        
        self.exposedWidget = LabeledCheckBox("Exposed")
        self.exposedWidget.getCheckBox().stateChanged.connect(self.dataChanged)
        masterLayout.addWidget(self.exposedWidget)
        
        self.hiddenWidget = LabeledCheckBox("Hidden")
        self.hiddenWidget.getCheckBox().stateChanged.connect(self.dataChanged)
        masterLayout.addWidget(self.hiddenWidget)
        
        self.exposedToGraphWidget = LabeledCheckBox("Exposed To Graph")
        self.exposedToGraphWidget.getCheckBox().stateChanged.connect(self.dataChanged)
        masterLayout.addWidget(self.exposedToGraphWidget)
        
        valueLayout = QtWidgets.QHBoxLayout()
        self.valueLabel = QtWidgets.QLabel("Default Value")
        valueLayout.addWidget(self.valueLabel)
        
        valueLayout.addSpacing(5)
        
        self.valueWidget = PlugValueWidget(1)
        self.valueWidget.valueChanged.connect(self.valueChanged)
        valueLayout.addWidget(self.valueWidget)
        masterLayout.addLayout(valueLayout)
        
        self.updatePlugData(plugData)
        
        self.setLayout(masterLayout)
        
    def updatePlugData(self, plugData : dict = None) -> None:
        """
        """
        if plugData is not None:
            longName = plugData["longName"]
            type = plugData["type"] - 1
            exposed = plugData["isExposed"]
            hidden = plugData["isHidden"]
            exposedToGraph = plugData["isExposedToGraph"]
            data = plugData["defaultData"]
            self.setDisabled(False)
        else:
            longName = ""
            type = 0
            exposed = False
            hidden = False
            exposedToGraph = False
            data = None
            self.setDisabled(True)
        
        self.longNameWidget.getLineEdit().setText(longName)
        self.typeWidget.getComboBox().setCurrentIndex(type)
        self.exposedWidget.getCheckBox().setChecked(exposed)
        self.hiddenWidget.getCheckBox().setChecked(hidden)
        self.exposedToGraphWidget.getCheckBox().setChecked(exposedToGraph)
        self.valueWidget.setData(type + 1, data)
        
    def updateValueWidget(self) -> None:
        """
        """
        self.valueWidget.setData(self.typeWidget.getComboBox().currentIndex() + 1)
        
    def getPlugData(self) -> dict:
        """
        """
        plugData = {}
        
        plugData["longName"] = self.longNameWidget.getLineEdit().text()
        plugData["type"] = self.typeWidget.getComboBox().currentIndex() + 1
        plugData["isExposed"] = self.exposedWidget.getCheckBox().isChecked()
        plugData["isHidden"] = self.hiddenWidget.getCheckBox().isChecked()
        plugData["isExposedToGraph"] = self.exposedToGraphWidget.getCheckBox().isChecked()
        plugData["defaultData"] = self.valueWidget.getValue()
        
        return plugData
        
    def dataChanged(self) -> None:
        """
        """
        self.plugDataChanged.emit(self.getPlugData())
    
    @QtCore.pyqtSlot(object)
    def valueChanged(self, data : object = None) -> None:
        """
        """
        self.plugDataChanged.emit(self.getPlugData())

    def cleanup(self) -> None:
        """
        """
        self.blockSignals(True)

        longName = ""
        type = 0
        exposed = False
        hidden = False
        exposedToGraph = False
        
        self.longNameWidget.getLineEdit().setText(longName)
        self.typeWidget.getComboBox().setCurrentIndex(type)
        self.exposedWidget.getCheckBox().setChecked(exposed)
        self.hiddenWidget.getCheckBox().setChecked(hidden)
        self.exposedToGraphWidget.getCheckBox().setChecked(exposedToGraph)
        
        self.setDisabled(True)

        self.blockSignals(False)
    

class PlugsEditor(QtWidgets.QWidget):
    """
    Interface to edit the plugs of a node
    """
    def __init__(self, iconsLib : Icons, nodeToEditAsDict : dict, parent = None):
        """
        """
        super().__init__(parent=parent)
        
        self.iconsLib = iconsLib
        
        self.plugs = {}
        
        masterLayout = QtWidgets.QHBoxLayout()
        
        self.plugsView = QtWidgets.QListWidget()
        self.plugsView.setMaximumWidth(350)
        self.plugsView.setFrameStyle(QtWidgets.QFrame.NoFrame)
        self.plugsView.installEventFilter(self)
        self.plugsView.clicked.connect(self.updatePlug)
        masterLayout.addWidget(self.plugsView)
        
        self.propertiesEditor = PlugPropertiesEditor()
        self.propertiesEditor.plugDataChanged.connect(self.plugDataChanged)
        masterLayout.addWidget(self.propertiesEditor)
        
        self.populateListFromNode(nodeToEditAsDict)
        
        self.setLayout(masterLayout)
        
    def populateListFromNode(self, nodeToEditAsDict : dict) -> None:
        """
        """
        self.plugs.clear()
        self.plugsView.clear()
        
        for inPlugName, inPlug in nodeToEditAsDict["inputs"].items():
            input = inPlug[0]
            item = QtWidgets.QListWidgetItem(input["shortName"])
            item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)
            item.setIcon(self.iconsLib.GetIcon("input"))
            
            item.setData(256, input)
            
            self.plugs[inPlugName] = input
            
            self.plugsView.addItem(item)
        
        for outPlugName, outPlug in nodeToEditAsDict["outputs"].items():
            output = outPlug[0]
            item = QtWidgets.QListWidgetItem(output["shortName"])
            item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)
            item.setIcon(self.iconsLib.GetIcon("output"))
            
            item.setData(256, output)
            
            self.plugs[outPlugName] = output
            
            self.plugsView.addItem(item)
        
    def updatePlug(self, index) -> None:
        """
        """
        item = self.plugsView.item(index.row())
        data = item.data(256)
        self.propertiesEditor.updatePlugData(data)
        
    @QtCore.pyqtSlot(dict)
    def plugDataChanged(self, data : dict) -> None:
        """
        """
        self.plugsView.currentItem().setData(256, data)

    def setNodeToEdit(self, nodeToEdit : Node) -> None:
        """
        """
        self.populateListFromNode(nodeToEdit)
        
    def addNewInputPlug(self) -> None:
        """
        """
        newName = "innewinput"
        
        hasName = True
        
        while hasName: 
            newName = Increment(newName)
            
            hasName = False
            
            for plug in self.getItems():
                if newName == plug.text():
                    hasName = True
        
        newInput = {
                    "shortName" : newName,
                    "longName" : "New Input",
                    "isExposed" : False,
                    "isHidden" : False,
                    "isExposedToGraph" : False,
                    "defaultData" : "",
                    "type" : 7
                   }
        
        item = QtWidgets.QListWidgetItem(newInput["shortName"])
        item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)
        item.setIcon(self.iconsLib.GetIcon("input"))
        
        item.setData(256, newInput)
        
        self.plugsView.addItem(item)
    
    def addNewOutputPlug(self) -> None:
        """
        """
        newName = "outnewinput"
        
        hasName = True
        
        while hasName: 
            newName = Increment(newName)
            
            hasName = False
            
            for plug in self.getItems():
                if newName == plug.text():
                    hasName = True
        
        newOutput = {
                     "shortName" : newName,
                     "longName" : "New Output",
                     "isExposed" : False,
                     "isHidden" : False,
                     "isExposedToGraph" : False,
                     "defaultData" : "",
                     "type" : 7 
                    }
        
        item = QtWidgets.QListWidgetItem(newOutput["shortName"])
        item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)
        item.setIcon(self.iconsLib.GetIcon("output"))
        
        item.setData(256, newOutput)
        
        self.plugsView.addItem(item)

    def getItems(self):
        """
        """
        for i in range(self.plugsView.count()):
            yield self.plugsView.item(i)

    def getPlugs(self) -> dict:
        """
        """
        plugs = {}

        for item in self.getItems():
            plugName = item.text()
            plugData = item.data(256)
            
            if not "shortName" in plugData:
                plugData["shortName"] = plugName

            plugs[plugName] = plugData

        return plugs
        
    def eventFilter(self, source : QtCore.QObject, event : QtCore.QEvent) -> None:
        """
        """
        if event.type() == QtCore.QEvent.ContextMenu and source is self.plugsView:
            menu = QtWidgets.QMenu("Menu", self)
            
            menu.setStyleSheet(QMENUSTYLE)
            
            newInputAction = QtWidgets.QAction("Add Input", self)
            newInputAction.triggered.connect(self.addNewInputPlug)
            menu.addAction(newInputAction)
            
            newOutputAction = QtWidgets.QAction("Add Output", self)
            newOutputAction.triggered.connect(self.addNewOutputPlug)
            menu.addAction(newOutputAction)
            
            menu.exec_(event.globalPos())

        elif event.type() == QtCore.QEvent.KeyPress and event.key() == QtCore.Qt.Key_Delete:
            items = self.plugsView.selectedItems()

            for item in items:
                self.plugsView.takeItem(self.plugsView.row(item))
                del item

            self.propertiesEditor.cleanup()
            
        return super().eventFilter(source, event)

    def cleanup(self) -> None:
        """
        """
        self.plugsView.clear()
        self.propertiesEditor.cleanup()


CODEEDITORSYNTAXHIGHLIGHT = {
    "string" : Format(GetQColorFromPalette(ColorPalette.STRINGSCOLOR)),
    "keyword" : Format(GetQColorFromPalette(ColorPalette.KEYWORDSCOLOR)),
    "operator" : Format(GetQColorFromPalette(ColorPalette.OPERATORSCOLOR)),
    "brace" : Format(GetQColorFromPalette(ColorPalette.FOREGROUND)),
    "self" : Format(GetQColorFromPalette(ColorPalette.OPERATORSCOLOR)),
    "defclass" : Format(GetQColorFromPalette(ColorPalette.FUNCTIONSCOLOR)),
    "numbers" : Format(GetQColorFromPalette(ColorPalette.NUMBERSCOLOR)),
    "comment" : Format(GetQColorFromPalette(ColorPalette.COMMENTSCOLOR))
}


class OpEditor(QtWidgets.QWidget):
    """
    Interface that enable to type the python opcode of the node
    """
    def __init__(self, nodeToEditAsDict : dict, parent = None) -> None:
        """
        """
        super().__init__(parent=parent)
        
        self.masterLayout = QtWidgets.QVBoxLayout()
        
        self.codeEditor = PyCodeEditor(CODEEDITORSYNTAXHIGHLIGHT, QtGui.QFont("Source Code Pro", 10))
        self.codeEditor.setFrameStyle(QtWidgets.QFrame.NoFrame)
        self.codeEditor.setMinimumSize(800, 1000)
        self.codeEditor.setStyleSheet(CODEEDITORSTYLE)
        self.codeEditor.setLineHighlightColor(GetQColorFromPalette(ColorPalette.HIGHLIGHT))
        self.codeEditor.setLineIndicesTextColor(GetQColorFromPalette(ColorPalette.DISABLED))
        self.codeEditor.setLineIndicesBgColor(GetQColorFromPalette(ColorPalette.BACKGROUND))
        
        self.codeEditor.appendPlainText(nodeToEditAsDict["opCode"])
        
        self.masterLayout.addWidget(self.codeEditor)
        
        self.setLayout(self.masterLayout)
    
    def setNodeToEdit(self, nodeToEditAsDict : dict) -> None:
        """
        """
        self.nodeToEditAsDict = nodeToEditAsDict
        self.codeEditor.setPlainText(self.nodeToEditAsDict["opCode"])

    def cleanup(self) -> None:
        """
        """
        self.codeEditor.setPlainText("")
        
    def getCode(self) -> str:
        """
        """
        return self.codeEditor.toPlainText()

class NodeEditor(QtWidgets.QWidget):
    """
    Interface that enables the user to create and edit nodes
    """
    
    needToClose = QtCore.pyqtSignal()
    
    def __init__(self, iconsLib : Icons, environment : Environment, nodeToEdit : Node = None, parent = None):
        """
        """
        super().__init__(parent=parent)
        
        self.iconsLib = iconsLib
        self.environment = environment
        
        if nodeToEdit is not None:
            self.nodeToEditAsDict = nodeToEdit.ToDict()
        else:
            self.nodeToEditAsDict = { "name" : "NewNode",
                                      "iconPath" : "$FLASH_ICONS/flash.png",
                                      "category" : "NewCategory",
                                      "definitionPath" : "$FLASH_LIB/Nodes/new_node.fnode", 
                                      "id" : "0",
                                      "color" : [0, 0, 0], 
                                      "opCode" : "",
                                      "inputs" : {},
                                      "outputs" : {} }
        
        masterLayout = QtWidgets.QVBoxLayout()
        
        self.attributeEditor = AttributeEditor(self.nodeToEditAsDict)
        masterLayout.addWidget(self.attributeEditor)
        
        self.editTabs = QtWidgets.QTabWidget()
        
        self.plugsEditor = PlugsEditor(self.iconsLib, self.nodeToEditAsDict)
        self.editTabs.addTab(self.plugsEditor, self.iconsLib.GetIcon("plug"), "Plugs")
        self.editTabs.setIconSize(QtCore.QSize(14, 14))
        
        self.opEditor = OpEditor(self.nodeToEditAsDict)
        self.editTabs.addTab(self.opEditor, self.iconsLib.GetIcon("code"), "Op")
        self.editTabs.setIconSize(QtCore.QSize(14, 14))
        
        masterLayout.addWidget(self.editTabs)
        
        buttonsLayout = QtWidgets.QHBoxLayout()
        buttonsLayout.setAlignment(QtCore.Qt.AlignRight)
        
        self.saveButton = QtWidgets.QPushButton("Save")
        self.saveButton.setMaximumHeight(25)
        self.saveButton.clicked.connect(self.saveNode)
        buttonsLayout.addWidget(self.saveButton)
        
        self.closeButton = QtWidgets.QPushButton("Close")
        self.closeButton.setMaximumHeight(25)
        self.closeButton.clicked.connect(self.closeWindow)
        buttonsLayout.addWidget(self.closeButton)
        
        masterLayout.addLayout(buttonsLayout)
        
        self.setLayout(masterLayout)
        
    def setNodeToEdit(self, nodeToEdit : Node = None) -> None:
        """
        """
        if nodeToEdit is not None:
            self.nodeToEditAsDict = nodeToEdit.ToDict()
        else:
            self.nodeToEditAsDict = { "name" : "NewNode",
                                      "iconPath" : "$FLASH_ICONS/flash.png",
                                      "category" : "NewCategory",
                                      "definitionPath" : "$FLASH_LIB/Nodes/new_node.fnode", 
                                      "nodeType" : "NewCategory/NewNode",
                                      "id" : "0",
                                      "color" : [0, 0, 0], 
                                      "opCode" : "",
                                      "inputs" : {},
                                      "outputs" : {} }
        
        self.attributeEditor.setNodeToEdit(self.nodeToEditAsDict)
        self.plugsEditor.setNodeToEdit(self.nodeToEditAsDict)
        self.opEditor.setNodeToEdit(self.nodeToEditAsDict)
        
    def saveNode(self) -> None:
        """
        """
        tmpEnv = self.environment

        self.nodeToEditAsDict["name"] = self.attributeEditor.getName()
        self.nodeToEditAsDict["category"] = self.attributeEditor.getCategory()
        self.nodeToEditAsDict["iconPath"] = self.attributeEditor.getIcon()
        self.nodeToEditAsDict["definitionPath"] = self.attributeEditor.getSavePath()
        
        self.nodeToEditAsDict["nodeType"] = f"{self.nodeToEditAsDict['category']}/{self.nodeToEditAsDict['name']}"
        
        self.nodeToEditAsDict["opCode"] = self.opEditor.getCode()
        
        self.nodeToEditAsDict["inputs"] = {}
        self.nodeToEditAsDict["outputs"] = {}
        
        plugs = self.plugsEditor.getPlugs()

        i = 0
        for plugName, plugData in plugs.items():
            if plugName.startswith("in"):
                self.nodeToEditAsDict["inputs"][plugName] = [{ "shortName" : plugData["shortName"],
                                                               "longName" : plugData["longName"],
                                                               "index" : i,
                                                               "isExposed" : plugData["isExposed"],
                                                               "isHidden" : plugData["isHidden"],
                                                               "isExposedToGraph" : plugData["isExposedToGraph"],
                                                               "data" : plugData["defaultData"],
                                                               "defaultData" : plugData["defaultData"],
                                                               "type" : plugData["type"],
                                                               "connectionName" : None,
                                                               "connectionNodeId" : None }]
                
                i += 1
              
        i = 0  
        for plugName, plugData in plugs.items():
            if plugName.startswith("out"):
                self.nodeToEditAsDict["outputs"][plugName] = [{ "shortName" : plugData["shortName"],
                                                               "longName" : plugData["longName"],
                                                               "index" : i,
                                                               "isExposed" : plugData["isExposed"],
                                                               "isHidden" : plugData["isHidden"],
                                                               "isExposedToGraph" : plugData["isExposedToGraph"],
                                                               "data" : plugData["defaultData"],
                                                               "defaultData" : plugData["defaultData"],
                                                               "type" : plugData["type"],
                                                               "connectionName" : None,
                                                               "connectionNodeId" : None }]
                
                i += 1

        tmpNode = Node(tmpEnv)
        tmpNode.FromDict(self.nodeToEditAsDict)
        
        savePath = self.nodeToEditAsDict["definitionPath"]
        
        if self.environment.SearchInString(savePath):
            savePath = self.environment.ReplaceInString(savePath)
        
        with open(savePath, "w") as file:
            file.write(tmpNode.ToFile())
    
    def closeWindow(self) -> None:
        """
        """
        self.needToClose.emit()

        self.attributeEditor.cleanup()
        self.plugsEditor.cleanup()
        self.opEditor.cleanup()
        

class NodeEditorWindow(QtWidgets.QMainWindow):
    """
    """
    def __init__(self, iconsLib : Icons, environment : Environment, nodeToEdit : Node = None, parent=None) -> None:
        """
        """
        super().__init__(parent=parent)
        
        self.environment = environment
        
        self.editor = NodeEditor(iconsLib, self.environment, nodeToEdit)
        self.editor.needToClose.connect(lambda: self.close())
        
        self.setMinimumSize(900, 800)
        
        name = "Node Properties"
        
        if nodeToEdit is not None:
            name = f"Node Properties : {nodeToEdit.GetName()}"
        
        self.setWindowTitle(name)
        
        self.setCentralWidget(self.editor)
        
    def setNodeToEdit(self, nodeToEdit : Node = None) -> None:
        """
        """
        self.editor.setNodeToEdit(nodeToEdit)
        
        name = "Node Properties"
        
        if nodeToEdit is not None:
            name = f"Node Properties : {nodeToEdit.GetName()}"
        
        self.setWindowTitle(name)