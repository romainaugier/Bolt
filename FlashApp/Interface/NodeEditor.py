from PyQt5 import QtCore, QtWidgets

from FlashApi.Core.Node import *
from FlashApp.Interface.Icons import *
from FlashApp.Interface.Widgets import *
from FlashApp.Interface.Utils import *
from FlashApp.Interface.Style import *
from FlashApp.Interface.PlugEditor import *


class AttributeEditor(QtWidgets.QWidget):
    """
    Interface to edit the main attributes of a node
    """
    def __init__(self, nodeToEdit : Node = None, parent = None):
        """
        """
        super().__init__(parent=parent)
        
        masterLayout = QtWidgets.QVBoxLayout()
        
        self.savePathWidget = LabeledLineEdit("Save Path", "")
        masterLayout.addWidget(self.savePathWidget)
        
        self.nameWidget = LabeledLineEdit("Name", "")
        masterLayout.addWidget(self.nameWidget)
        
        self.iconWidget = LabeledLineEdit("Icon", "")
        masterLayout.addWidget(self.iconWidget)
        
        self.categoryWidget = LabeledLineEdit("Category", "")
        masterLayout.addWidget(self.categoryWidget)
        
        self.setNodeToEdit(nodeToEdit)
        
        self.setLayout(masterLayout)
        
    def setNodeToEdit(self, nodeToEdit : Node = None) -> None:
        """
        """
        if nodeToEdit is not None:
            name = nodeToEdit.GetName()
            icon = nodeToEdit.GetIconPathRaw()
            category = nodeToEdit.GetCategory()
            savePath = nodeToEdit.GetDefinitionPath()
        else:
            name = "NewNode"
            icon = "$FLASH_ICONS/flash.png"
            category = "NewCategory"   
            savePath = "$FLASH_LIB/Nodes/new_node.fnode"
            
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
        
        self.shortNameWidget = LabeledLineEdit("Short Name", "")
        self.shortNameWidget.getLineEdit().editingFinished.connect(self.dataChanged)
        masterLayout.addWidget(self.shortNameWidget)
        
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
            shortName = plugData["shortName"]
            longName = plugData["longName"]
            type = plugData["type"] - 1
            exposed = plugData["exposed"]
            hidden = plugData["hidden"]
            exposedToGraph = plugData["exposedToGraph"]
        else:
            shortName = ""
            longName = ""
            type = 0
            exposed = False
            hidden = False
            exposedToGraph = False
        
        self.shortNameWidget.getLineEdit().setText(shortName)
        self.longNameWidget.getLineEdit().setText(longName)
        self.typeWidget.getComboBox().setCurrentIndex(type)
        self.exposedWidget.getCheckBox().setChecked(exposed)
        self.exposedWidget.getCheckBox().setChecked(hidden)
        self.exposedWidget.getCheckBox().setChecked(exposedToGraph)
        # plugData["defaultValue"] TODO
        
    def getPlugData(self) -> dict:
        """
        """
        plugData = {}
        
        plugData["shortName"] = self.shortNameWidget.getLineEdit().text()
        plugData["longName"] = self.longNameWidget.getLineEdit().text()
        plugData["type"] = self.typeWidget.getComboBox().currentIndex() + 1
        plugData["exposed"] = self.exposedWidget.getCheckBox().isChecked()
        plugData["hidden"] = self.exposedWidget.getCheckBox().isChecked()
        plugData["exposedToGraph"] = self.exposedWidget.getCheckBox().isChecked()
        
    def dataChanged(self) -> None:
        """
        """
        self.plugDataChanged.emit(self.getPlugData())
    
class PlugsEditor(QtWidgets.QWidget):
    """
    Interface to edit the plugs of a node
    """
    def __init__(self, nodeToEdit : Node = None, parent = None):
        """
        """
        super().__init__(parent=parent)
        
        masterLayout = QtWidgets.QHBoxLayout()
        
        self.plugsView = QtWidgets.QListView()
        self.plugsView.clicked.connect(self.updatePlug)
        masterLayout.addWidget(self.plugsView)
        
        self.model = QtGui.QStandardItemModel(self.plugsView)
        
        self.propertiesEditor = PlugPropertiesEditor()
        masterLayout.addWidget(self.propertiesEditor)
        
        self.setLayout(masterLayout)
        
    def populateList(self, nodeToEdit : Node = None) -> None:
        """
        """
        self.model.clear()
        
        for inPlugName, inPlug in nodeToEdit.GetInputs().items():
            item = QtGui.QStandardItem(inPlug.GetShortName())
            
            plugDataPacked = {
                "shortName" : inPlug.GetShortName(),
                "longName" : inPlug.GetLongName(),
                "defaultValue" : inPlug.GetDefaultValue(),
                "type" : inPlug.GetType(),
                "exposed" : inPlug.IsExposed(),
                "hidden" : inPlug.IsHidden(),
                "exposedToGraph" : inPlug.IsExposedToGraph(),
            }
            
            item.setData(plugDataPacked, 256)
            
            self.model.appendRow(item)
        
        for outPlugName, outPlug in nodeToEdit.GetOutputs().items():
            item = QtGui.QStandardItem(outPlug.GetShortName())
            
            plugDataPacked = {
                "shortName" : outPlug.GetShortName(),
                "longName" : outPlug.GetLongName(),
                "defaultValue" : outPlug.GetDefaultValue(),
                "type" : outPlug.GetType(),
                "exposed" : outPlug.IsExposed(),
                "hidden" : outPlug.IsHidden(),
                "exposedToGraph" : outPlug.IsExposedToGraph(),
            }
            
            item.setData(plugDataPacked, 256)
            
            self.model.appendRow(item)
            
        self.plugsView.setModel(self.model)
        
    def updatePlug(self, index) -> None:
        """
        """
        item = self.model().item(index.row(), index.column())
        data = item.data(256)
        self.propertiesEditor.updatePlugData(data)


class OpEditor(QtWidgets.QWidget):
    """
    Interface that enable to type the python opcode of the node
    """
    def __init__(self, nodeToEdit : Node = None, parent = None) -> None:
        """
        """
        super().__init__(parent=parent)
    

class NodeEditor(QtWidgets.QWidget):
    """
    Interface that enables the user to create and edit nodes
    """
    def __init__(self, iconsLib : Icons, nodeToEdit : Node = None, parent = None):
        """
        """
        super().__init__(parent=parent)
        
        self.iconsLib = iconsLib
        
        masterLayout = QtWidgets.QVBoxLayout()
        
        self.attributeEditor = AttributeEditor(nodeToEdit)
        masterLayout.addWidget(self.attributeEditor)
        
        self.tabs = QtWidgets.QTabWidget()
        
        self.plugPropertiesEditor = PlugPropertiesEditor()
        self.tabs.addTab(self.plugPropertiesEditor, self.iconsLib.GetIcon("plugs"), "Plugs")
        self.tabs.setIconSize(QtCore.QSize(14, 14))
        
        self.opEditor = OpEditor()
        self.tabs.addTab(self.opEditor, self.iconsLib.GetIcon("python"), "Op")
        self.tabs.setIconSize(QtCore.QSize(14, 14))
        
        masterLayout.addWidget(self.tabs)
        
        self.setLayout(masterLayout)
        

class NodeEditorWindow(QtGui.QMainWindow):
    """
    """
    def __init__(self, iconsLib : Icons, nodeToEdit : Node = None, parent=None) -> None:
        """
        """
        super().__init__(parent=parent)
        
        self.editor = NodeEditor(iconsLib, nodeToEdit)
        
        self.setCentralWidget(self.editor)