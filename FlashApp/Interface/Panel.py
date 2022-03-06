from PyQt5 import QtCore, QtGui, QtWidgets

from FlashApp.Interface.GraphsEditor import *


class TabType(QtWidgets.QWidget):
    """
    """

    name = "Tab Type"

    def __init__(self, iconsLib : Icons, logger : Logger, environment : Environment, parent=None) -> None:
        """
        """
        super().__init__(parent=parent)
        
        self.iconsLib = iconsLib
        self.logger = logger
        self.environment = environment

    def getName(self) -> str:
        """
        """
        return self.name


class TabTypeGraphsEditor(TabType):
    """
    """

    name = "Graphs Editor"

    def __init__(self, iconsLib : Icons, logger : Logger, environment : Environment, parent=None) -> None:
        """
        """
        super().__init__(iconsLib, logger, environment, parent=parent)

        self.masterLayout = QtWidgets.QVBoxLayout()

        self.masterLayout.addWidget(GraphsEditor(iconsLib, logger, environment))

        self.setLayout(self.masterLayout)


class TabTypeJobs(TabType):
    """
    """

    name = "Jobs"

    def __init__(self, iconsLib : Icons, logger : Logger, environment : Environment, parent=None) -> None:
        """
        """
        super().__init__(iconsLib, logger, environment, parent=parent)

class TabTypeGraphLibrary(TabType):
    """
    """

    name = "Graph Library"

    def __init__(self, iconsLib : Icons, logger : Logger, environment : Environment, parent=None) -> None:
        """
        """
        super().__init__(iconsLib, logger, environment, parent=parent)

class TabTypeGraphParameters(TabType):
    """
    """

    name = "Graph Parameters"

    def __init__(self, iconsLib : Icons, logger : Logger, environment : Environment, parent=None) -> None:
        """
        """
        super().__init__(iconsLib, logger, environment, parent=parent)
        
            
class TabButtons(QtWidgets.QWidget):
    """
    """
    
    addButtonClicked = QtCore.pyqtSignal()
    splitButtonClicked = QtCore.pyqtSignal(QtCore.QPoint)
    
    def __init__(self, addIcon : QtGui.QIcon, splitIcon : QtGui.QIcon, parent=None) -> None:
        """
        """
        super().__init__(parent=parent)
        
        self.masterLayout = QtWidgets.QHBoxLayout()
        
        self.addButton = QtWidgets.QToolButton(self)
        self.addButton.setIcon(addIcon)
        self.addButton.setFixedSize(16, 16)
        self.addButton.setIconSize(QtCore.QSize(16, 16))
        self.addButton.setStyleSheet("background: transparent")
        self.addButton.clicked.connect(self.addButtonClicked.emit)
        self.masterLayout.addWidget(self.addButton)
        
        self.splitButton = QtWidgets.QToolButton(self)
        self.splitButton.setFixedSize(16, 16)
        self.splitButton.setIcon(splitIcon)
        self.splitButton.setIconSize(QtCore.QSize(16, 16))
        self.splitButton.setStyleSheet("background: transparent")
        self.splitButton.clicked.connect(lambda: self.splitButtonClicked.emit(self.splitButton.mapToGlobal(self.splitButton.pos())))
        self.masterLayout.addWidget(self.splitButton)
        
        self.setLayout(self.masterLayout)
        
    def getAddButton(self) -> QtWidgets.QToolButton:
        """
        """
        return self.addButton
    
    def getSplitButton(self) -> QtWidgets.QToolButton:
        """
        """
        return self.splitButton
            
            
class Tab(QtWidgets.QTabWidget):
    """
    """
    
    splitButtonClicked = QtCore.pyqtSignal(QtCore.QPoint)
    
    def __init__(self, iconsLib : Icons, logger : Logger, environment : Environment, parent=None) -> None:
        """
        """
        super().__init__(parent=parent)
        
        self.iconsLib = iconsLib
        self.logger = logger
        self.environment = environment
        
        self.setMovable(True)
        self.setTabsClosable(True)
        
        addPixmap = self.iconsLib.GetColoredPixmap("add-button", GetQColorFromPalette(ColorPalette.FOREGROUND))
        splitPixmap = self.iconsLib.GetColoredPixmap("split-button", GetQColorFromPalette(ColorPalette.FOREGROUND))
        
        self.buttons = TabButtons(QtGui.QIcon(addPixmap), QtGui.QIcon(splitPixmap))
        self.buttons.addButtonClicked.connect(self.addTabMenu)
        self.buttons.splitButtonClicked.connect(self.splitButtonClicked)
        self.setCornerWidget(self.buttons)
        
        self.tabCloseRequested.connect(self.removeTab)
        
        self.addGraphEditor()

    def removeTab(self, index : int) -> None:
        """
        """
        if self.count() > 1:
            super().removeTab(index)

    def addGraphEditor(self) -> None:
        """
        """
        graphEditor = TabTypeGraphsEditor(self.iconsLib, self.logger, self.environment)

        self.addTab(graphEditor, graphEditor.getName())
        
    def addTabMenu(self) -> None:
        """
        """
        menu = ContextMenu()
        
        addGraphAction = menu.addAction("Add Graph Editor")
        addGraphAction.triggered.connect(self.addGraphEditor)
        
        menu.exec_(self.buttons.getAddButton().mapToGlobal(self.buttons.getAddButton().pos()))
        
        
class TabWidget(QtWidgets.QWidget):
    """
    """
    def __init__(self, iconsLib : Icons, logger : Logger, environment : Environment, parent=None) -> None:
        """
        """
        super().__init__(parent=parent)
        
        self.tab = Tab(iconsLib, logger, environment, parent)
        
        masterLayout = QtWidgets.QVBoxLayout()
        
        masterLayout.setSpacing(0)
        masterLayout.setContentsMargins(10, 10, 10, 10)
        
        masterLayout.addWidget(self.tab)
        
        self.setLayout(masterLayout)
        
    def getTab(self) -> Tab:
        """
        """
        return self.tab


class Panel(QtWidgets.QWidget):
    """
    Class used to hold a widget that is used as a panel for the application
    Trying to replicate houdini tabs and splitter system which I like a lot

    This widget holds 2 widgets : 
    - the principal widget, which is a Tab with at least one tab (default is a graph)
    - the splitter widget, which contains 2 widgets that are 2 tabs (and one of them is the principal widget)
    """

    def __init__(self, index : int, iconsLib : Icons, logger : Logger, environment : Environment, principalWidget : TabWidget = None, parent=None) -> None:
        """
        """
        super().__init__(parent=parent)
        
        self.index = index
        self.iconsLib = iconsLib
        self.logger = logger
        self.environment = environment
        
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

        self.masterLayout = QtWidgets.QVBoxLayout()
        self.masterLayout.setSpacing(0)
        self.masterLayout.setContentsMargins(0, 0, 0, 0)

        self.splitterWidget = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.splitterWidget.setContentsMargins(0, 0, 0, 0)
        
        if principalWidget is not None:
            self.principalWidget = principalWidget
            self.principalWidget.getTab().splitButtonClicked.connect(self.splitterMenu)
        else:
            self.principalWidget = TabWidget(self.iconsLib, self.logger, self.environment)
            self.principalWidget.getTab().splitButtonClicked.connect(self.splitterMenu)
        
        self.stackWidget = QtWidgets.QStackedWidget()

        self.stackWidget.addWidget(self.principalWidget)
        self.stackWidget.addWidget(self.splitterWidget)

        self.masterLayout.addWidget(self.stackWidget)
        
        self.showPrincipalWidget()
        
        self.setLayout(self.masterLayout)
    
    # GETTERS / SETTERS

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
        self.stackWidget.setCurrentIndex(0)

        self.splitterWidgetIsActive = False

    def showSplitterWidget(self) -> None:
        """
        """
        self.stackWidget.setCurrentIndex(1)
        
        self.splitterWidgetIsActive = True

    def activateSplitterWidget(self) -> None:
        """
        """
        if self.getSplitterWidget().count() > 1:
            self.splitterWidget.widget(0).deleteLater()
            self.splitterWidget.widget(1).deleteLater()
            
        self.principalWidget.getTab().splitButtonClicked.disconnect()

        leftPanel = Panel(0, self.iconsLib, self.logger, self.environment, self.principalWidget, parent=self)
        rightPanel = Panel(1, self.iconsLib, self.logger, self.environment, parent=self)

        self.splitterWidget.addWidget(leftPanel)
        self.splitterWidget.addWidget(rightPanel)
        
        self.showSplitterWidget()

    def setSplitterWidgetOrientation(self, orientation : QtCore.Qt.Orientation) -> None:
        """
        """
        self.getSplitterWidget().setOrientation(orientation)

    def isSplitterWidgetActive(self) -> bool:
        """
        """
        return self.splitterWidgetIsActive
    
    def closePanel(self) -> None:
        """
        """
        parent = self.parentWidget()
        
        if isinstance(parent, QtWidgets.QSplitter):
            if self.index == 0:
                topParent = parent.parentWidget().parentWidget()
                
                print("idx0", topParent)
                
                if isinstance(topParent, Panel):
                    if self.isSplitterWidgetActive():
                        topParent.setSplitterWidget(self.splitterWidget)
                        topParent.showSplitterWidget()
                    else:
                        topParent.setPrincipalWidget(self.principalWidget)
                        topParent.showPrincipalWidget()
            else:
                topParent = parent.parentWidget().parentWidget()
                
                print("idx1", topParent)
                
                if isinstance(topParent, Panel):
                    if self.isSplitterWidgetActive():
                        topParent.setSplitterWidget(self.splitterWidget)
                        topParent.showSplitterWidget()
                    else:
                        topParent.setPrincipalWidget(self.principalWidget)
                        topParent.showPrincipalWidget()
            
                if parent.count() == 1:
                    self.index = 0
                
            parent.widget(self.index).deleteLater()
            self.close()
            self.setParent(None)
    
    @QtCore.pyqtSlot(QtCore.QPoint)
    def splitterMenu(self, position : QtCore.QPoint) -> None:
        """
        """
        menu = ContextMenu()
        
        splitHorizontallyAction = menu.addAction("Split Horizontally")
        splitHorizontallyAction.triggered.connect(lambda: (self.setSplitterWidgetOrientation(QtCore.Qt.Horizontal), self.activateSplitterWidget()))
        
        splitVerticallyAction = menu.addAction("Split Vertically")
        splitVerticallyAction.triggered.connect(lambda: (self.setSplitterWidgetOrientation(QtCore.Qt.Vertical), self.activateSplitterWidget()))
        
        closeAction = menu.addAction("Close")
        closeAction.triggered.connect(lambda: self.closePanel())
        
        menu.exec_(QtCore.QPoint(position.x() - 50, position.y()))