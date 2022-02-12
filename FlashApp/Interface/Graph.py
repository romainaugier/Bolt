import json, threading

from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtCore import Qt

from FlashApp.Interface.Node import *
from FlashApi.Core.Lib import *
from FlashApi.Core.Graph import *
from FlashApi.Core.Logger import *
from FlashApp.Interface.Icons import *

class GraphicsScene(QtWidgets.QGraphicsScene):
    """
    Reimplementation of the graphics scene
    """
    def __init__(self, parent=None) -> None:
        """
        """
        super(QtWidgets.QGraphicsScene, self).__init__(parent)


class GGraph(QtWidgets.QGraphicsView):
    """
    Graphics view of the current graph
    """
    startCooking = QtCore.pyqtSignal()
    finishedCooking = QtCore.pyqtSignal()
    errorCooking = QtCore.pyqtSignal()
    hasBeenEdited = QtCore.pyqtSignal()

    threadCanJoin = QtCore.pyqtSignal()

    selectedNodeChanged = QtCore.pyqtSignal(str)

    def __init__(self, nodeLib : Lib, logger : Logger, graph : Graph = None) -> None:
        """
        """
        super().__init__()

        self.logger = logger

        self.scene = GraphicsScene(self) 

        self.iconsLib = Icons()
        self.isCookingMovie = self.iconsLib.GetAnim("graph-cooking")

        self.nodeLibrary = nodeLib
        nodeLib.Load()

        if graph is not None:
            self.graph = graph
            self.constructGraphFromInternalGraph()
        else:
            self.graph = Graph(self.logger, "New")

        self.gEdges = []

        # Graphic nodes
        self.gNodes = []

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.scene.setItemIndexMethod(QtWidgets.QGraphicsScene.NoIndex)
        self.scene.setSceneRect(0, 0, 800, 800)
        self.setScene(self.scene)
        self.setCacheMode(QtWidgets.QGraphicsView.CacheBackground)
        self.setViewportUpdateMode(QtWidgets.QGraphicsView.BoundingRectViewportUpdate)
        self.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.TextAntialiasing | QtGui.QPainter.SmoothPixmapTransform)
        self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setContextMenuPolicy(Qt.DefaultContextMenu)

        self.setMinimumSize(800, 800)

        self.startPos = None
        self.pan = False
        self.setMouseTracking(True)

        self.cookThread = None
        self.threadCanJoin.connect(lambda: self.joinGraphThread())

        QtWidgets.QApplication.instance().installEventFilter(self)

    @QtCore.pyqtSlot(str)
    def onNodeSelectionChange(self, nodeId : str) -> None:
        self.selectedNodeChanged.emit(nodeId)

    def getAnimationLogoMovie(self) -> QtGui.QMovie:
        """     
        Returns:
            QtGui.QMovie: movie
        """
        return self.isCookingMovie

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        """
        """
        key = event.key()

        if key == Qt.Key_Plus:
            self.scaleView(1.2)
        elif key == Qt.Key_Minus:
            self.scaleView(1 / 1.2)
        elif key == Qt.Key_Delete:
            self.deleteItem()

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.MiddleButton and self.startPos is None:
            self.startPos = event.pos()
            self.prevPos = event.pos()
            self.pan = True
        
        return super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        if self.pan:
            delta = self.prevPos - event.pos()

            transform = self.transform()

            deltaX = delta.x() / transform.m11()
            deltaY = delta.y() / transform.m22()

            self.setSceneRect(self.sceneRect().translated(deltaX, deltaY))

            self.prevPos = event.pos()

        return super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.MiddleButton and self.startPos is not None:
            self.startPos = None
            self.pan = False

        return super().mouseReleaseEvent(event)

    def eventFilter(self, obj: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if event.type() == QtCore.QEvent.Wheel:
            oldPos = self.mapToScene(event.pos())

            if event.angleDelta().y() > 0:
                # self.scaleView(1.01)
                self.scale(1.01, 1.01)
            else:
                # self.scaleView(0.99)
                self.scale(0.99, 0.99)

            newPos = self.mapToScene(event.pos())

            delta = newPos - oldPos

            self.translate(delta.x(), delta.y())

            return super().eventFilter(obj, event)

        elif event.type() == QtCore.QEvent.MouseButtonPress and event.button() == QtCore.Qt.LeftButton:
            self.scene.clearSelection()
            self.scene.selectedItems()
            return super().eventFilter(obj, event)
            
        return super().eventFilter(obj, event)
            

    def scaleView(self, scaleFactor: float) -> None:
        """
        """
        factor = self.transform().scale(scaleFactor, scaleFactor).mapRect(QtCore.QRectF(0, 0, 1, 1)).width()

        if factor < 0.07 or factor > 100:
            return

        self.scale(scaleFactor, scaleFactor)

    def addNode(self, nodeType : str, position : QtCore.QPointF) -> None:
        """
        """
        tmpInternalNode = self.nodeLibrary.Get(nodeType)
        self.graph.AddNode(tmpInternalNode)

        tmpGNode = GNode(tmpInternalNode, "", self, self.iconsLib)
        tmpGNode.hasBeenSelected.connect(self.onNodeSelectionChange)
        tmpGNode.setPos(position)

        self.scene.addItem(tmpGNode)

        self.hasBeenEdited.emit()

    def addNodeFromInternalGraph(self, node : Node) -> None:
        """
        Adds an existing internal node to the scene

        Args:
            node (Node): internal node
        """
        tmpGNode = GNode(node, "", self, self.iconsLib)

        tmpGNode.hasBeenSelected.connect(self.onNodeSelectionChange)

        self.scene.addItem(tmpGNode)

    def deleteNode(self, node: GNode) -> None:
        """
        """
        for sock in node.inputGPlugs:
            for edge in sock.edges[:]:
                self.deleteEdge(edge)
        
        for sock in node.outputGPlugs:
            for edge in sock.edges[:]:
                self.deleteEdge(edge)

        self.graph.RemoveNode(node.getInternalNode())

        self.scene.removeItem(node)

        self.hasBeenEdited.emit()

    def getNodeById(self, nodeId : str) -> GNode:
        """
        """
        for item in self.scene.items():
            if type(item) is GNode:
                if item.id == nodeId:
                    return item

    def addEdge(self, outputGPlug: GPlug, inputGPlug: GPlug, connectInternally : bool = True) -> None:
        """
        """
        if connectInternally: 
            outputGPlug.getInternalPlug().Connect(inputGPlug.getInternalPlug())

        self.logger.Log(LogLevel.DIAGNOSTIC, f"New Connection : {outputGPlug.getInternalPlug().GetShortName()} -> {inputGPlug.getInternalPlug().GetShortName()}")

        newEdge = Edge(outputGPlug, inputGPlug)

        self.scene.addItem(newEdge)

        self.hasBeenEdited.emit()

    def deleteEdge(self, edge: Edge) -> None:
        """
        """
        edge.source.getInternalPlug().Disconnect(edge.destination.getInternalPlug())

        edge.source.edges.remove(edge)
        edge.destination.edges.remove(edge)

        self.scene.removeItem(edge)

        self.hasBeenEdited.emit()

    def updateAllEdges(self) -> None:
        """
        """
        for item in self.items():
            if type(item) is Edge:
                item.adjust()

    def deleteItem(self) -> None:
        """
        """
        items = self.scene.selectedItems()

        if len(items) > 0: 
            item = items[0]
            
            if type(item) is GNode:
                self.deleteNode(item)
            elif type(item) is GPlug:
                node = item.node
                self.deleteNode(node)
            elif type(item) is Edge:
                self.deleteEdge(item)

    def cookGraph(self) -> None:
        """
        Cooks the graph
        """
        self.startCooking.emit()
        self.graph.Cook()
        self.threadCanJoin.emit()

    def launchGraphCooking(self) -> None:
        """
        Launches the thread that cooks the graph
        """
        self.isCookingMovie.start()
        self.cookThread = threading.Thread(target=self.cookGraph)
        self.cookThread.start()

    def joinGraphThread(self) -> None:
        """
        Joins the thread that cooks the graph
        """
        if self.cookThread is not None:
            self.cookThread.join()
            self.isCookingMovie.stop()

            self.finishedCooking.emit()

            if self.graph.hasError:
                self.errorCooking.emit()

    def debugGraph(self) -> None:
        """
        """
        print("Nodes : ")
        print(json.dumps([node.GetName() for node in self.graph.nodes], indent=4))
        
        self.graph.Sort()

        print("Sorted Nodes : ")
        print(json.dumps([node.GetName() for node in self.graph.sortedNodes], indent=4))

    def constructGraphFromInternalGraph(self) -> None:
        """
        Constructs the scene from a graph
        """
        for item in self.scene.items():
            if type(item) is GNode:
                self.deleteNode(item)
            elif type(item) is GPlug:
                node = item.node
                self.deleteNode(node)
            elif type(item) is Edge:
                self.deleteEdge(item)

        for node in self.graph.GetNodes():
            self.addNodeFromInternalGraph(node)

        for node in self.graph.GetNodes():
            gNode = self.getNodeById(node.GetID())

            for outputName, output in node.GetOutputs().items():
                if output.IsConnected():

                    for connection in output.GetConnections():
                        connectedGNode =  self.getNodeById(connection.GetNode().GetID())
                        self.addEdge(gNode.getOutputGPlug(outputName), connectedGNode.getInputGPlug(connection.GetShortName()), False)

        self.layoutGraph()

    def layoutGraph(self) -> None:
        """
        """
        self.graph.Sort()

        nodesNeedLayout = True

        iterations = 0

        while nodesNeedLayout == True:
        # while iterations < 2:
            for i, node in enumerate(self.graph.sortedNodes):
                gNode = self.getNodeById(node.GetID())

                gNodePos = gNode.pos() + QtCore.QPointF(gNode.sizeX / 2, gNode.sizeY / 2)

                if gNode.getInternalNode().GetOutputCount() > 0:
                    output = gNode.getInternalNode().GetOutput(index=0)

                    if output.IsConnected():
                        outGPlug = gNode.getOutputGPlug(output.GetShortName())
                        otherGNode = self.getNodeById(output.GetConnections()[0].GetNode().GetID())

                        inGPlug = otherGNode.getInputGPlug(output.GetConnections()[0].GetShortName())

                        pluggedNode = self.getNodeById(inGPlug.getInternalPlug().GetNode().GetID())
                        newPos = pluggedNode.pos() 
                        gNode.setPos(newPos.x() - 50, newPos.y())
                        gNode.adjustEdges()

                for item in self.scene.items():
                    if type(item) is not GNode or item.id == gNode.id:
                        continue

                    itemPos = item.scenePos()
                    itemPos = QtCore.QPointF(itemPos.x() + item.sizeX / 2, itemPos.y() + item.sizeY / 2)

                    if abs(itemPos.x() - gNodePos.x()) < (gNode.sizeX / 2):
                        item.setPos(itemPos.x() + 100 + gNode.sizeX / 2, itemPos.y())
                        nodesNeedLayout = True
                        gNode.adjustEdges()
                        item.adjustEdges()
                    elif abs(itemPos.y() - gNodePos.y()) < (gNode.sizeY / 2):
                        item.setPos(itemPos.x(), itemPos.y() + gNode.sizeY / 2 + 100)
                        nodesNeedLayout = True
                        gNode.adjustEdges()
                        item.adjustEdges()
                    else:
                        nodesNeedLayout = False

            iterations += 1

        

        for node in self.graph.sortedNodes:
            gNode = self.getNodeById(node.GetID())

        scene = self.scene
        rect = scene.sceneRect()

        self.scaleView(0.5)

    def contextMenuEvent(self, event: QtGui.QContextMenuEvent) -> None:
        """
        """
        position = event.globalPos()

        menu = QtWidgets.QMenu()

        newNodeMenu = menu.addMenu("Create Node")

        for nodeType in self.nodeLibrary.GetAvailableNodes():
            newNodeAction = QtWidgets.QAction(nodeType, self)
            newNodeAction.setData(nodeType)
            newNodeAction.triggered.connect(lambda: self.addNode(newNodeAction.sender().data(), QtCore.QPointF(self.mapToScene(event.pos()))))
            newNodeMenu.addAction(newNodeAction)

        computeAction = menu.addAction("Cook")
        computeAction.triggered.connect(lambda: self.launchGraphCooking())

        reloadLibAction = menu.addAction("Reload Node Library")
        reloadLibAction.triggered.connect(lambda: self.nodeLibrary.Reload())

        debugAction = menu.addAction("Debug Graph")
        debugAction.triggered.connect(lambda: self.debugGraph())

        menu.setStyleSheet("""
QMenu {
	background-color: rgb(201, 196, 207);
}

QMenu::item {
    color: rgb(72, 69, 79);
    background-color: transparent;
}

QMenu::item:selected {
    color: rgb(72, 69, 79);
    background-color: rgb(205, 200, 211);
}
        """)

        menu.exec_(position)