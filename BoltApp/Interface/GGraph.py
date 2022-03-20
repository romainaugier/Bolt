import json, threading

from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtCore import Qt

from BoltApp.Interface.GNode import *
from BoltApi.Core.Lib import *
from BoltApi.Core.Graph import *
from BoltApi.Core.Logger import *
from BoltApp.Interface.Icons import *
from BoltApp.Interface.PlugEditor import *


class GBlock(QtWidgets.QGraphicsObject):
    """
    Construct a convex hull that will contain all the nodes in the block
    """
    def __init__(self, blockBegin : GNode, blockEnd : GNode, graph : GGraph) -> None:
        """
        """
        self.id = binascii.hexlify(os.urandom(16)).hex()

        super().__init__()

        self.blockBegin = blockBegin
        self.blockEnd = blockEnd
        self.gGraph = graph

        self.offset = 10

        self.nodes = [self.blockBegin, self.blockEnd]

        self.blockId = self.blockBegin.getInternalNode().GetID()

        self.hullPoints : list[QtCore.QPoint] = []

        self.setFlag(QtWidgets.QGraphicsItem.ItemIsFocusable, False)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, False)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, False)
        self.setAcceptHoverEvents(False)
        self.setAcceptedMouseButtons(Qt.MouseButton.NoButton)

        self.blockBegin.hasMoved.connect(self.adjust)
        self.blockEnd.hasMoved.connect(self.adjust)

        self.adjust()

    def getBlockBeginNode(self) -> GNode:
        """
        """
        return self.blockBegin
    
    def getBlockEndNode(self) -> GNode:
        """
        """
        return self.blockEnd

    def addNode(self, node : GNode) -> None:
        """
        """
        self.nodes.append(node)

        node.hasMoved.connect(self.adjust)

        self.adjust()

    def removeNode(self, node : GNode) -> None:
        """
        """
        self.nodes.remove(node)
        
        node.hasMoved.disconnect()
        
        self.adjust()

    def getPoints(self) -> list[QtCore.QPoint]:
        """
        """
        points = []

        for node in self.nodes:
            width = node.sizeX
            height = node.sizeY
            pos = node.pos()

            points.append(QtCore.QPoint(int(pos.x()) - self.offset,
                                        int(pos.y()) - self.offset))
            points.append(QtCore.QPoint(int(pos.x() + width) + self.offset,
                                        int(pos.y()) - self.offset))
            points.append(QtCore.QPoint(int(pos.x() + width) + self.offset,
                                        int(pos.y() + height) + self.offset))
            points.append(QtCore.QPoint(int(pos.x()) - self.offset,
                                        int(pos.y() + height) + self.offset))

        return points

    def getLeftMostPoint(self, points : list[QtCore.QPoint]) -> int:
        """
        """
        xMax = 2 ** 31

        index = 0

        for i, point in enumerate(points):
            if point.x() < xMax:
                xMax = point.x()
                index = i

        return index

    @staticmethod
    def getOrientation(p1 : QtCore.QPoint, p2 : QtCore.QPoint, p3 : QtCore.QPoint) -> int:
        """
        """
        val = (p2.y() - p1.y()) * (p3.x() - p2.x()) - (p2.x() - p1.x()) * (p3.y() - p2.y())

        if val == 0:
            return 0
        elif val > 0:
            return 1
        else:
            return 2

    def updateShape(self):
        """
        """
        self.hullPoints.clear()

        points = self.getPoints()

        n = len(points)

        leftMostIndex = self.getLeftMostPoint(points)

        hull : list[int] = []

        p = leftMostIndex
        q = 0

        maxIters = 50

        iter = 0

        while True:
            if iter > maxIters: 
                break

            hull.append(p)

            q = (p + 1) % n

            for i in range(n):
                if(self.getOrientation(points[p], points[i], points[q]) == 2):
                    q = i

            p = q

            if p == leftMostIndex:
                break

            iter += 1

        for each in hull:
            self.hullPoints.append(points[each])

    def boundingRect(self) -> QtCore.QRectF: 
        return QtCore.QRectF(QtGui.QPolygon(self.hullPoints).boundingRect())

    def adjust(self) -> None:
        self.updateShape()
        # self.setZValue(-100)
        self.update(self.boundingRect())
        self.gGraph.update(self.pos().x(), self.pos().y(), self.pos().x() + self.boundingRect().width(), self.pos().y() + self.boundingRect().height())

    def paint(self, painter : QtGui.QPainter, option : QtWidgets.QStyleOptionGraphicsItem, widget : QtWidgets.QWidget):
        """
        """
        pass

class GraphicsScene(QtWidgets.QGraphicsScene):
    """
    Reimplementation of the graphics scene
    """
    
    hasBeenEdited = QtCore.pyqtSignal()
    
    def __init__(self, parent=None) -> None:
        """
        """
        super(QtWidgets.QGraphicsScene, self).__init__(parent)
        
        self.movingNode = None
        

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
    
    tabIndex = None

    def __init__(self, nodeLib : Lib, logger : Logger, env : Environment, graph : Graph = None) -> None:
        """
        """
        super().__init__()

        self.logger = logger

        self.setScene(GraphicsScene(self))

        self.iconsLib = Icons()
        self.isCookingMovie = self.iconsLib.GetAnim("badge-cooking")

        self.nodeLibrary = nodeLib
        nodeLib.Load()

        if graph is not None:
            self.graph = graph
            self.constructGraphFromInternalGraph()
        else:
            self.graph = Graph(self.logger, env, "New")

        self.gEdges = []

        # Blocks are polygons that encapsulate all the nodes inside 
        # an if/for block
        self.gBlocks : list[GBlock] = []

        # Graphic nodes
        self.gNodes : list[GNode] = []
        
        # When a node is moved around the scene, we try to connect it
        # to the edges it hovers
        self.movingNodeCanConnect = False
        self.movingNodeConnectionSourcePlug = None
        self.movingNodeConnectionDestinationPlug = None
        self.movingNodeConnectionInputPlug = None
        self.movingNodeConnectionOutputPlug = None
        self.movingNodeConnectionEdgeToDelete = None
        
        # When a node is clicked and moved while Alt is pressed, duplicate this node on 
        # mouse release
        self.nodeToDuplicate = None

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.scene().setItemIndexMethod(QtWidgets.QGraphicsScene.NoIndex)
        self.scene().setSceneRect(0, 0, 800, 800)
        self.setScene(self.scene())
        self.setViewportUpdateMode(QtWidgets.QGraphicsView.FullViewportUpdate)
        self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.TextAntialiasing | QtGui.QPainter.SmoothPixmapTransform | QtGui.QPainter.HighQualityAntialiasing)
        self.setContextMenuPolicy(Qt.DefaultContextMenu)

        self.gridSize = 50

        self.scene().gridSize = self.gridSize

        self.startPos = None
        self.pan = False
        self.setMouseTracking(True)

        self.plugEditor = PlugEditor(self.iconsLib)
        self.plugEditor.setParent(self)
        self.plugEditor.move(self.rect().width() - self.plugEditor.getWidth() - 50, 50)

        self.cookThread = None
        self.updateThread = None
        self.updateTimer = None
        self.threadCanJoin.connect(lambda: self.joinGraphThread())

        self.selectedNodeChanged.connect(self.onSelectedNodeChange)
        self.hasBeenEdited.connect(lambda: (self.stopGraphCooking(), self.getInternalGraph().SetAllDirty(), self.updateNodeBadges(), self.updateBlocks()))

        QtWidgets.QApplication.instance().installEventFilter(self)

    # GETTERS / SETTERS

    def getEnv(self) -> Environment:
        """
        Returns the environment of the internal graph
        """
        return self.getInternalGraph().GetEnv()

    def setEnv(self, environment : Environment) -> None:
        """
        Sets the environment of the internal graph
        """
        self.getInternalGraph().SetEnv(environment)
        
    def getTabIndex(self) -> int:
        """
        Returns the graph tab index
        """
        return self.tabIndex
    
    def setTabIndex(self, tabIndex : int) -> None:
        """
        Sets the tab index
        """
        self.tabIndex = tabIndex

    # PAINTING

    def drawBackground(self, painter: QtGui.QPainter, rect: QtCore.QRectF) -> None:
        
        brush = QtGui.QBrush(QtGui.QColor("#292D3E"), Qt.SolidPattern)
        
        painter.fillRect(rect, brush)

        gridColor = QtGui.QColor("#464B5D")
        gridColor.setAlpha(127)

        pen = QtGui.QPen()
        pen.setColor(gridColor)
        pen.setWidth(1)
        painter.setPen(pen)

        left = int(rect.left()) - (int(rect.left()) % self.gridSize)
        top = int(rect.top()) - (int(rect.top()) % self.gridSize)

        gridLines = []

        for x in range(left, int(rect.right()), self.gridSize):
            gridLines.append(QtCore.QLineF(x, rect.top(), x, rect.bottom()))
        
        for y in range(top, int(rect.bottom()), self.gridSize):
            gridLines.append(QtCore.QLineF(rect.left(), y, rect.right(), y))

        painter.drawLines(gridLines)

        for block in self.gBlocks: 
            polygon = QtGui.QPolygon(block.hullPoints)

            painter.setBrush(QtGui.QColor(104, 240, 222, 43))
            painter.setPen(QtGui.QPen(QtGui.QColor(104, 240, 222, 255)))

            painter.drawPolygon(polygon)

    # UTILS
    
    @QtCore.pyqtSlot(str)
    def onNodeSelectionChange(self, nodeId : str) -> None:
        self.selectedNodeChanged.emit(nodeId)

    def showPlugEditor(self) -> None:
        """
        """
        if self.plugEditor.isHidden():
            self.plugEditor.show()
        else:
            self.plugEditor.hide()

    def getAnimationLogoMovie(self) -> QtGui.QPixmap:
        """     
        Returns:
            QtGui.QMovie: movie
        """
        pixmap = self.isCookingMovie.currentPixmap()
        mask = pixmap.createMaskFromColor(QtGui.QColor(0, 0, 0), QtCore.Qt.MaskInColor)
        pixmap.setMask(mask)
        
        return pixmap

    # EVENTS

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        """
        """
        if self.plugEditor.getWidth() > self.rect().width() - 50:
            self.plugEditor.hide()
        else:
            if self.plugEditor.isHidden():
                self.showPlugEditor()
        
        self.plugEditor.move(self.rect().width() - self.plugEditor.getWidth() - 50, 50)
        self.plugEditor.setMaxHeight(self.rect().height() - 225)
        
        return super().resizeEvent(event)

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
            self.plugEditor.setCurrentNode(None)
        elif key == Qt.Key_Space:
            globalPos = QtGui.QCursor.pos()
            scenePos = self.mapToScene(self.mapFromGlobal(globalPos))
            self.contextMenu(globalPos.x(), globalPos.y(), scenePos.x(), scenePos.y())
        
        return super().keyPressEvent(event)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.MiddleButton and self.startPos is None:
            self.setDragMode(QtWidgets.QGraphicsView.NoDrag)
            self.startPos = event.pos()
            self.prevPos = event.pos()
            self.pan = True
            return
        elif event.button() == QtCore.Qt.LeftButton:
            if QtGui.QGuiApplication.keyboardModifiers() & Qt.AltModifier:
                items = self.scene().selectedItems()
                
                if len(items) == 0:
                    items = self.items(event.pos())
                    
                if len(items) != 0:
                    self.nodeToDuplicate = items[0] if type(items[0]) is GNode else None

            else:
                self.setDragMode(QtWidgets.QGraphicsView.RubberBandDrag)
                
            return super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        """
        """
        sceneSelection = self.scene().selectedItems()

        if self.pan:
            delta = self.prevPos - event.pos()

            transform = self.transform()

            deltaX = delta.x() / transform.m11()
            deltaY = delta.y() / transform.m22()

            self.setSceneRect(self.sceneRect().translated(deltaX, deltaY))

            self.prevPos = event.pos()
        
        elif len(sceneSelection) > 0:
            for item in self.scene().selectedItems():
                if isinstance(item, GNode): 
                    item.adjustEdges()
            
        if len(sceneSelection) == 1 and isinstance(sceneSelection[0], GNode):    
            # Handle when a node is passed on an edge and connect it to the two nodes
            scenePos = event.pos()
            
            items = self.items(scenePos.x(), scenePos.y())
            
            self.movingNodeCanConnect = False
            nodeToConnect = sceneSelection[0]

            for item in self.scene().items():
                if isinstance(item, GEdge):
                    item.setHoveredByNode(False)
                
            for item in items:
                if isinstance(item, GEdge):

                    item.setHoveredByNode(True)
                    
                    if nodeToConnect is not None:
                        if nodeToConnect.getInputGPlug(0) is not None:
                            if not nodeToConnect.getInputGPlug(0).IsConnected():
                                self.movingNodeCanConnect = True
                                edge = item
                                
                                self.prepareMovingNodeConnection(edge)
            
        return super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.MiddleButton and self.startPos is not None:
            self.startPos = None
            self.pan = False
        
        elif self.movingNodeCanConnect:
            self.completeMovingNodeConnection()
            return super().mouseReleaseEvent(event)
        
        elif self.nodeToDuplicate is not None:
            pos = self.mapToScene(event.pos().x() - self.nodeToDuplicate.sizeX / 2, event.pos().y() - self.nodeToDuplicate.sizeY / 2)
            self.addNode(self.nodeToDuplicate.getInternalNode().GetNodeType(), pos)
            self.nodeToDuplicate = None
        
        else:
            return super().mouseReleaseEvent(event)

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        if not event.isAccepted():
            inFactor = 1.1
            outFactor = 1.0 / inFactor
            
            oldPos = self.mapToScene(event.pos())
            
            if event.angleDelta().y() > 0:
                zoomFactor = inFactor
            else:
                zoomFactor = outFactor
                
            self.scale(zoomFactor, zoomFactor)
            
            newPos = self.mapToScene(event.pos())
            
            delta = oldPos - newPos
            
            self.setSceneRect(self.sceneRect().translated(delta))
            
            return

        return super().wheelEvent(event)
            
    def scaleView(self, scaleFactor: float) -> None:
        """
        """
        factor = self.transform().scale(scaleFactor, scaleFactor).mapRect(QtCore.QRectF(0, 0, 1, 1)).width()

        if factor < 0.07 or factor > 100:
            return

        self.scale(scaleFactor, scaleFactor)

    def dragEnterEvent(self, event : QtGui.QDragEnterEvent):
        """
        """
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event : QtGui.QDragEnterEvent):
        """
        """
        if event.mimeData().hasUrls():
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event : QtGui.QDragEnterEvent):
        """
        """
        if event.mimeData().hasUrls():
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()

            for url in event.mimeData().urls():
                itemPath = url.toLocalFile()
                
                if os.path.isfile(itemPath):
                    scenePos = self.mapToScene(self.mapFromGlobal(QtGui.QCursor.pos()))
                    tmpGNode = self.addNode("Utility/File", scenePos)
                    scenePos = QtCore.QPointF(scenePos.x() - tmpGNode.sizeX / 2, scenePos.y() - tmpGNode.sizeY / 2)
                    tmpGNode.setPos(scenePos)
                    tmpGNode.getInternalNode().SetPlugValue("infile", itemPath)
        else:
            event.ignore()

    # Menus

    @QtCore.pyqtSlot(list)
    def plugContextMenu(self, data : list) -> None:
        """
        Context menu triggered when clicking on plugs

        Mainly used to disconnect and expose/unexpose plugs
        """
        clickedNode = self.getNodeById(data[0])
        clickedPlug = clickedNode.getInputGPlug(data[1])

    def contextMenu(self, globalX : int, globalY : int, sceneX : int, sceneY : int) -> None:
        """
        """
        position = QtCore.QPoint(globalX, globalY)

        menu = ContextMenu()

        newNodeMenu = menu.addMenu("Create Node")

        nodeCategories = {}

        for node in self.nodeLibrary.GetAvailableNodes():
            nodeCategory, nodeType = node.split("/")

            nodeCategoryMenu = nodeCategories.get(nodeCategory)

            if nodeCategoryMenu is None:
                nodeCategoryMenu = newNodeMenu.addMenu(nodeCategory)
                nodeCategories[nodeCategory] = nodeCategoryMenu

            newNodeAction = QtWidgets.QAction(nodeType, self)
            newNodeAction.setData(node)
            newNodeAction.triggered.connect(lambda: self.addNode(newNodeAction.sender().data(), QtCore.QPointF(float(sceneX), float(sceneY))))
            nodeCategoryMenu.addAction(newNodeAction)

        cookAction = menu.addAction("Cook")
        cookAction.triggered.connect(lambda: self.launchGraphCooking())

        recookAction = menu.addAction("Recook")
        recookAction.triggered.connect(lambda: self.launchGraphCooking(skipCookedNodes=False))

        reloadLibAction = menu.addAction("Reload Node Library")
        reloadLibAction.triggered.connect(lambda: self.nodeLibrary.Reload())

        debugAction = menu.addAction("Debug Graph")
        debugAction.triggered.connect(lambda: self.debugGraph())

        menu.exec_(position)

    def contextMenuEvent(self, event: QtGui.QContextMenuEvent) -> None:
        """
        """
        super().contextMenuEvent(event)

        if not event.isAccepted():
            globalPos = event.globalPos()
            scenePos = self.mapToScene(event.pos())

            self.contextMenu(globalPos.x(), globalPos.y(), scenePos.x(), scenePos.y())

    # BLOCKS

    def updateBlocks(self):
        """
        """
        self.getInternalGraph().FindNodesInIfBlock(silent=True)

        for blockId in self.getInternalGraph().ifBlocks:
            gBlockExists = False

            for gBlock in self.gBlocks: 
                if gBlock.blockId == blockId:
                    gBlockExists = True

            if not gBlockExists:
                blockBeginNode = self.getNodeById(blockId)
                blockEndNode = self.getNodeById(blockBeginNode.getInternalNode().GetAssociatedBlockEnd())

                self.addBlock(blockBeginNode, blockEndNode)

        for blockId, blockNodes in self.getInternalGraph().ifBlocks.items():  
            for gBlock in self.gBlocks:
                if blockId == gBlock.blockId:
                    for blockNode in blockNodes:
                        if not blockNode in gBlock.nodes:
                            gBlock.addNode(self.getNodeById(blockNode))
            
    # NODES FUNCTIONS
    
    def showNodeInfosPanel(self, node : GNode) -> None:
        """_summary_

        Args:
            node (GNode): _description_

        Returns:
            _type_: _description_
        """
        pass
    
    def prepareMovingNodeConnection(self, edge : GEdge) -> None:
        """
        """
        nodeToConnect = self.scene().selectedItems()[0]
        
        self.movingNodeCanConnect = True
        
        self.movingNodeConnectionSourcePlug = edge.getSourcePlug()
        self.movingNodeConnectionDestinationPlug = edge.getDestinationPlug()
        
        self.movingNodeConnectionInputPlug = nodeToConnect.getInputGPlug(index=0)
        self.movingNodeConnectionOutputPlug = nodeToConnect.getOutputGPlug(index=0)
        
        self.movingNodeConnectionEdgeToDelete = edge
            
    def completeMovingNodeConnection(self) -> None:
        """
        """
        self.blockSignals(True)
        
        if self.movingNodeConnectionInputPlug is not None:
            inputEdge = self.addEdge(self.movingNodeConnectionSourcePlug, self.movingNodeConnectionInputPlug)
            
        if self.movingNodeConnectionOutputPlug is not None:
            outputEdge = self.addEdge(self.movingNodeConnectionOutputPlug, self.movingNodeConnectionDestinationPlug)    
        
        self.deleteEdge(self.movingNodeConnectionEdgeToDelete)
        
        # Cleanup
        
        self.movingNodeConnectionSourcePlug = None
        self.movingNodeConnectionDestinationPlug = None
        
        self.movingNodeConnectionInputPlug = None
        self.movingNodeConnectionOutputPlug = None
        
        self.movingNodeConnectionEdgeToDelete = None
        
        self.blockSignals(False)
        
        self.hasBeenEdited.emit()

    # GRAPH FUNCTIONS

    def getInternalGraph(self) -> Graph:
        """
        """
        return self.graph

    def addNode(self, nodeType : str, position : QtCore.QPointF) -> GNode:
        """
        """
        if "If_Block" in nodeType:
            nodesPath = self.nodeLibrary.GetPath(nodeType)
            
            tmpBeginInternalNode = Node(self.getInternalGraph().GetEnv())
            tmpBeginInternalNode.Load(nodesPath[0])
            tmpBeginInternalNode.SetIfBeginBlock()
            
            tmpEndInternalNode = Node(self.getInternalGraph().GetEnv())
            tmpEndInternalNode.Load(nodesPath[1])
            tmpEndInternalNode.SetIfEndBlock()
            
            self.getInternalGraph().AddNode(tmpBeginInternalNode)
            self.getInternalGraph().AddNode(tmpEndInternalNode)
            
            tmpBeginInternalNode.SetAssociatedBlockEnd(tmpEndInternalNode.GetID())
            tmpEndInternalNode.SetAssociatedBlockBegin(tmpBeginInternalNode.GetID())
            
            tmpBeginGNode = GNode(tmpBeginInternalNode, "", self, self.iconsLib)
            tmpBeginGNode.hasBeenSelected.connect(self.onNodeSelectionChange)
            tmpBeginGNode.setPos(position)
            tmpBeginGNode.setZValue(0)
            
            self.scene().addItem(tmpBeginGNode)
            
            tmpEndGNode = GNode(tmpEndInternalNode, "", self, self.iconsLib)
            tmpEndGNode.hasBeenSelected.connect(self.onNodeSelectionChange)
            tmpEndGNode.setPos(position.x() + 400, position.y())
            tmpEndGNode.setZValue(0)

            self.scene().addItem(tmpEndGNode)
            
            self.addEdge(tmpBeginGNode.getOutputGPlug(index=0), tmpEndGNode.getInputGPlug(index=0))

            self.addBlock(tmpBeginGNode, tmpEndGNode)
            
            self.hasBeenEdited.emit()
            
            return tmpBeginGNode
        else:
            tmpInternalNode = self.nodeLibrary.Get(nodeType)
            tmpInternalNode.SetEnv(self.getInternalGraph().GetEnv())
            self.getInternalGraph().AddNode(tmpInternalNode)

            tmpGNode = GNode(tmpInternalNode, "", self, self.iconsLib)
            tmpGNode.hasBeenSelected.connect(self.onNodeSelectionChange)
            tmpGNode.setPos(position)

            tmpGNode.setZValue(0)

            self.scene().addItem(tmpGNode)

            self.hasBeenEdited.emit()

            return tmpGNode

    def addNodeFromInternalGraph(self, node : Node) -> None:
        """
        Adds an existing internal node to the scene

        Args:
            node (Node): internal node
        """
        tmpGNode = GNode(node, "", self, self.iconsLib)
        tmpGNode.setZValue(0)

        tmpGNode.hasBeenSelected.connect(self.onNodeSelectionChange)

        self.scene().addItem(tmpGNode)

    def deleteNode(self, node: GNode) -> None:
        """
        """
        self.blockSignals(True)
        
        for sock in node.inputGPlugs:
            for edge in sock.edges[:]:
                self.deleteEdge(edge)
        
        for sock in node.outputGPlugs:
            for edge in sock.edges[:]:
                self.deleteEdge(edge)
                
        if node.getInternalNode().IsIfBeginBlock():
            node2 = self.getNodeById(node.getInternalNode().GetAssociatedBlockEnd())

            self.deleteBlock(node)

        elif node.getInternalNode().IsIfEndBlock():
            node2 = self.getNodeById(node.getInternalNode().GetAssociatedBlockBegin())
            
            self.deleteBlock(node2)

        else:
            node2 = None
            
        self.getInternalGraph().RemoveNode(node.getInternalNode())
        
        if node2 is not None: 
            for sock in node2.inputGPlugs:
                for edge in sock.edges[:]:
                    self.deleteEdge(edge)
            
            for sock in node2.outputGPlugs:
                for edge in sock.edges[:]:
                    self.deleteEdge(edge)
                    
            self.getInternalGraph().RemoveNode(node2.getInternalNode())
        
        for block in self.gBlocks:
            if node in block.nodes:
                block.nodes.remove(node)
                break

        if node2 is not None:
            for block in self.gBlocks:
                if node2 in block.nodes:
                    block.nodes.remove(node2)
                    break

        self.scene().removeItem(node)
        
        if node2 is not None: self.scene().removeItem(node2)

        self.blockSignals(False)

        self.hasBeenEdited.emit()

    @QtCore.pyqtSlot(str)
    def onSelectedNodeChange(self, nodeId : str) -> None:
        """
        """
        gNode = self.getNodeById(nodeId)

        self.plugEditor.setCurrentNode(gNode)

    def getNodeById(self, nodeId : str) -> GNode:
        """
        """
        for item in self.scene().items():
            if type(item) is GNode:
                if item.id == nodeId:
                    return item

    def addEdge(self, outputGPlug: GPlug, inputGPlug: GPlug, connectInternally : bool = True) -> GEdge:
        """
        """
        if connectInternally: 
            outputGPlug.getInternalPlug().Connect(inputGPlug.getInternalPlug())

        outputNodeName = outputGPlug.getInternalPlug().GetNode().GetName()
        outputPlugName = outputGPlug.getInternalPlug().GetShortName()
        inputNodeName = inputGPlug.getInternalPlug().GetNode().GetName()
        inputPlugName = inputGPlug.getInternalPlug().GetShortName()

        self.logger.Log(LogLevel.DIAGNOSTIC, f"""New Connection : [{outputNodeName}] {outputPlugName} -> {inputPlugName} [{inputNodeName}] """)

        newEdge = GEdge(outputGPlug, inputGPlug)

        self.scene().addItem(newEdge)

        self.hasBeenEdited.emit()
        
        return newEdge

    def deleteEdge(self, edge: GEdge) -> None:
        """
        """
        edge.source.getInternalPlug().Disconnect(edge.destination.getInternalPlug())

        edge.source.edges.remove(edge)
        edge.destination.edges.remove(edge)

        self.scene().removeItem(edge)

        self.hasBeenEdited.emit()

    def updateAllEdges(self) -> None:
        """
        """
        for item in self.items():
            if type(item) is GEdge:
                item.adjust()

    def addBlock(self, beginBlockNode : GNode, endBlockNode : GNode) -> None:
        """
        """
        newBlock = GBlock(beginBlockNode, endBlockNode, self)
        newBlock.setZValue(-100)

        self.gBlocks.append(newBlock)

        self.scene().addItem(newBlock)

    def deleteBlock(self, anyBlockNode : GNode) -> None:
        """
        """
        blockToDelete = None

        for block in self.gBlocks:
            if (block.getBlockBeginNode() == anyBlockNode or
                block.getBlockEndNode() == anyBlockNode):
                blockToDelete = block

        if blockToDelete is not None:
            self.getInternalGraph().ifBlocks.pop(blockToDelete.blockId)

            self.gBlocks.remove(blockToDelete)

            self.scene().removeItem(blockToDelete)

    def deleteItem(self, item=None) -> None:
        """
        """
        if item is not None:
            if type(item) is GNode:
                self.deleteNode(item)
            elif type(item) is GPlug:
                node = item.node
                self.deleteNode(node)
            elif type(item) is GEdge:
                self.deleteEdge(item)
        
        else:
            items = self.scene().selectedItems()

            if len(items) > 0: 
                # Remove edges first
                for item in items:
                    if type(item) is GEdge:
                        self.deleteEdge(item)
                
                for item in items:
                    if type(item) is GNode:
                        self.deleteNode(item)        

    def cookGraph(self, lastNodeToCook : str = None, skipCookedNodes : bool = True) -> None:
        """
        Cooks the graph
        """
        self.startCooking.emit()
        self.getInternalGraph().Cook(lastNodeToCook, skipCookedNodes)
        self.threadCanJoin.emit()
        
    def stopGraphCooking(self) -> None:
        """
        """
        self.getInternalGraph().StopCook()

    def updateNodeBadges(self) -> None:
        """
        """
        for item in self.items():
            if type(item) is GNode:
                item.updateBadge()

    def launchGraphCooking(self, lastNodeToCook : str = None, skipCookedNodes : bool = True) -> None:
        """
        Launches the thread that cooks the graph
        """
        self.isCookingMovie.start()

        self.cookThread = threading.Thread(target=self.cookGraph, args=(lastNodeToCook, skipCookedNodes, ))
        self.cookThread.start()

        self.updateTimer = QtCore.QTimer(self, interval=20, timeout=self.updateNodeBadges)
        self.updateTimer.start()

    def joinGraphThread(self) -> None:
        """
        Joins the thread that cooks the graph
        """
        if self.cookThread is not None:
            self.cookThread.join()
            self.updateTimer.stop()
            self.isCookingMovie.stop()

            self.finishedCooking.emit()

            if self.getInternalGraph().hasError:
                self.errorCooking.emit()

        self.updateNodeBadges()

    def debugGraph(self) -> None:
        """
        """
        print("Nodes : ")
        print(json.dumps([node.GetName() for node in self.getInternalGraph().nodes], indent=4))
        
        self.getInternalGraph().Sort()

        print("Sorted Nodes : ")
        print(json.dumps([node.GetName() for node in self.getInternalGraph().sortedNodes], indent=4))
        
        print("Found If Blocks : ")
        for blockName, nodes in self.getInternalGraph().ifBlocks.items():
            blockBegin = self.getInternalGraph().GetNodeWithID(blockName)
            print(f"Block Begin [{blockBegin.GetName()}]")
            
            for node in nodes:
                print(f"- {self.getInternalGraph().GetNodeWithID(node).GetName()}")
                
            blockEnd = self.getInternalGraph().GetNodeWithID(blockBegin.GetAssociatedBlockEnd())
            print(f"Block End [{blockEnd.GetName()}]")

    def saveGraph(self, filePath : str) -> None:
        """
        Saves a graph to a .bgraph file, and adds the positions of each node

        Args:
            filePath (str): path to save the file
        """
        name, _ = os.path.splitext(os.path.basename(filePath))
        
        self.getInternalGraph().SetName(name)
        self.getInternalGraph().SetSavePath(filePath)

        graphSerialized = self.getInternalGraph().Serialize()

        graphDict = json.loads(graphSerialized)

        graphDict["positions"] = []

        for item in self.items():
            if type(item) is GNode:
                nodeId = item.id
                nodePosition = item.pos()

                graphDict["positions"].append({ "id" : nodeId, "x" : nodePosition.x(), "y" : nodePosition.y() })

        graphSerialized = json.dumps(graphDict, indent=2)

        with open(filePath, "w") as file:
            file.write(graphSerialized)

    def loadGraph(self, filePath : str) -> None:
        """
        Loads a graph from a .bgraph file and position the items

        Args:
            filePath (str): path to the graph file
        """
        self.getInternalGraph().LoadFromFile(filePath)

        self.constructGraphFromInternalGraph()

        with open(filePath, "r") as file:
            graphData = json.load(file)

        if "positions" in graphData:
            for nodePos in graphData["positions"]:
                id = nodePos["id"]
                x = nodePos["x"]
                y = nodePos["y"]

                gNode = self.getNodeById(id)
                gNode.setPos(x, y)

        self.updateAllEdges()
        self.updateNodeBadges()
        self.updateBlocks()
        # self.hasBeenEdited.emit()

    def constructGraphFromInternalGraph(self) -> None:
        """
        Constructs the scene from a graph
        """
        self.blockSignals(True)

        for item in self.scene().items():
            if type(item) is GNode:
                self.deleteNode(item)
            elif type(item) is GPlug:
                node = item.node
                self.deleteNode(node)
            elif type(item) is GEdge:
                self.deleteEdge(item)

        for node in self.getInternalGraph().GetNodes():
            self.addNodeFromInternalGraph(node)

        for node in self.getInternalGraph().GetNodes():
            gNode = self.getNodeById(node.GetID())

            for outputName, output in node.GetOutputs().items():
                if output.IsConnected():

                    for connection in output.GetConnections():
                        connectedGNode =  self.getNodeById(connection.GetNode().GetID())
                        self.addEdge(gNode.getOutputGPlug(outputName), connectedGNode.getInputGPlug(connection.GetShortName()), False)

        self.blockSignals(False)

    def layoutGraph(self) -> None:
        """
        """
        self.getInternalGraph().Sort()
        
        if not self.getInternalGraph().HasError():
            nodesNeedLayout = True

            iterations = 0

            while nodesNeedLayout == True:
            # while iterations < 2:
                for i, node in enumerate(self.getInternalGraph().sortedNodes):
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
                            gNode.setPos(newPos.x() - 50 - pluggedNode.sizeX, newPos.y())
                            gNode.adjustEdges()

                    for item in self.scene().items():
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

            

            for node in self.getInternalGraph().sortedNodes:
                gNode = self.getNodeById(node.GetID())

            scene = self.scene()
            rect = scene.sceneRect()

            self.scaleView(0.5)
