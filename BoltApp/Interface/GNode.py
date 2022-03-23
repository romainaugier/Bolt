import binascii, os, math, time

from enum import Enum

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt

from BoltApi.Core.Node import *
from BoltApi.Core.Graph import *
from BoltApp.Interface.Icons import *
from BoltApp.Interface.Style import ColorPalette, GetQColorFromPalette
from BoltApp.Interface.Widgets import *

class GNode():
    pass

class GEdge():
    pass

class GGraph():
    pass


def GetPlugColor(plugType : PlugType) -> QtGui.QColor:
    """
    Plug types available
    """
    if plugType == PlugType.INT: return GetQColorFromPalette(ColorPalette.BLUECOLOR)
    elif plugType == PlugType.INT2: return GetQColorFromPalette(ColorPalette.BLUECOLOR)
    elif plugType == PlugType.INT3: return GetQColorFromPalette(ColorPalette.BLUECOLOR)
    elif plugType == PlugType.FLOAT: return GetQColorFromPalette(ColorPalette.CYANCOLOR)
    elif plugType == PlugType.FLOAT2: return GetQColorFromPalette(ColorPalette.CYANCOLOR)
    elif plugType == PlugType.FLOAT3: return GetQColorFromPalette(ColorPalette.CYANCOLOR)
    elif plugType == PlugType.STR: return GetQColorFromPalette(ColorPalette.GREENCOLOR)
    elif plugType == PlugType.BOOL: return GetQColorFromPalette(ColorPalette.WHITECOLOR)
    elif plugType == PlugType.LIST: return GetQColorFromPalette(ColorPalette.ORANGECOLOR)
    elif plugType == PlugType.DICT: return GetQColorFromPalette(ColorPalette.PURPLECOLOR)
    elif plugType == PlugType.CUSTOM: return GetQColorFromPalette(ColorPalette.REDCOLOR)


def GetFontRect(text : str, font : str, size : int) -> QtCore.QRect:
    """
    Gets size of a text

    Args:
        text (str): text

    Returns:
        QtCore.QRect: bounding box of the text
    """
    metric = QtGui.QFontMetrics(QtGui.QFont(font, size))
    return metric.boundingRect(text)


class BadgeState(Enum):
    """
    """
    DIRTY = 0
    COOKED = 1
    COOKING = 2
    WARNING = 3
    ERROR = 4


class Badge(QtWidgets.QGraphicsObject):
    """
    Information badge that displays the cooking state of a node (cook, warning, error)
    """

    startsCooking = QtCore.pyqtSignal(str)
    stopsCooking = QtCore.pyqtSignal(str)

    def __init__(self, x : int, y : int, node : Node, iconsLib : Icons, parent = None) -> None:
        """
        """
        super().__init__(parent=parent)

        self.id = binascii.hexlify(os.urandom(16)).hex()

        self.size = 18

        self.node = node
        self.iconsLib = iconsLib
        self.state = BadgeState.DIRTY
        self.message = ""

        self.dirtyPixmap = self.iconsLib.GetPixmap("clock")
        self.cookedPixmap = self.iconsLib.GetPixmap("done")
        self.warningPixmap = self.iconsLib.GetPixmap("warning")
        self.errorPixmap = self.iconsLib.GetPixmap("error")

        # self.cookingMovie = self.iconsLib.GetAnim("badge-cooking")
        self.cookingMovie = QtGui.QMovie(f"{BOLTROOT}/Library/Icons/badge-cooking.gif")

        self.setPos(x - self.size, y)

        self.isHovered = False
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, False)
        self.setCacheMode(QtWidgets.QGraphicsItem.DeviceCoordinateCache)
        self.setZValue(2)
        self.setAcceptHoverEvents(True)

    def updateState(self) -> None:
        """
        """
        with self.node.GetLock():
            if self.node.IsCooking():
                self.state = BadgeState.COOKING
                self.message = ""
                if self.cookingMovie.state() == QtGui.QMovie.NotRunning:
                    self.startsCooking.emit(self.node.GetID())
            
            elif self.node.HasError():
                self.state = BadgeState.ERROR
                self.message = self.node.GetErrorMessage()
                if self.cookingMovie.state() == QtGui.QMovie.Running:
                    self.stopsCooking.emit(self.node.GetID())

            elif self.node.HasWarning():
                self.state = BadgeState.WARNING
                self.message = self.node.GetWarningMessage()
                if self.cookingMovie.state() == QtGui.QMovie.Running:
                    self.stopsCooking.emit(self.node.GetID())


            elif self.node.IsDirty():
                self.state = BadgeState.DIRTY
                self.message = ""
                if self.cookingMovie.state() == QtGui.QMovie.Running:
                    self.stopsCooking.emit(self.node.GetID())
                
            elif self.node.IsCooked():
                self.state = BadgeState.COOKED
                self.message = ""
                if self.cookingMovie.state() == QtGui.QMovie.Running:
                    self.stopsCooking.emit(self.node.GetID())

        self.update(self.boundingRect().left(), self.boundingRect().top(), self.boundingRect().width(), self.boundingRect().height())

    def startMovie(self) -> None:
        """
        """
        self.cookingMovie.start()

    def stopMovie(self) -> None:
        """
        """
        self.cookingMovie.stop()

    def boundingRect(self) -> QtCore.QRectF:
        return QtCore.QRectF(0, 0, self.size, self.size)

    def paint(self, painter : QtGui.QPainter, option : QtWidgets.QStyleOptionGraphicsItem, widget : QtWidgets.QWidget) -> None:
        """
        """
        painter.setRenderHints(QtGui.QPainter.Antialiasing | 
                               QtGui.QPainter.LosslessImageRendering |
                               QtGui.QPainter.TextAntialiasing | 
                               QtGui.QPainter.SmoothPixmapTransform | 
                               QtGui.QPainter.HighQualityAntialiasing)
        
        alpha = 1.0
        
        if self.node.IsDisabled():
            alpha = 0.3

        if self.state == BadgeState.ERROR:
            painter.drawPixmap(0, 0, self.size, self.size, self.errorPixmap)
        elif self.state == BadgeState.WARNING:
            painter.drawPixmap(0, 0, self.size, self.size, self.warningPixmap)
        elif self.state == BadgeState.DIRTY:
            painter.drawPixmap(0, 0, self.size, self.size, self.dirtyPixmap)
        elif self.state == BadgeState.COOKED:
            painter.drawPixmap(0, 0, self.size, self.size, self.cookedPixmap)
        elif self.state == BadgeState.COOKING:
            pixmap = self.cookingMovie.currentPixmap()
            mask = pixmap.createMaskFromColor(QtGui.QColor(0, 0, 0), QtCore.Qt.MaskInColor) 
            pixmap.setMask(mask)
            painter.setOpacity(alpha)
            painter.drawPixmap(0, 0, self.size, self.size, pixmap)

class GPlug(QtWidgets.QGraphicsObject):
    """
    Graphical representation of a plug
    """

    hasBeenRightClicked = QtCore.pyqtSignal(list)

    def __init__(self, x: int, y: int, plug : Plug, node: Node, graph : GGraph, input=True, parent=None):
        super().__init__(parent=parent)

        self.id = binascii.hexlify(os.urandom(16)).hex()

        self.internalPlug : Plug = plug
        self.node  : Node = node
        self.graph : GGraph = graph
        self.closestGPlug = None
        self.isInput = input

        self.color = GetPlugColor(self.getInternalPlug().GetType())

        if self.getInternalPlug().IsExposed():
            self.color.setAlpha(62)
            self.setAcceptTouchEvents(False)

        self.edges = []

        self.radius = 15

        malus = 0

        if not input:
            malus = self.radius / 2.0

        self.labelRect = GetFontRect(self.getInternalPlug().GetShortName(), "Helvetica", 8)

        self.textWOffset = 5

        if not self.isInput:
            outputOffset = self.labelRect.width() + self.textWOffset
        else:
            outputOffset = 0

        self._x = x - malus - outputOffset
        self._y = y - (self.radius / 2.0)

        self.setPos(self._x, self._y)

        self.isHovered = False
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, True)
        self.setCacheMode(QtWidgets.QGraphicsItem.DeviceCoordinateCache)
        self.setZValue(1)
        self.setAcceptHoverEvents(True)

    def getInternalPlug(self) -> Plug:
        """
        Returns:
            Plug: attached internal plug
        """
        return self.internalPlug

    def boundingRect(self):
        if self.isInput:
            return QtCore.QRectF(0, 0, self.radius + self.labelRect.width() + self.textWOffset, self.radius)
        else:
            return QtCore.QRectF(0, 0, self.radius + self.labelRect.width() + self.textWOffset, self.radius)

    def paint(self, painter : QtGui.QPainter, option : QtWidgets.QStyleOptionGraphicsItem, widget : QtWidgets.QWidget) -> None:
        """
        """
        painter.setRenderHints(QtGui.QPainter.Antialiasing | 
                               QtGui.QPainter.LosslessImageRendering |
                               QtGui.QPainter.TextAntialiasing | 
                               QtGui.QPainter.SmoothPixmapTransform | 
                               QtGui.QPainter.HighQualityAntialiasing)

        pen = QtGui.QPen()
        pen.setBrush(Qt.black)
        pen.setWidth(0.01)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)

        painter.setPen(Qt.NoPen)
        
        color = QtGui.QColor(self.color)
        
        if self.getInternalPlug().GetParentNode().IsDisabled():
            color.setAlpha(78)

        painter.setBrush(color)

        if self.isInput:
            painter.drawEllipse(0, 0, self.radius, self.radius)

            painter.setPen(color)
            painter.setFont(QtGui.QFont("Helvetica", 8))

            fontRect = QtCore.QRect(self.radius + self.textWOffset, 0, self.labelRect.width(), self.radius)
            painter.drawText(fontRect, 0, self.getInternalPlug().GetShortName())
        else:
            painter.drawEllipse(self.labelRect.width() + self.textWOffset, 0, self.radius, self.radius)

            painter.setPen(color)
            painter.setFont(QtGui.QFont("Helvetica", 8))

            fontRect = QtCore.QRect(0, 0, self.labelRect.width() + self.textWOffset, self.radius)
            painter.drawText(fontRect, 0, self.getInternalPlug().GetShortName())

    # EVENTS

    def hoverEnterEvent(self, ev) -> None:
        """
        """
        self.isHovered = True
        self.update()
        
        return super().hoverEnterEvent(ev)
    
    def hoverLeaveEvent(self, ev) -> None:
        """
        """
        self.isHovered = False
        self.update()
        
        return super().hoverLeaveEvent(ev)

    def mousePressEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        if event.buttons() & QtCore.Qt.RightButton:
            self.hasBeenRightClicked.emit([self.node.getInternalNode().GetID(), self.getInternalPlug().GetShortName()])
        
        return super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event) -> None:
        x = event.scenePos().x()
        y = event.scenePos().y()

        dist = 2 ** 30
        closestGPlug = None

        for item in self.graph.items():
            if item.id == self.id or type(item) is not GPlug or item.node.id == self.node.id:
                continue

            itemPos = item.scenePos()

            distTmp = math.sqrt(math.pow(itemPos.x() - x, 2) + pow(itemPos.y() - y, 2))

            if distTmp < dist and distTmp < 15: 
                dist = distTmp
                closestGPlug = item

        self.closestGPlug = closestGPlug

        return super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event : 'QGraphicsSceneMouseEvent') -> None:
        if self.closestGPlug is not None and not self.closestGPlug.id == self.id:
            condition1 = True

            if self.isInput and self.closestGPlug.isInput:
                condition1 = False

            condition2 = True

            if not self.isInput and not self.closestGPlug.isInput:
                condition2 = False
            
            condition3 = True

            for edge in self.edges:
                if edge.destination.id == self.closestGPlug.id:
                    condition3 = False
                    break

            condition4 = True

            if self.closestGPlug.getInternalPlug().IsExposed():
                condition4 = False

            if condition1 and condition2 and condition3 and condition4:
                if self.closestGPlug.getInternalPlug().IsConnected():
                    for edge in self.closestGPlug.edges:
                        self.graph.deleteEdge(edge)

                self.graph.addEdge(self, self.closestGPlug)
        
        return super().mouseMoveEvent(event)

    def contextMenuEvent(self, event: QtGui.QContextMenuEvent) -> None:
        """
        """
        super().contextMenuEvent(event)

        position = event.screenPos()

        menu = ContextMenu()

        if self.getInternalPlug().IsConnected():
            disconnectAction = menu.addAction("Disconnect")
            disconnectAction.triggered.connect(lambda: self.deleteEdges())

        if self.isInput:
            if self.getInternalPlug().IsExposed():
                unexposeAction = QtWidgets.QAction("Unexpose")
                unexposeAction.triggered.connect(self.unexpose)
                menu.addAction(unexposeAction)
            else:
                unexposeAction = QtWidgets.QAction("Expose")
                unexposeAction.triggered.connect(self.expose)
                menu.addAction(unexposeAction)
            
            if self.getInternalPlug().IsExposedToGraph():
                unexposeToGraphAction = QtWidgets.QAction("Unexpose To Graph")
                unexposeToGraphAction.triggered.connect(self.unexposeToGraph)
                menu.addAction(unexposeToGraphAction)
            else:
                unexposeToGraphAction = QtWidgets.QAction("Expose To Graph")
                unexposeToGraphAction.triggered.connect(self.exposeToGraph)
                menu.addAction(unexposeToGraphAction)

        menu.exec(QtCore.QPoint(position.x(), position.y()))

        event.setAccepted(True)

    # MISC      

    def expose(self) -> None:
        """
        """
        self.getInternalPlug().SetExposed(True)
        self.color.setAlpha(62)
        self.setAcceptTouchEvents(False)
        self.update(self.boundingRect())

    def exposeToGraph(self) -> None:
        """
        """
        self.getInternalPlug().SetExposedToGraph()
        self.expose()
        
    def unexpose(self) -> None:
        """
        """
        self.getInternalPlug().SetExposed(False)
        self.color.setAlpha(255)
        self.setAcceptTouchEvents(True)
        self.update(self.boundingRect())

    def unexposeToGraph(self) -> None:
        """
        """
        self.getInternalPlug().SetExposedToGraph(False)

    def addEdge(self, edge : GEdge) -> None:
        """
        """
        self.edges.append(edge)

    def deleteEdges(self) -> None:
        """
        """
        for edge in self.edges:
            self.graph.deleteItem(edge)


class GNode(QtWidgets.QGraphicsObject):
    """
    GNode holds the representation of a node in the qgraphicsview
    """

    hasBeenSelected = QtCore.pyqtSignal(str)
    plugHasBeenClicked = QtCore.pyqtSignal(list)
    hasMoved = QtCore.pyqtSignal()
    openSubGraph = QtCore.pyqtSignal(Graph)

    def __init__(self, node : Node, name : str, graph : GGraph, iconsLib : Icons):
        """
        GNode constructor
        Sets up the dependent objects (badge and plugs)
        """
        super().__init__()
        
        self.internalNode = node
        self.graph = graph
        self.iconsLib = iconsLib

        self.name = self.getInternalNode().GetName()
        self.id = self.getInternalNode().GetID()
        self.iconPath = self.getInternalNode().GetIconPath()

        if self.iconPath != "":
            pixname = self.iconsLib.AddPixmap(self.iconPath)
            self.pixMap = self.iconsLib.GetPixmap(pixname)
        else:
            self.pixMap = None

        self.newPos = QtCore.QPointF()
        self.iconSize = 18

        labelSizeX = GetFontRect(self.name, "Helvetica", 14).width() * 1.5 + 3 * self.iconSize
        inputNameSizeX = 0
        outputNameSizeX = 0

        for inputName in self.getInternalNode().GetInputs():
            size = GetFontRect(inputName, "Helvetica", 8).width() + 15 + 5
            inputNameSizeX = size if size > inputNameSizeX else inputNameSizeX
        
        for outputName in self.getInternalNode().GetOutputs():
            size = GetFontRect(outputName, "Helvetica", 8).width() + 15 + 5
            outputNameSizeX = size if size > outputNameSizeX else outputNameSizeX

        plugsSize = inputNameSizeX + outputNameSizeX + 30

        self.sizeX = labelSizeX if labelSizeX > plugsSize else plugsSize
        self.sizeY = 125
        self.labelSizeY = 30

        self.inputGPlugs : list[GPlug] = []
        self.outputGPlugs : list[GPlug] = []

        numInputs = self.getInternalNode().GetInputCount()
        numOutputs = self.getInternalNode().GetOutputCount()

        maxNumPlugs = numInputs if numInputs > numOutputs else numOutputs
        
        bodySizeYPerPlug = (self.sizeY - self.labelSizeY) / 3 

        bodySizeY = bodySizeYPerPlug * (maxNumPlugs + 2)
        
        if bodySizeY > self.sizeY:
            self.sizeY = bodySizeY 
        else:
            bodySizeYPerPlug = (self.sizeY - self.labelSizeY) / 3
            self.sizeY = bodySizeYPerPlug * 3

        i = 1

        for inputName, input in self.getInternalNode().GetInputs().items():
            positionX = self.pos().x() + 5
            positionY = self.pos().y() + self.labelSizeY + (bodySizeYPerPlug * i)
            
            newGPlug = GPlug(positionX, positionY, input, self, self.graph, parent=self)
            newGPlug.hasBeenRightClicked.connect(self.onPlugClicked)
            self.inputGPlugs.append(newGPlug)

            i += 1

        i = 1
        
        for outputName, output in self.getInternalNode().GetOutputs().items():
            positionX = self.pos().x() + self.sizeX - 12.5
            positionY = self.pos().y() + self.labelSizeY + (bodySizeYPerPlug * i)
            
            newGPlug = GPlug(positionX, positionY, output, self, self.graph, input=False, parent=self)
            newGPlug.hasBeenRightClicked.connect(self.onPlugClicked)
            self.outputGPlugs.append(newGPlug)

            i += 1

        self.numInputs = numInputs
        self.numOuputs = numOutputs
        self.color = QtGui.QColor(self.internalNode.GetColor()[0], self.internalNode.GetColor()[1], self.internalNode.GetColor()[2])

        self.badge = Badge(self.pos().x() + self.sizeX - 7, self.pos().y() + 7, self.getInternalNode(), self.iconsLib, parent=self)

        self.badge.startsCooking.connect(lambda: (self.badge.startMovie()))
        self.badge.stopsCooking.connect(lambda: (self.badge.stopMovie()))

        self.canMove = True
        self.isHovered = False
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsFocusable, True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setCacheMode(QtWidgets.QGraphicsItem.DeviceCoordinateCache)
        self.setZValue(1)
        self.setAcceptHoverEvents(True)
        
        self.setToolTip(f"{self.getInternalNode().GetName()}")

    # NODE UTILS

    def getInternalNode(self) -> Node:
        """
        Returns:
            Node: internal node
        """
        return self.internalNode
    
    def reloadNode(self) -> None:
        """
        """
        definitionPath = self.getInternalNode().GetDefinitionPath()
        
        self.getInternalNode().Load(definitionPath)
        
        self = GNode(self.getInternalNode(), self.getInternalNode().GetName(), self.graph, self.iconsLib)
        
        QtCore.QTimer.singleShot(10, self.updateAfterReload)
        
    def updateAfterReload(self) -> None:
        """
        """
        self.update(self.boundingRect())

    def getInputGPlugs(self):
        """
        """
        return self.inputGPlugs

    def getOutputGPlugs(self):
        """
        """
        return self.outputGPlugs

    def getInputGPlug(self, name : str = None, index : int = None) -> GPlug:
        """
        """
        if name is not None:
            for gplug in self.inputGPlugs:
                if gplug.getInternalPlug().GetShortName() == name:
                    return gplug

        if index is not None:
            return list(self.inputGPlugs)[index]

        return None
    
    def getOutputGPlug(self, name : str = None, index : int = None) -> GPlug:
        """
        """
        if name is not None:
            for gplug in self.outputGPlugs:
                if gplug.getInternalPlug().GetShortName() == name:
                    return gplug

        if index is not None:
            return list(self.outputGPlugs)[index]
        
        return None

    def updateBadge(self) -> None:
        """
        """
        self.badge.updateState()

    def getPixmap(self) -> QtGui.QPixmap:
        """
        """
        return self.pixMap

    def boundingRect(self):
        """
        """
        adjust = 10
        return QtCore.QRectF(-adjust, -adjust, self.sizeX + adjust * 2, self.sizeY + adjust * 2)
    
    def cook(self) -> None:
        """
        """
        if self.getInternalNode().IsCooked():
            self.graph.launchGraphCooking(lastNodeToCook=self.getInternalNode().GetID(), skipCookedNodes=False)
        else:
            self.graph.launchGraphCooking(lastNodeToCook=self.getInternalNode().GetID())

    # PAINT

    def paint(self, painter : QtGui.QPainter, option : QtWidgets.QStyleOptionGraphicsItem, widget : QtWidgets.QWidget) -> None:
        """
        """
        painter.setRenderHints(QtGui.QPainter.LosslessImageRendering |
                               QtGui.QPainter.TextAntialiasing | 
                               QtGui.QPainter.SmoothPixmapTransform | 
                               QtGui.QPainter.HighQualityAntialiasing)

        ## Shadow
        shadowOffset = 10
        path = QtGui.QPainterPath()
        path.setFillRule(Qt.WindingFill)
        path.addRoundedRect(QtCore.QRectF(shadowOffset, shadowOffset, self.sizeX, self.sizeY), 10, 10)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QtGui.QColor(0, 0, 0, 60))
        painter.drawPath(path.simplified())
        
        ## Body
        
        labelColor = GetQColorFromPalette(ColorPalette.NODELABELCOLOR)
        bodyColor = GetQColorFromPalette(ColorPalette.NODEBODYCOLOR)
        
        nodeType = self.getInternalNode().GetNodeType()
        
        if "SubGraph" in nodeType:
            labelColor = GetQColorFromPalette(ColorPalette.SUBGRAPHLABELCOLOR)
        elif "IfBlock" in nodeType:
            labelColor = GetQColorFromPalette(ColorPalette.IFBLOCKLABELCOLOR)
        elif "ForBlock" in nodeType:
            labelColor = GetQColorFromPalette(ColorPalette.FORBLOCKLABELCOLOR)
            
        # Label
        path = QtGui.QPainterPath()
        path.setFillRule(Qt.WindingFill)
        path.addRoundedRect(QtCore.QRectF(0, 0, self.sizeX, self.labelSizeY), 10, 10)
        path.addRect(0, self.labelSizeY / 2, self.sizeX, self.labelSizeY / 2)

        painter.setBrush(labelColor)
        painter.setPen(Qt.NoPen)
        painter.drawPath(path.simplified())

        # Icon (if has any)
        pixMapWidth = 0

        if self.pixMap is not None:
            pixMapWidth = self.iconSize
            pixmap = self.pixMap.scaled(24, 24, QtCore.Qt.IgnoreAspectRatio, QtCore.Qt.SmoothTransformation)
            painter.drawPixmap(7, 7, pixMapWidth, pixMapWidth, pixmap)

        # Label name
        painter.setPen(GetQColorFromPalette(ColorPalette.SELECTIONFOREGROUND))
        painter.setFont(QtGui.QFont("Helvetica", 10))

        fontRect = QtCore.QRect(14 + pixMapWidth, 6, self.sizeX - 10, self.labelSizeY - 10)
        painter.drawText(fontRect, 0, self.name)

        # Body
        path = QtGui.QPainterPath()
        path.setFillRule(Qt.WindingFill)
        path.addRoundedRect(QtCore.QRectF(0, self.labelSizeY, self.sizeX, self.sizeY - self.labelSizeY), 10, 10)
        path.addRect(0, self.labelSizeY, self.sizeX, self.sizeY / 2)

        painter.setBrush(bodyColor)
        painter.setPen(Qt.NoPen)
        painter.drawPath(path.simplified())
        
        if self.isSelected():
            painter.setPen(GetQColorFromPalette(ColorPalette.WARNINGCOLOR))
            
            selectionPath = QtGui.QPainterPath()
            selectionPath.addRoundedRect(QtCore.QRectF(0, 0, self.sizeX, self.sizeY), 10, 10)
            
            painter.setBrush(Qt.transparent)
            painter.drawPath(selectionPath)
            
        if self.getInternalNode().IsDisabled():
            path = QtGui.QPainterPath()
            path.setFillRule(Qt.WindingFill)
            path.addRoundedRect(QtCore.QRectF(0, 0, self.sizeX, self.sizeY), 10, 10)

            painter.setPen(Qt.NoPen)
            
            disabledColor = QtGui.QColor(0, 0, 0)
            disabledColor.setAlpha(100)
            
            painter.setBrush(disabledColor)
            painter.drawPath(path.simplified())
            
    def updateGPlugs(self) -> None:
        """
        """
        for plug in self.inputGPlugs:
            plug.update(plug.boundingRect())
        
        for plug in self.outputGPlugs:
            plug.update(plug.boundingRect())

    # EVENTS
    
    def contextMenuEvent(self, event: QtGui.QContextMenuEvent) -> None:
        """
        """
        super().contextMenuEvent(event)
        
        position = event.screenPos()

        menu = ContextMenu()
        
        cookAction = QtWidgets.QAction("Cook")
        cookAction.setToolTip("Cook the graph up to this node")
        cookAction.triggered.connect(lambda: self.cook())
        menu.addAction(cookAction)
        
        infoAction = QtWidgets.QAction("Infos")
        infoAction.triggered.connect(lambda: self.graph.showNodeInfosPanel(self))
        menu.addAction(infoAction)
        
        reloadOpCode = QtWidgets.QAction("Reload Op Code")
        reloadOpCode.setToolTip("Reloads the op code from the file definition")
        reloadOpCode.triggered.connect(lambda: self.getInternalNode().ReloadOpCode())
        menu.addAction(reloadOpCode)
        
        reload = QtWidgets.QAction("Reload")
        reload.setToolTip("Reloads the whole node from the file definition and resets plugs values")
        reload.triggered.connect(lambda: self.reloadNode())
        menu.addAction(reload)
        
        disableActionName = "Enable" if self.getInternalNode().IsDisabled() else "Disable"
        disable = QtWidgets.QAction(disableActionName)
        disable.triggered.connect(lambda: (self.getInternalNode().SetDisabled(True), self.updateBadge(), self.updateGPlugs()))
        menu.addAction(disable)
        
        deleteAction = QtWidgets.QAction("Delete")
        deleteAction.setToolTip("Delete this node from the graph")
        deleteAction.triggered.connect(lambda: (self.graph.deleteNode(self), self.graph.plugEditor.setCurrentNode(None)))
        menu.addAction(deleteAction)

        menu.exec(QtCore.QPoint(position.x(), position.y()))
        
        event.setAccepted(True)

    @QtCore.pyqtSlot(list)
    def onPlugClicked(self, data : list) -> None:
        self.plugHasBeenClicked.emit(data)
        self.hasBeenSelected.emit(self.getInternalNode().GetID())

    def hoverEnterEvent(self, ev):
        self.isHovered = True
        self.update()
        
        return super().hoverEnterEvent(ev)

    def hoverLeaveEvent(self, ev):
        self.isHovered = False
        self.update()
        
        return super().hoverLeaveEvent(ev)

    def mousePressEvent(self, event : QtGui.QMouseEvent) -> None:
        """
        When a node is clicked, set it on top of the other ones
        """
        for item in self.graph.items():
            item.setZValue(1)
        
        for item in self.graph.items():
            if isinstance(item, GEdge): item.setZValue(0)
        
        self.setZValue(2)

        self.hasBeenSelected.emit(self.getInternalNode().GetID())

        return super().mousePressEvent(event)
    
    def mouseDoubleClickEvent(self, event : QtGui.QMouseEvent) -> None:
        """
        """
        subGraphTypes = ["SubGraph", "IfBlock", "ForBlock"]
        
        if self.getInternalNode().GetNodeType() in subGraphTypes:
            self.openSubGraph.emit(self.getInternalNode().GetGraph())

    def mouseMoveEvent(self, event : QtGui.QMouseEvent) -> None:
        """
        """     
        return super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event : QtGui.QMouseEvent) -> None:
        """
        """
        return super().mouseReleaseEvent(event)

    # CHANGE

    def adjustEdges(self):
        """
        """
        for inputPlug in self.inputGPlugs:
            for edge in inputPlug.edges:
                edge.adjust()
        
        for outputPlug in self.outputGPlugs:
            for edge in outputPlug.edges:
                edge.adjust()   


class GEdge(QtWidgets.QGraphicsPathItem):
    """
    """
    def __init__(self, source: GPlug, dest: GPlug, parent=None):
        super().__init__(parent=parent)

        self.id = binascii.hexlify(os.urandom(16)).hex()

        self.setAcceptHoverEvents(True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges, True)

        self.source = source
        self.destination = dest
        self.source.addEdge(self)
        self.destination.addEdge(self)

        self.firstPos = self.source.scenePos()
        self.lastPos = self.destination.scenePos()

        self.__isHoveredByNode = False

        self.setFlag(QtWidgets.QGraphicsItem.ItemIsFocusable, True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, True)
        self.setZValue(0)

        self.adjust()

    def getFirstPointOffset(self) -> float:
        """
        """
        return self.source.boundingRect().width()
    
    def getSourcePlug(self) -> GPlug:
        """
        """
        return self.source
    
    def getDestinationPlug(self) -> GPlug:
        """
        """
        return self.destination

    def getControlPointsOffet(self) -> float:
        """
        """
        dist = math.sqrt((self.firstPos.x() - self.lastPos.x()) ** 2 + (self.firstPos.y() - self.lastPos.y()) ** 2)

        return dist / 2
    
    def buildPath(self) -> QtGui.QPainterPath:
        """
        """
        offset = self.getControlPointsOffet()

        path = QtGui.QPainterPath()
        path.moveTo(self.firstPos.x() + self.getFirstPointOffset(), self.firstPos.y() + 7.5)
        path.cubicTo(QtCore.QPointF(self.firstPos.x() + self.getFirstPointOffset() + offset, self.firstPos.y() + 7.5),
                     QtCore.QPointF(self.lastPos.x() - offset, self.lastPos.y() + 7.5),
                     QtCore.QPointF(self.lastPos.x(), self.lastPos.y() + 7.5))

        return path
    
    def shape(self):
        """
        """
        path = self.buildPath()
        
        stroke = QtGui.QPainterPathStroker()
        stroke.setWidth(20)
        
        return stroke.createStroke(path)

    def boundingRect(self) -> QtCore.QRectF:
        """
        """
        path = self.buildPath()
        
        stroke = QtGui.QPainterPathStroker()
        stroke.setWidth(20)
        
        return stroke.createStroke(path).boundingRect()

    # PAINTING

    def paint(self, painter : QtGui.QPainter, option : QtWidgets.QStyleOptionGraphicsItem, widget : QtWidgets.QWidget) -> None:
        """
        """
        painter.setRenderHints(QtGui.QPainter.Antialiasing | 
                               QtGui.QPainter.LosslessImageRendering |
                               QtGui.QPainter.TextAntialiasing | 
                               QtGui.QPainter.SmoothPixmapTransform | 
                               QtGui.QPainter.HighQualityAntialiasing)

        path = self.buildPath()

        gradient = QtGui.QLinearGradient()
        gradient.setColorAt(0.0, self.source.color)
        gradient.setColorAt(1.0, self.destination.color)
        gradient.setStart(self.firstPos)
        gradient.setFinalStop(self.lastPos)

        pen = QtGui.QPen()
        pen.setWidth(2)
        pen.setBrush(gradient)

        if self.isSelected() or self.isHoveredByNode():
            pen.setBrush(GetQColorFromPalette(ColorPalette.WARNINGCOLOR))

        painter.setPen(pen)

        painter.drawPath(path)

    def adjust(self):
        """
        """
        self.prepareGeometryChange()

        self.firstPos = self.source.scenePos()
        self.lastPos = self.destination.scenePos()

        rect = self.shape().boundingRect()

        self.update(rect)

    # NODE HOVER

    def setHoveredByNode(self, hovered : bool) -> None:
        """
        """
        self.__isHoveredByNode = hovered

    def isHoveredByNode(self) -> bool:
        """
        """
        return self.__isHoveredByNode