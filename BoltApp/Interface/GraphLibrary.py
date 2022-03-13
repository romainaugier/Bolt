from PyQt5 import QtCore, QtGui, QtWidgets

from BoltApi.Core.Environment import Environment

from BoltApp.Interface.Icons import *
from BoltApp.Interface.Style import GetQColorFromPalette, ColorPalette

class GraphLibrary(QtWidgets.QWidget):
    """
    """
    def __init__(self, environment : Environment, iconsLib : Icons, parent=None):
        """
        """
        super().__init__(parent=parent)
        
        self.environment = environment
        self.iconsLib = iconsLib
        
        libPaths = self.environment.Get("BOLT_GRAPHS_LIBS").split(";")
        self.libPaths = []
        
        for path in libPaths:
            if path != "":
                self.libPaths.append(path)
            
        if len(self.libPaths) == 0:
            self.libPaths.append("$BOLT_LIB/Graphs")
        
        self.filesystem = QtWidgets.QFileSystemModel()
        self.filesystem.setRootPath(self.environment.ReplaceInString(self.libPaths[0]))
        
        self.masterLayout = QtWidgets.QVBoxLayout()
        
        self.librarySearchBarLayout = QtWidgets.QHBoxLayout()
        
        self.librariesComboBox = QtWidgets.QComboBox()
        self.librariesComboBox.setMinimumHeight(20)
        self.librariesComboBox.addItems(self.libPaths)
        self.librariesComboBox.currentIndexChanged.connect(self.updateTreeView)
        self.librarySearchBarLayout.addWidget(self.librariesComboBox)
        
        self.addPathButton = QtWidgets.QToolButton(self)
        self.addPathButton.setIcon(QtGui.QIcon(self.iconsLib.GetColoredPixmap("add-button", 
                                    GetQColorFromPalette(ColorPalette.GREENCOLOR)).scaled(20, 20, QtCore.Qt.IgnoreAspectRatio, QtCore.Qt.SmoothTransformation)))
        self.addPathButton.setIconSize(QtCore.QSize(20, 20))
        self.addPathButton.setStyleSheet("background-color: transparent")
        self.addPathButton.clicked.connect(self.addNewLibPath)
        self.librarySearchBarLayout.addWidget(self.addPathButton)
        
        self.masterLayout.addLayout(self.librarySearchBarLayout)
        
        self.masterLayout.addSpacing(10)
        
        self.libraryTree = QtWidgets.QTreeView()
        self.libraryTree.setFrameStyle(QtWidgets.QFrame.NoFrame)
        self.libraryTree.setAlternatingRowColors(True)
        self.libraryTree.setDragEnabled(True)
        self.libraryTree.setModel(self.filesystem)
        self.libraryTree.setRootIndex(self.filesystem.index(self.environment.ReplaceInString(self.libPaths[0])))
        self.libraryTree.hideColumn(1)
        self.libraryTree.hideColumn(2)
        self.libraryTree.hideColumn(3)
        self.masterLayout.addWidget(self.libraryTree)
        
        self.setLayout(self.masterLayout)
        
    def addNewLibPath(self) -> None:
        """
        """
        path = QtWidgets.QFileDialog.getExistingDirectory(self)
        
        if os.path.exists(path):
            self.libPaths.append(path)
            
        self.librariesComboBox.clear()
        self.librariesComboBox.addItems(self.libPaths)
        
    def updateTreeView(self) -> None:
        """
        """
        currentPath = self.environment.ReplaceInString(self.librariesComboBox.currentText())
        
        self.filesystem.setRootPath(currentPath)
        self.libraryTree.setRootIndex(self.filesystem.index(currentPath))
        self.libraryTree.hideColumn(1)
        self.libraryTree.hideColumn(2)
        self.libraryTree.hideColumn(3)
        
        
        