import os

from PyQt5 import QtCore, QtGui, QtWidgets

from FlashApp.Interface.Graph import *

class Icons():
    """
    """
    def __init__(self):
        """
        """
        # TODO : link with runtime path
        self.iconFolderPath = "D:/dev/Flash/Library/Icons"

        self.icons = {}

        allIcons = os.listdir(self.iconFolderPath)

        for icon in allIcons:
            name, _ = os.path.splitext(icon)
            path = os.path.join(self.iconFolderPath, icon)

            self.icons[name] = QtGui.QIcon(QtGui.QPixmap(path))

    def Get(self, name):
        """
        """
        return self.icons[name]

class GraphTabs(QtWidgets.QWidget):
    """
    """
    def __init__(self, nodeLib : Lib, parent):
        super(QtWidgets.QWidget, self).__init__(parent)

        self.nodeLib = nodeLib

        self.layout = QtWidgets.QVBoxLayout(self)

        self.tabs = QtWidgets.QTabWidget()

        self.newTab = QtWidgets.QWidget()

        self.tabs.addTab(self.newTab, "Main")

        self.newTab.layout = QtWidgets.QVBoxLayout()
        self.gGraph = GGraph(self.nodeLib)
        self.gGraph.setFrameStyle(QtWidgets.QFrame.NoFrame)
        self.newTab.layout.addWidget(self.gGraph)
        self.newTab.setLayout(self.newTab.layout)

        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)

    def addTab(self, graph : GGraph = None) -> None:
        """
        Adds a new tab with a graph if provided

        Args:
            graph (GGraph, optional): Graph to load. Defaults to None.
        """
        self.newTab = QtWidgets.QWidget()

        self.tabs.addTab(self.newTab, "New*")

        self.newTab.layout = QtWidgets.QVBoxLayout()
        self.gGraph = GGraph(self.nodeLib)
        self.gGraph.setFrameStyle(QtWidgets.QFrame.NoFrame)
        self.newTab.layout.addWidget(self.gGraph)
        self.newTab.setLayout(self.newTab.layout)

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

        self.nodeLib = Lib()

        self.icons = Icons()

        self.setWindowTitle("Flash")
  
        self.setWindowIcon(self.icons.Get("flash"))

        masterLayout = QtWidgets.QVBoxLayout()
        masterWidget = QtWidgets.QWidget()

        # Shelf

        shelfLayout = QtWidgets.QHBoxLayout()
        shelfLayout.setAlignment(Qt.AlignLeft)

        self.newGraphButton = QtWidgets.QPushButton("")
        self.newGraphButton.setIcon(self.icons.Get("graph"))
        self.newGraphButton.setToolTip("Create New Graph")
        self.newGraphButton.clicked.connect(lambda: self.graphTabs.addTab())
        shelfLayout.addWidget(self.newGraphButton)

        self.addNodeButton = QtWidgets.QPushButton("")
        self.addNodeButton.setIcon(self.icons.Get("add-plus-button"))
        self.addNodeButton.setToolTip("Add Node")
        shelfLayout.addWidget(self.addNodeButton)

        self.movie = QtGui.QMovie("Icons/anim-load.gif")
        self.movie.setScaledSize(QtCore.QSize(50, 50))
        self.testLabel = QtWidgets.QLabel("")
        self.testLabel.setMovie(self.movie)
        self.movie.start()
        shelfLayout.addWidget(self.testLabel)

        masterLayout.addLayout(shelfLayout)

        # Graphs

        self.graphTabs = GraphTabs(self.nodeLib, self)
        masterLayout.addWidget(self.graphTabs)

        masterWidget.setLayout(masterLayout)

        self.setCentralWidget(masterWidget)