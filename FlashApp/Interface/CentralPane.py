from PyQt5 import QtCore, QtGui, QtWidgets

class TabBarPlus(QtWidgets.QTabBar):
    """
    Tab bar with a plus button to add a tab
    """
    
    addTab = QtCore.pyqtSignal()
    
    def __init__(self, parent=None) -> None:
        """
        """
        super().__init__(parent=parent)
        
        self.addButton = QtWidgets.QPushButton("+")
        self.addButton.setParent(self)
        self.addButton.setFixedSize(10, 10)
        self.addButton.clicked.connect(self.addTab.emit)
        self.moveAddButton()
        
    def sizeHint(self) -> QtCore.QSize:
        """
        Returns the size of the tabbar plus the button width
        """
        sizeHint = QtGui.QTabBar.sizeHint(self)
        width = sizeHint.width()
        height = sizeHint.height()
        
        return QtCore.QSize(width + 15, height)
        
    def resizeEvent(self, event) -> None:
        """
        """
        super().resizeEvent(event)
        
        self.moveAddButton()
        
    def tabLayoutChanged(self) -> None:
        """
        """
        super().tabLayoutChanged()
        
        self.moveAddButton()
        
    def moveAddButton(self) -> None:
        """
        """
        size = sum([self.tabRect(i).width() for i in range(self.count())])
        
        h = self.geometry().top()
        w = self.width()
        
        if size > w:
            self.addButton.move(w - 54, h)
        else:
            self.addButton.move(size, h)
            
            
class Tab(QtWidgets.QTabWidget):
    """
    """
    def __init__(self, parent=None) -> None:
        """
        """
        super().__init__(parent=parent)
        
        self._tabBar = TabBarPlus()
        self.setTabBar(self._tabBar)
        
        self.setMovable(True)
        self.setTabsClosable(True)
        
        self._tabBar.addTab.connect(self.addTab)
        self._tabBar.tabMoved.connect(self.moveTab)
        self.tabCloseRequested.connect(self.removeTab)


class Panel(QtGui.QTabWidget):
    """
    Class used to hold a widget that is used as a panel for the application
    Trying to replicate houdini tabs and splitter system which I like a lot
    """
        
        