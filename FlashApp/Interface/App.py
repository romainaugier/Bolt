import os

from PyQt5 import QtCore, QtGui, QtWidgets

from FlashApp.Interface.Panel import *
from FlashApp.Interface.NodeEditor import *
from FlashApi.Core.Logger import *
from FlashApi.Core.Environment import *
from FlashApp.Interface.Utils import *
from FlashApp.Interface.Widgets import *


class App(QtWidgets.QMainWindow):
    """
    """
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.logger = Logger(level=LogLevel.MESSAGE)

        self.environment = Environment()

        self.nodeLib = Lib(self.logger, self.environment)
        
        self.icons = Icons()
        
        self.nodeEditor = NodeEditorWindow(self.icons, self.environment, parent=self)

        self.setWindowTitle("Flash")
  
        self.setWindowIcon(self.icons.GetIcon("flash"))
        
        # Central layout and widget
        
        self.centralLayout = QtWidgets.QVBoxLayout()
        self.centralLayout.setSpacing(0)
        self.centralLayout.setContentsMargins(0, 0, 0, 0)
        self._centralWidget = QtWidgets.QWidget()

        # Shelf

        shelfLayout = QtWidgets.QHBoxLayout()
        shelfLayout.setAlignment(Qt.AlignLeft)
        # shelfLayout.setSpacing(0)
        shelfLayout.setContentsMargins(5, 5, 5, 5)
        
        shelfWidget = QtWidgets.QWidget()
        shelfWidget.setFixedHeight(60)

        # Graph Buttons

        self.newGraphButton = QtWidgets.QPushButton("")
        self.newGraphButton.setIcon(self.icons.GetIcon("new-graph"))
        self.newGraphButton.setToolTip("Create New Graph")
        self.newGraphButton.clicked.connect(lambda: self.ctrlNShortcut())
        shelfLayout.addWidget(self.newGraphButton)

        self.cookGraphButton = QtWidgets.QPushButton("")
        self.cookGraphButton.setIcon(self.icons.GetIcon("cook-graph"))
        self.cookGraphButton.setToolTip("Cook Active Graph")
        self.cookGraphButton.clicked.connect(lambda: self.cShortcut())
        shelfLayout.addWidget(self.cookGraphButton)

        self.saveGraphButton = QtWidgets.QPushButton("")
        self.saveGraphButton.setIcon(self.icons.GetIcon("save-graph"))
        self.saveGraphButton.setToolTip("Save Active Graph")
        self.saveGraphButton.clicked.connect(lambda: self.saveGraph())
        shelfLayout.addWidget(self.saveGraphButton)

        self.loadGraphButton = QtWidgets.QPushButton("")
        self.loadGraphButton.setIcon(self.icons.GetIcon("load-graph"))
        self.loadGraphButton.setToolTip("Load Graph from a file")
        self.loadGraphButton.clicked.connect(lambda: self.ctrlLShortcut())
        shelfLayout.addWidget(self.loadGraphButton)

        self.layoutGraphButton = QtWidgets.QPushButton("")
        self.layoutGraphButton.setIcon(self.icons.GetIcon("layout-graph"))
        self.layoutGraphButton.setToolTip("Layout Active Graph")
        self.layoutGraphButton.clicked.connect(lambda: self.lShortcut())
        shelfLayout.addWidget(self.layoutGraphButton)

        separator = QVLine()
        separator.setColor(QtGui.QColor(255, 255, 255, 20))
        shelfLayout.addWidget(separator)

        # Node Buttons

        self.createNewNodeButton = QtWidgets.QPushButton("")
        self.createNewNodeButton.setIcon(self.icons.GetIcon("new-node"))
        self.createNewNodeButton.setToolTip("Create a new node type\nOpens the node properties editor")
        self.createNewNodeButton.clicked.connect(self.openNodeEditor)
        shelfLayout.addWidget(self.createNewNodeButton)

        self.modifySelectedNodeButton = QtWidgets.QPushButton("")
        self.modifySelectedNodeButton.setIcon(self.icons.GetIcon("edit-node"))
        self.modifySelectedNodeButton.setToolTip("Modify the selected node\nOpens the node properties editor")
        shelfLayout.addWidget(self.modifySelectedNodeButton)

        shelfWidget.setLayout(shelfLayout)
        
        self.centralLayout.addWidget(shelfWidget)

        # Separator
        
        sep = QHLine()
        sep.setFixedHeight(2)
        sep.setColor(GetQColorFromPalette(ColorPalette.TEXT))
        self.centralLayout.addWidget(sep)

        # Principal panel

        self.principalPanel = Panel(0, self.icons, self.logger, self.environment)
        self.centralLayout.addWidget(self.principalPanel) 

        # Central Widget

        self._centralWidget.setLayout(self.centralLayout)
        self.setCentralWidget(self._centralWidget)

        # Shortcuts
        
        self.newGraphSc = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+N"), self)
        self.newGraphSc.activated.connect(lambda: self.ctrlNShortcut())

        self.closeGraphSc = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+W"), self)
        self.closeGraphSc.activated.connect(lambda: self.ctrlWShortcut())

        self.cookGraphSc = QtWidgets.QShortcut(QtGui.QKeySequence("C"), self)
        self.cookGraphSc.activated.connect(lambda: self.cShortcut())

        self.saveGraphSc = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+S"), self)
        self.saveGraphSc.activated.connect(lambda: self.ctrlSShortcut())
        
        self.forceSaveGraphSc = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+Shift+S"), self)
        self.forceSaveGraphSc.activated.connect(lambda: self.ctrlShiftSShortcut(forceName=True))

        self.loadGraphSc = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+L"), self)
        self.loadGraphSc.activated.connect(lambda: self.ctrlLShortcut())
        
        self.layoutGraphSc = QtWidgets.QShortcut(QtGui.QKeySequence("L"), self)
        self.layoutGraphSc.activated.connect(lambda: self.lShortcut())
        
        self.showPlugEditorSc = QtWidgets.QShortcut(QtGui.QKeySequence("P"), self)
        self.showPlugEditorSc.activated.connect(lambda: self.pShortcut())
        
        self.stopGraphCookingSc = QtWidgets.QShortcut(QtGui.QKeySequence("Escape"), self)
        self.stopGraphCookingSc.activated.connect(lambda: self.escapeShortcut())

    def ctrlNShortcut(self) -> None:
        """
        """
        focusedWidget = QtWidgets.QApplication.focusWidget()
        
        if isinstance(focusedWidget, GraphsEditor):
            focusedWidget.addTab()

    def ctrlWShortcut(self) -> None:
        """
        Close the tab at the index given as argument. If the index
        is left to None, close the active tab

        Args:
            index (int, optional): Index of the tab to close. 
            Defaults to None.
        """
        focusedWidget = QtWidgets.QApplication.focusWidget()
        
        if isinstance(focusedWidget, GraphsEditor):
            focusedWidget.removeActiveTab()

    def cShortcut(self) -> None:
        """
        Called when C is pressed. Depending on the focused widget, it might do different things.
        
        If the focused widget is :
            - Graphs Editor -> Cooks the active graph
        """
        focusedWidget = QtWidgets.QApplication.focusWidget()
        
        if isinstance(focusedWidget, GraphsEditor):
            focusedWidget.cookActiveGraph()

    def ctrlSShortcut(self) -> None:
        """
        Called when Ctrl+S is pressed. Depending on the focused widget, it might do different things.
        
        If the focused widget is :
            - Graphs Editor -> Saves the active graph
        """
        focusedWidget = QtWidgets.QApplication.focusWidget()
        
        if isinstance(focusedWidget, GraphsEditor):
            focusedWidget.saveActiveGraph()
    
    def ctrlShiftSShortcut(self) -> None:
        """
        Called when Ctrl+Shift+S is pressed. Depending on the focused widget, it might do different things.
        
        If the focused widget is :
            - Graphs Editor -> Saves the active graph with name override
        """
        focusedWidget = QtWidgets.QApplication.focusWidget()
        
        if isinstance(focusedWidget, GraphsEditor):
            focusedWidget.saveActiveGraph(forceName=True)

    def ctrlLShortcut(self) -> None:
        """
        Called when Ctrl+L is pressed. Depending on the focused widget, it might do different things.
        
        If the focused widget is :
            - Graphs Editor -> Loads a graph from a file
        """
        focusedWidget = QtWidgets.QApplication.focusWidget()
        
        if isinstance(focusedWidget, GraphsEditor):
            focusedWidget.loadNewGraph()

    def lShortcut(self) -> None:
        """
        Called when L is pressed. Depending on the focused widget, it might do different things.
        
        If the focused widget is :
            - Graphs Editor -> Layout the active graph
        """
        focusedWidget = QtWidgets.QApplication.focusWidget()
        
        if isinstance(focusedWidget, GraphsEditor):
            focusedWidget.layoutActiveGraph()
        
    def escapeShortcut(self) -> None:
        """
        Called when Esc is pressed. Depending on the focused widget, it might do different things.
        
        If the focused widget is :
            - Graphs Editor -> Stops the current graph cooking op
        """
        focusedWidget = QtWidgets.QApplication.focusWidget()
        
        if isinstance(focusedWidget, GraphsEditor):
            focusedWidget.stopActiveGraph()
        
    def pShortcut(self) -> None:
        """
        Called when P is pressed. Depending on the focused widget, it might do different things.
        
        If the focused widget is :
            - Graphs Editor -> Show the active graph plug editor
        """
        focusedWidget = QtWidgets.QApplication.focusWidget()
        
        if isinstance(focusedWidget, GraphsEditor):
            focusedWidget.showActiveGraphPlugEditor()
        
    def openNodeEditor(self) -> None:
        """
        Show the node properties editor
        """
        focusedWidget = QtWidgets.QApplication.focusWidget()
        
        if isinstance(focusedWidget, GraphsEditor):
            index = focusedWidget.getActiveTabIndex()
            
            gGraph : GGraph = focusedWidget.tabs.widget(index).layout.itemAt(0).widget()
            
            currentGraphSelection = gGraph.scene.selectedItems() 
            
            node = None
            
            if len(currentGraphSelection) > 0:
                if type(currentGraphSelection[0]) is GNode:
                    node = currentGraphSelection[0].getInternalNode()
            
            self.nodeEditor.setNodeToEdit(node)
            
            self.nodeEditor.show()
        