from PyQt5 import QtCore, QtGui, QtWidgets

from FlashApp.Interface.GraphsEditor import *


class TabType(QtWidgets.QWidget):
    """
    """

    name = "Tab Type"

    def __init__(self, parent=None) -> None:
        """
        """
        super().__init__(parent=parent)

    def getName(self) -> str:
        """
        """
        return self.name


class TabTypeGraphsEditor(TabType):
    """
    """

    name = "Graphs Editor"

    def __init__(self, parent=None) -> None:
        """
        """
        super().__init__(parent=parent)

        self.masterLayout = QtWidgets.QVBoxLayout()

        self.masterLayout.addWidget(GraphsEditor())

        self.setLayout(self.masterLayout)


class TabTypeJobs(TabType):
    """
    """

    name = "Jobs"


class TabTypeGraphLibrary(TabType):
    """
    """

    name = "Graph Library"


class TabTypeGraphParameters(TabType):
    """
    """

    name = "Graph Parameters"


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
        sizeHint = QtWidgets.QTabBar.sizeHint(self)
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
        self._tabBar.tabMoved.connect(self._tabBar.moveAddButton)
        self.tabCloseRequested.connect(self.removeTab)

    def removeTab(self, index : int) -> None:
        """
        """
        if self.count() > 1:
            super().removeTab(index)

    def addGraphEditor(self) -> None:
        """
        """
        graphEditor = TabTypeGraphsEditor()

        self.addTab(graphEditor, graphEditor.getName())


class Panel(QtWidgets.QWidget):
    """
    Class used to hold a widget that is used as a panel for the application
    Trying to replicate houdini tabs and splitter system which I like a lot

    This widget holds 2 widgets : 
    - the principal widget, which is a Tab with at least one tab (default is a graph)
    - the splitter widget, which contains 2 widgets that are 2 tabs (and one of them is the principal widget)
    """

    def __init__(self, parent=None) -> None:
        """
        """
        super().__init__(parent=parent)

        self.masterLayout = QtWidgets.QVBoxLayout()

        self.splitterWidget = QtWidgets.QSplitter()
        self.principalWidget = Tab()

        self.showPrincipalWidget()

        self.masterLayout.addWidget(self.splitterWidget)
        self.masterLayout.addWidget(self.principalWidget)

        self.setLayout(self.masterLayout)

    def getPrincipalWidget(self) -> QtWidgets.QWidget:
        """
        """
        return self.principalWidget

    def setPrincipalWidget(self, widget : QtWidgets.QWidget) -> None:
        """
        """
        self.principalWidget = widget

    def getSplitterWidget(self) -> QtWidgets.QSplitter:
        """
        """
        return self.splitterWidget

    def setSplitterWidget(self, widget : QtWidgets.QSplitter) -> None:
        """
        """
        self.splitterWidget = widget

    def showPrincipalWidget(self) -> None:
        """
        """
        self.getPrincipalWidget().show()
        self.getSplitterWidget().hide()

        self.splitterWidgetIsActive = False

    def showSplitterWidget(self) -> None:
        """
        """
        self.getPrincipalWidget().hide()
        self.getSplitterWidget().show()
        
        self.splitterWidgetIsActive = True

    def activateSplitterWidget(self) -> None:
        """
        """
        if self.getSplitterWidget().count() > 1:
            self.getSplitterWidget().widget(0).deleteLater()
            self.getSplitterWidget().widget(1).deleteLater()

        self.getSplitterWidget().addWidget(Panel())
        self.getSplitterWidget().addWidget(Panel())

    def setSplitterWidgetOrientation(self, orientation : QtCore.Qt.Orientation) -> None:
        """
        """
        self.getSplitterWidget().setOrientation(orientation)

    def isSplitterWidgetActive(self) -> bool:
        """
        """
        return self.splitterWidgetIsActive

    def getActiveWidget(self) -> QtWidgets.QWidget:
        """
        Go through all widgets and find the one that is focused
        """
        if self.isSplitterWidgetActive():
            for i in range(2):
                widget = self.getSplitterWidget().widget(i)

                if widget.isSplitterWidgetActive():
                    activeWidget = widget.getActiveWidget()

                    if activeWidget is not None:
                        return activeWidget

                elif widget.hasFocus():
                    return widget

        else:
            if self.getPrincipalWidget().hasFocus():
                return self.getPrincipalWidget()
            else:
                return None