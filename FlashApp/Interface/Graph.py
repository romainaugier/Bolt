import json, threading

from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtCore import Qt

from FlashApp.Interface.Node import *
from FlashApi.Core.Lib import *
from FlashApi.Core.Graph import *

class GGraph(QtWidgets.QGraphicsView):
    """
    Graphics view of the current graph
    """
    def __init__(self, nodeLib : Lib, graph : Graph = None) -> None:
        """
        """
        super().__init__()

        self.scene = QtWidgets.QGraphicsScene(self) 

        self.nodeLibrary = nodeLib
        nodeLib.Load()

        if graph is not None:
            self.graph = graph
        else:
            self.graph = Graph()

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
        self.setRenderHint(QtGui.QPainter.Antialiasing)
        self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QtWidgets.QGraphicsView.AnchorViewCenter)
        self.setContextMenuPolicy(Qt.DefaultContextMenu)

        self.setMinimumSize(800, 800)

        self.startPos = None

        QtWidgets.QApplication.instance().installEventFilter(self)

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

    def eventFilter(self, obj: QtCore.QObject, ev: QtCore.QEvent) -> bool:
        if ev.type() == QtCore.QEvent.Wheel:
            if ev.angleDelta().y() > 0:
                self.scaleView(1.01)
            else:
                self.scaleView(0.99)

        elif ev.type() == QtCore.QEvent.MouseButtonPress and ev.button() == QtCore.Qt.MiddleButton:
            self.startPos = ev.pos()
            
        elif ev.type() == QtCore.QEvent.MouseMove and self.startPos is not None:
            delta = self.startPos - ev.pos()

            transform = self.transform()

            deltaX = delta.x() / transform.m11()
            deltaY = delta.y() / transform.m22()

            self.setSceneRect(self.sceneRect().translated(deltaX, deltaY))

            self.startPos = ev.pos()
            
        elif ev.type() == QtCore.QEvent.MouseButtonRelease:
            self.startPos = None

        elif ev.type() == QtCore.QEvent.MouseButtonPress and ev.button() == QtCore.Qt.LeftButton:
            self.scene.clearSelection()
            self.scene.selectedItems()
            
        return super().eventFilter(obj, ev)

    def scaleView(self, scaleFactor: int) -> None:
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

        tmpGNode = GNode(tmpInternalNode, "", self)
        tmpGNode.setPos(position)

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

    def addEdge(self, outputGPlug: GPlug, inputGPlug: GPlug) -> None:
        """
        """
        outputGPlug.getInternalPlug().Connect(inputGPlug.getInternalPlug())

        newEdge = Edge(outputGPlug, inputGPlug)

        self.scene.addItem(newEdge)

    def deleteEdge(self, edge: Edge) -> None:
        """
        """
        edge.source.internalPlug.Disconnect()

        edge.source.edges.remove(edge)
        edge.destination.edges.remove(edge)

        self.scene.removeItem(edge)

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
        Launch the thread that cooks the graph
        """
        self.cookThread = threading.Thread(target=self.graph.Cook())
        self.cookThread.start()

    def debugGraph(self) -> None:
        """
        """
        print("Nodes : ")
        print(json.dumps([node.GetName() for node in self.graph.nodes], indent=4))
        
        self.graph.Sort()

        print("Sorted Nodes : ")
        print(json.dumps([node.GetName() for node in self.graph.sortedNodes], indent=4))

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
        computeAction.triggered.connect(lambda: self.cookGraph())

        reloadLibAction = menu.addAction("Reload Node Library")
        reloadLibAction.triggered.connect(lambda: self.nodeLibrary.Reload())

        debugAction = menu.addAction("Debug Graph")
        debugAction.triggered.connect(lambda: self.debugGraph())

        menu.exec_(position)