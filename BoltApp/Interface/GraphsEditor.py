from PyQt5 import QtCore, QtGui, QtWidgets


from BoltApp.Interface.GGraph import *


class GraphViewer(QtWidgets.QWidget):
    """
    """

    selectedNodeChanged = QtCore.pyqtSignal(str)

    def __init__(self, icons : Icons, logger : Logger, environment : Environment, parent=None):
        super(QtWidgets.QWidget, self).__init__(parent)

        self.nodeLib = Lib(logger, environment)
        self.environment = environment
        self.iconsLib = icons
        self.logger = logger
        
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setAcceptDrops(True)

        self._layout = QtWidgets.QVBoxLayout(self)
        self._layout.setSpacing(0)
        self._layout.setContentsMargins(0, 0, 0, 0)

        self.tabs = QtWidgets.QTabWidget()

        self._layout.addWidget(self.tabs)
        self.setLayout(self._layout)

        self.addTab()

    # SLOTS

    @QtCore.pyqtSlot(str)
    def onNodeSelectionChange(self, nodeId : str) -> None:
        self.selectedNodeChanged.emit(nodeId)
        
    # UTILS
    
    def updateGraphTabIndexes(self) -> None:
        """
        Updates the tab index of the different graphs
        """
        for i in range(self.tabs.count()):
            graph = self.tabs.widget(i).layout().itemAt(0).widget()
            
            graph.setTabIndex(i)
        
    # TAB METHODS
        
    def addTab(self, graph : GGraph = None) -> None:
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
            gGraph = GGraph(self.nodeLib, self.logger, self.environment)
            
        gGraph.setFocusProxy(self)
        gGraph.setTabIndex(tabIndex)

        self.tabs.addTab(self.newTab, self.iconsLib.GetIcon("edited"), f"{gGraph.graph.GetName()}")
        self.tabs.setIconSize(QtCore.QSize(18, 18))

        self.newTab._layout = QtWidgets.QVBoxLayout()
        gGraph.setFrameStyle(QtWidgets.QFrame.NoFrame)
        gGraph.isCookingMovie.frameChanged.connect(lambda: self.tabs.setTabIcon(gGraph.getTabIndex(), QtGui.QIcon(gGraph.getAnimationLogoMovie())))
        gGraph.hasBeenEdited.connect(lambda: (self.tabs.setTabIcon(gGraph.getTabIndex(), self.iconsLib.GetIcon("edited")), 
                                              self.tabs.setTabText(gGraph.getTabIndex(), f"{gGraph.graph.GetName()}*")))
        gGraph.finishedCooking.connect(lambda: self.tabs.setTabIcon(gGraph.getTabIndex(), self.iconsLib.GetIcon("done")))
        gGraph.errorCooking.connect(lambda: self.tabs.setTabIcon(gGraph.getTabIndex(), self.iconsLib.GetIcon("error")))
        gGraph.selectedNodeChanged.connect(self.onNodeSelectionChange)

        self.newTab._layout.addWidget(gGraph)
        self.newTab.setLayout(self.newTab._layout)

        self.tabs.setCurrentIndex(tabIndex)

    def removeTab(self, index : int) -> None:
        """
        Removes a tab

        Args:
            index (int): tab index to remove
        """
        self.tabs.removeTab(index)
        
        self.updateGraphTabIndexes()
        
    def removeActiveTab(self) -> None:
        """
        Removes the active tab
        """
        self.removeTab(self.tabs.currentIndex())

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
        
    def cookActiveGraph(self) -> None:
        """
        Cooks the graph in the active tab
        """
        index = self.tabs.currentIndex()
        self.tabs.widget(index).layout().itemAt(0).widget().launchGraphCooking(skipCookedNodes=False)
        
    def saveActiveGraph(self, forceName : bool = False) -> None:
        """
        Save the active graph to a file

        Args:
            forceName (bool) : force renaming the file. Defaults to False.
        """
        index = self.getActiveTabIndex()

        graph : GGraph = self.tabs.widget(index).layout().itemAt(0).widget()
        internalGraph : Graph = graph.getInternalGraph()

        if internalGraph.GetSavePath() != "" and not forceName:
            filePath = internalGraph.GetSavePath()
        else:
            filePath, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save File", self.environment.Get("BOLT_ROOT"), "Bolt Graph (*.bgraph)")

        if filePath != "":
            graph.saveGraph(filePath)

            self.tabs.setTabText(index, internalGraph.GetName())

    def loadNewGraph(self, filePath : str = None) -> None:
        """
        Loads a graph from a file
        """
        if filePath is None:
            filePath, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open File", self.environment.Get("BOLT_ROOT"), "Bolt Graph (*.bgraph)")
        
        if os.path.exists(filePath):
            newGGraph = GGraph(self.nodeLib, self.logger, self.environment)

            newGGraph.loadGraph(filePath)

            self.addTab(graph=newGGraph)

    def layoutActiveGraph(self) -> None:
        """
        Layouts the active graph
        """
        index = self.getActiveTabIndex()

        self.tabs.widget(index).layout().itemAt(0).widget().layoutGraph()
        
    def stopActiveGraph(self) -> None:
        """
        Force the active graph to stop the cooking if it is cooking
        """
        index = self.getActiveTabIndex()

        self.tabs.widget(index).layout().itemAt(0).widget().stopGraphCooking()
        
    def showActiveGraphPlugEditor(self) -> None:
        """
        Shows/Hides the plug editor of the active graph
        """
        index = self.getActiveTabIndex()

        self.tabs.widget(index).layout().itemAt(0).widget().showPlugEditor()
        
    # EVENTS

    def keyPressEvent(self, event : QtGui.QKeyEvent) -> None:
        """
        """
        if self.tabs.count() > 0:
            index = self.getActiveTabIndex()
            activeLayout = self.tabs.widget(index).layout()

            if activeLayout.count():
                activeGraph = activeLayout.itemAt(0).widget()

                activeGraph.keyPressEvent(event)

        return super().keyPressEvent(event)
    
    def dragEnterEvent(self, event : QtGui.QDragEnterEvent):
        """
        """
        eventAccepted = False
        
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                itemPath = url.toLocalFile()
                if ".bgraph" in itemPath:
                    event.accept()
                    eventAccepted = True
        
        if eventAccepted:
            event.accept()
        else:
            return super().dragEnterEvent(event)

    def dropEvent(self, event : QtGui.QDragEnterEvent):
        """
        """
        eventAccepted = False
        
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                itemPath = url.toLocalFile()
                if ".bgraph" in itemPath:
                    
                    if os.path.isfile(itemPath):
                        self.loadNewGraph(itemPath)
                        
                        event.setDropAction(QtCore.Qt.CopyAction)
                        event.accept()
                        eventAccepted = True
        
        if eventAccepted:
            event.accept()
        else:
            return super().dropEvent(event)