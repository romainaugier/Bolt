from PyQt5 import QtCore, QtGui, QtWidgets


from FlashApp.Interface.GGraph import *


class GraphsEditor(QtWidgets.QWidget):
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

        self.addTab()

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
        gGraph.isCookingMovie.frameChanged.connect(lambda: self.tabs.setTabIcon(tabIndex, QtGui.QIcon(gGraph.getAnimationLogoMovie())))
        gGraph.hasBeenEdited.connect(lambda: (self.tabs.setTabIcon(tabIndex, self.iconsLib.GetIcon("graph-edited")), 
                                              self.tabs.setTabText(tabIndex, f"{gGraph.graph.GetName()}*")))
        gGraph.finishedCooking.connect(lambda: self.tabs.setTabIcon(tabIndex, self.iconsLib.GetIcon("graph-done")))
        gGraph.errorCooking.connect(lambda: self.tabs.setTabIcon(tabIndex, self.iconsLib.GetIcon("error")))
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