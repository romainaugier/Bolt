import os

from PyQt5 import QtCore, QtGui, QtWidgets

from FlashApp.Interface.Icons import *
from FlashApp.Interface.GGraph import *
from FlashApi.Core.Logger import *
from FlashApi.Core.Environment import *
from FlashApp.Interface.Utils import *
from FlashApp.Interface.Widgets import *


class GraphTabs(QtWidgets.QWidget):
    """
    """

    selectedNodeChanged = QtCore.pyqtSignal(str)

    def __init__(self, nodeLib : Lib, icons : Icons, logger : Logger, parent):
        super(QtWidgets.QWidget, self).__init__(parent)

        self.nodeLib = nodeLib
        self.iconsLib = icons
        self.logger = logger

        self.layout = QtWidgets.QVBoxLayout(self)

        self.tabs = QtWidgets.QTabWidget()

        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)

    def addTab(self, graph : GGraph = None, env : Environment = None) -> None:
        """
        Adds a new tab with a graph if provided

        Args:
            graph (GGraph, optional): Graph to load. Defaults to None.
        """
        tabIndex = self.tabs.count()

        self.newTab = QtWidgets.QWidget()

        if graph is not None:
            gGraph = graph
        else:
            gGraph = GGraph(self.nodeLib, self.logger, env)

        self.tabs.addTab(self.newTab, self.iconsLib.GetIcon("graph-edited"), f"{gGraph.graph.GetName()}")
        self.tabs.setIconSize(QtCore.QSize(18, 18))

        self.newTab.layout = QtWidgets.QVBoxLayout()
        gGraph.setFrameStyle(QtWidgets.QFrame.NoFrame)
        gGraph.isCookingMovie.frameChanged.connect(lambda: self.tabs.setTabIcon(tabIndex, QtGui.QIcon(gGraph.getAnimationLogoMovie().currentPixmap())))
        gGraph.hasBeenEdited.connect(lambda: (self.tabs.setTabIcon(tabIndex, self.iconsLib.GetIcon("graph-edited")), 
                                              self.tabs.setTabText(tabIndex, f"{gGraph.graph.GetName()}*")))
        gGraph.finishedCooking.connect(lambda: self.tabs.setTabIcon(tabIndex, self.iconsLib.GetIcon("graph-done")))
        gGraph.errorCooking.connect(lambda: self.tabs.setTabIcon(tabIndex, self.iconsLib.GetIcon("graph-error")))
        gGraph.selectedNodeChanged.connect(self.onNodeSelectionChange)

        self.newTab.layout.addWidget(gGraph)
        self.newTab.setLayout(self.newTab.layout)

        self.tabs.setCurrentIndex(tabIndex)

    @QtCore.pyqtSlot(str)
    def onNodeSelectionChange(self, nodeId : str) -> None:
        self.selectedNodeChanged.emit(nodeId)

    def removeTab(self, index : int) -> None:
        """
        Removes a tab

        Args:
            index (int): tab index to remove
        """
        self.tabs.removeTab(index)

    def getActiveTabIndex(self) -> int:
        """
        Returns the index of the active tab

        Returns:
            int: index of the active tab
        """
        return self.tabs.currentIndex()

    def setTabName(self, index : int, name : str) -> None:
        """
        Sets the name of the tab at the given index

        Args:
            index (int): index of the tab
            name (str): new name of the tab
        """
        self.tabs.setTabText(index, name)

class App(QtWidgets.QMainWindow):
    """
    """
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.logger = Logger(level=LogLevel.DIAGNOSTIC)

        self.environment = Environment()

        self.nodeLib = Lib(self.logger, self.environment)

        self.icons = Icons()

        self.setWindowTitle("Flash")
  
        self.setWindowIcon(self.icons.GetIcon("flash"))

        masterLayout = QtWidgets.QVBoxLayout()
        masterWidget = QtWidgets.QWidget()

        # Shelf

        shelfLayout = QtWidgets.QHBoxLayout()
        shelfLayout.setAlignment(Qt.AlignLeft)

        # Graph Buttons

        self.newGraphButton = QtWidgets.QPushButton("")
        self.newGraphButton.setIcon(self.icons.GetIcon("new-graph"))
        self.newGraphButton.setToolTip("Create New Graph")
        self.newGraphButton.clicked.connect(lambda: self.addGraph())
        shelfLayout.addWidget(self.newGraphButton)

        self.cookGraphButton = QtWidgets.QPushButton("")
        self.cookGraphButton.setIcon(self.icons.GetIcon("cook-graph"))
        self.cookGraphButton.setToolTip("Cook Active Graph")
        self.cookGraphButton.clicked.connect(lambda: self.cookGraph())
        shelfLayout.addWidget(self.cookGraphButton)

        self.saveGraphButton = QtWidgets.QPushButton("")
        self.saveGraphButton.setIcon(self.icons.GetIcon("save-graph"))
        self.saveGraphButton.setToolTip("Save Active Graph")
        self.saveGraphButton.clicked.connect(lambda: self.saveGraph())
        shelfLayout.addWidget(self.saveGraphButton)

        self.loadGraphButton = QtWidgets.QPushButton("")
        self.loadGraphButton.setIcon(self.icons.GetIcon("load-graph"))
        self.loadGraphButton.setToolTip("Load Graph from a file")
        self.loadGraphButton.clicked.connect(lambda: self.loadGraph())
        shelfLayout.addWidget(self.loadGraphButton)

        self.layoutGraphButton = QtWidgets.QPushButton("")
        self.layoutGraphButton.setIcon(self.icons.GetIcon("layout-graph"))
        self.layoutGraphButton.setToolTip("Layout Active Graph")
        self.layoutGraphButton.clicked.connect(lambda: self.layoutGraph())
        shelfLayout.addWidget(self.layoutGraphButton)

        separator = QVLine()
        separator.setColor(QtGui.QColor(255, 255, 255, 20))
        shelfLayout.addWidget(separator)

        # Node Buttons

        self.createNewNodeButton = QtWidgets.QPushButton("")
        self.createNewNodeButton.setIcon(self.icons.GetIcon("new-node"))
        self.createNewNodeButton.setToolTip("Create a new node type\nOpens the node properties editor")
        shelfLayout.addWidget(self.createNewNodeButton)

        self.modifySelectedNodeButton = QtWidgets.QPushButton("")
        self.modifySelectedNodeButton.setIcon(self.icons.GetIcon("modify-node"))
        self.modifySelectedNodeButton.setToolTip("Modify the selected node\nOpens the node properties editor")
        shelfLayout.addWidget(self.modifySelectedNodeButton)

        masterLayout.addLayout(shelfLayout)

        # Graphs

        graphLayout = QtWidgets.QHBoxLayout()

        self.graphTabs = GraphTabs(self.nodeLib, self.icons, self.logger, self)

        graphLayout.addWidget(self.graphTabs)

        masterLayout.addLayout(graphLayout)

        masterWidget.setLayout(masterLayout)

        self.setCentralWidget(masterWidget)
        
        # Shortcuts
        self.newGraphSc = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+N"), self)
        self.newGraphSc.activated.connect(lambda: self.addGraph())

        self.closeGraphSc = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+W"), self)
        self.closeGraphSc.activated.connect(lambda: self.closeGraph())

        self.cookGraphSc = QtWidgets.QShortcut(QtGui.QKeySequence("C"), self)
        self.cookGraphSc.activated.connect(lambda: self.cookGraph())

        self.saveGraphSc = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+S"), self)
        self.saveGraphSc.activated.connect(lambda: self.saveGraph())
        
        self.forceSaveGraphSc = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+Shift+S"), self)
        self.forceSaveGraphSc.activated.connect(lambda: self.saveGraph(forceName=True))

        self.loadGraphSc = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+L"), self)
        self.loadGraphSc.activated.connect(lambda: self.loadGraph())
        
        self.layoutGraphSc = QtWidgets.QShortcut(QtGui.QKeySequence("L"), self)
        self.layoutGraphSc.activated.connect(lambda: self.layoutGraph())

        # Init at least one graph
        self.addGraph()

    def addGraph(self) -> None:
        """
        """
        self.graphTabs.addTab(env=self.environment)

    def closeGraph(self, index : int = None) -> None:
        """
        Close the tab at the index given as argument. If the index
        is left to None, close the active tab

        Args:
            index (int, optional): Index of the tab to close. 
            Defaults to None.
        """
        if index is not None:
            self.graphTabs.removeTab(index)
        else:
            self.graphTabs.removeTab(self.graphTabs.getActiveTabIndex())

    def cookGraph(self, index : int = None) -> None:
        """
        Cook the graph at the given index

        Args:
            index (int, optional): Index of the graph to cook. Defaults to None.
        """
        if index is None:
            index = self.graphTabs.getActiveTabIndex()

        self.graphTabs.tabs.widget(index).layout.itemAt(0).widget().launchGraphCooking()

    def saveGraph(self, index : int = None, forceName : bool = False) -> None:
        """
        Save the graph to a file

        Args:
            index (int, optional): index of the graph to save. Defaults to None.
        """
        if index is None:
            index = self.graphTabs.getActiveTabIndex()

        graph : GGraph = self.graphTabs.tabs.widget(index).layout.itemAt(0).widget()
        internalGraph : Graph = self.graphTabs.tabs.widget(index).layout.itemAt(0).widget().graph

        if internalGraph.GetSavePath() != "" and not forceName:
            filePath = internalGraph.GetSavePath()
        else:
            filePath, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save File", self.environment.Get("FLASH_ROOT"), "Flash Graph (*.fgraph)")

        if filePath != "":
            graph.saveGraph(filePath)

            self.graphTabs.tabs.setTabText(index, internalGraph.GetName())

    def loadGraph(self) -> None:
        """
        Loads a graph from a file
        """
        filePath, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open File", self.environment.Get("FLASH_ROOT"), "Flash Graph (*.fgraph)")
        
        if os.path.exists(filePath):
            newGGraph = GGraph(self.nodeLib, self.logger, self.environment)

            newGGraph.loadGraph(filePath)

            self.graphTabs.addTab(graph=newGGraph)

    def layoutGraph(self, index : int = None) -> None:
        """
        Layouts the graph at the given index 

        Args:
            index (int, optional): graph index. Defaults to None.
        """
        if index is None:
            index = self.graphTabs.getActiveTabIndex()

        self.graphTabs.tabs.widget(index).layout.itemAt(0).widget().layoutGraph()
        