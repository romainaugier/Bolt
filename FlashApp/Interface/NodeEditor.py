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
        self.typeWidget.getComboBox().currentIndexChanged.connect(self.dataChanged)
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
            self.show()
        else:
            longName = ""
            type = 0
            exposed = False
            hidden = False
            exposedToGraph = False
            self.hide()
        
        self.longNameWidget.getLineEdit().setText(longName)
        self.typeWidget.getComboBox().setCurrentIndex(type)
        self.exposedWidget.getCheckBox().setChecked(exposed)
        self.exposedWidget.getCheckBox().setChecked(hidden)
        self.exposedWidget.getCheckBox().setChecked(exposedToGraph)
        
    def getPlugData(self) -> dict:
        """
        """
        plugData = {}
        
        plugData["longName"] = self.longNameWidget.getLineEdit().text()
        plugData["type"] = self.typeWidget.getComboBox().currentIndex() + 1
        plugData["isExposed"] = self.exposedWidget.getCheckBox().isChecked()
        plugData["isHidden"] = self.exposedWidget.getCheckBox().isChecked()
        plugData["isExposedToGraph"] = self.exposedWidget.getCheckBox().isChecked()
        
        return plugData
        
    def dataChanged(self) -> None:
        """
        """
        self.plugDataChanged.emit(self.getPlugData())
    

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
        self.plugsView.itemChanged.connect(self.plugNameChanged)
        self.plugsView.clicked.connect(self.updatePlug)
        masterLayout.addWidget(self.plugsView)
        
        self.propertiesEditor = PlugPropertiesEditor()
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
            item.setIcon(self.iconsLib.GetIcon("input"))
            
            item.setData(256, input)
            
            self.plugs[inPlugName] = input
            
            self.plugsView.addItem(item)
        
        for outPlugName, outPlug in nodeToEditAsDict["outputs"].items():
            output = outPlug[0]
            item = QtWidgets.QListWidgetItem(output["shortName"])
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
        
    def plugNameChanged(self) -> None:
        """
        """
        print(self.plugsView.currentItem())

    def setNodeToEdit(self, nodeToEdit : Node) -> None:
        """
        """
        self.populateListFromNode(nodeToEdit)
        
    def addNewInputPlug(self) -> None:
        """
        """
        newName = "innewinput"
        
        while newName in self.plugs: 
            newName = Increment(newName)
        
        newInput = {
        "shortName" : newName,
        "longName" : "New Input",
        "index" : 0,
        "isExposed" : False,
        "isHidden" : False,
        "isExposedToGraph" : False,
        "defaultData" : "",
        "type" : 7 }
        
        item = QtWidgets.QListWidgetItem(newInput["shortName"])
        item.setIcon(self.iconsLib.GetIcon("input"))
        
        item.setData(256, newInput)
        
        self.plugsView.addItem(item)
    
    def addNewOutputPlug(self) -> None:
        """
        """
        newName = "outnewinput"
        
        while newName in self.plugs: 
            newName = Increment(newName)
        
        newOutput = {
        "shortName" : newName,
        "longName" : "New Output",
        "index" : 0,
        "isExposed" : False,
        "isHidden" : False,
        "isExposedToGraph" : False,
        "defaultData" : "",
        "type" : 7 }
        
        item = QtWidgets.QListWidgetItem(newOutput["shortName"])
        item.setIcon(self.iconsLib.GetIcon("output"))
        
        item.setData(256, newOutput)
        
        self.plugsView.addItem(item)
        
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
            
        return super().eventFilter(source, event)


class OpEditor(QtWidgets.QWidget):
    """
    Interface that enable to type the python opcode of the node
    """
    def __init__(self, nodeToEditAsDict : dict, parent = None) -> None:
        """
        """
        super().__init__(parent=parent)
        pass
    
    def setNodeToEdit(self, nodeToEditAsDict : dict) -> None:
        """
        """
        pass

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
        self.editTabs.addTab(self.opEditor, self.iconsLib.GetIcon("python"), "Op")
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
        tmpEnv = Environment()
        
        tmpNode = Node(tmpEnv)
        tmpNode.FromDict(self.nodeToEditAsDict)
        
        print(tmpNode.ToFile())
        
        self.needToClose.emit()
    
    def closeWindow(self) -> None:
        """
        """
        self.needToClose.emit()
        

class NodeEditorWindow(QtWidgets.QMainWindow):
    """
    """
    def __init__(self, iconsLib : Icons, nodeToEdit : Node = None, parent=None) -> None:
        """
        """
        super().__init__(parent=parent)
        
        self.editor = NodeEditor(iconsLib, nodeToEdit)
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