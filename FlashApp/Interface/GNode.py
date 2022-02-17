import binascii, os, math, time

from enum import Enum

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt

from FlashApi.Core.Node import *
from FlashApp.Interface.Icons import *
from FlashApp.Interface.Style import ColorPalette, GetQColorFromPalette
from FlashApp.Interface.Widgets import *

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
    if plugType == PlugType.INT: return QtGui.QColor("#89ddff")
    if plugType == PlugType.INT2: return QtGui.QColor("#89ddff")
    if plugType == PlugType.INT3: return QtGui.QColor("#89ddff")
    if plugType == PlugType.FLOAT: return QtGui.QColor("#80cbc4")
    if plugType == PlugType.FLOAT2: return QtGui.QColor("#80cbc4")
    if plugType == PlugType.FLOAT3: return QtGui.QColor("#80cbc4")
    if plugType == PlugType.STR: return QtGui.QColor("#c3e88d")
    if plugType == PlugType.BOOL: return QtGui.QColor("#eeffff")
    if plugType == PlugType.LIST: return QtGui.QColor("#f78c6c")
    if plugType == PlugType.DICT: return QtGui.QColor("#c792ea")
    if plugType == PlugType.CUSTOM: return QtGui.QColor("#f07178")


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

        self.dirtyPixmap = self.iconsLib.GetPixmap("badge-dirty")
        self.cookedPixmap = self.iconsLib.GetPixmap("badge-cooked")
        self.warningPixmap = self.iconsLib.GetPixmap("badge-warning")
        self.errorPixmap = self.iconsLib.GetPixmap("badge-error")

        # self.cookingMovie = self.iconsLib.GetAnim("badge-cooking")
        self.cookingMovie = QtGui.QMovie(f"{FLASHROOT}/Library/Icons/badge-cooking.gif")

        self.setPos(x - self.size, y)

        self.isHovered = False
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, True)
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

        painter.setBrush(self.color)

        if self.isInput:
            painter.drawEllipse(0, 0, self.radius, self.radius)

            painter.setPen(self.color)
            painter.setFont(QtGui.QFont("Helvetica", 8))

            fontRect = QtCore.QRect(self.radius + self.textWOffset, 0, self.labelRect.width(), self.radius)
            painter.drawText(fontRect, 0, self.getInternalPlug().GetShortName())
        else:
            painter.drawEllipse(self.labelRect.width() + self.textWOffset, 0, self.radius, self.radius)

            painter.setPen(self.color)
            painter.setFont(QtGui.QFont("Helvetica", 8))

            fontRect = QtCore.QRect(0, 0, self.labelRect.width() + self.textWOffset, self.radius)
            painter.drawText(fontRect, 0, self.getInternalPlug().GetShortName())

    # EVENTS

    def hoverEnterEvent(self, ev) -> None:
        """
        """
        self.isHovered = True
        self.update()
    
    def hoverLeaveEvent(self, ev) -> None:
        """
        """
        self.isHovered = False
        self.update()

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

        return super().mousePressEvent(event)

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

        printAction = QtWidgets.QAction("Debug")
        printAction.triggered.connect(lambda: print("Debug"))
        menu.addAction(printAction)

        if self.getInternalPlug().IsConnected():
            disconnectAction = menu.addAction("Disconnect")
            # disconnectAction.triggered.connect(lambda: self.deleteEdges())

        if self.isInput:
            if self.getInternalPlug().IsExposed():
                unexposeAction = QtWidgets.QAction("Unexpose")
                unexposeAction.triggered.connect(self.unexpose)
                menu.addAction(unexposeAction)
            else:
                unexposeAction = QtWidgets.QAction("Expose")
                unexposeAction.triggered.connect(self.expose)
                menu.addAction(unexposeAction)

        # menu.setWindowFlags(QtCore.Qt.FramelessWindowHint)

        action = menu.exec(QtCore.QPoint(position.x(), position.y()))

        event.setAccepted(True)

    # MISC      

    def expose(self) -> None:
        """
        """
        self.getInternalPlug().SetExposed(True)
        self.color.setAlpha(62)
        self.setAcceptTouchEvents(False)
        self.update(self.boundingRect())

        self.hasBeenRightClicked.emit([])
        
    def unexpose(self) -> None:
        """
        """
        self.getInternalPlug().SetExposed(False)
        self.color.setAlpha(255)
        self.setAcceptTouchEvents(True)
        self.update(self.boundingRect())
        
        self.hasBeenRightClicked.emit([])

    def addEdge(self, edge : GEdge) -> None:
        """
        """
        self.edges.append(edge)

    def deleteEdges(self) -> None:
        """
        """
        for edge in self.edges:
            edge.source.getInternalPlug().Disconnect(edge.destination.getInternalPlug())

            edge.source.edges.remove(edge)
            edge.destination.edges.remove(edge)

            self.scene.removeItem(edge)

class GNode(QtWidgets.QGraphicsObject):
    """
    """

    hasBeenSelected = QtCore.pyqtSignal(str)
    plugHasBeenClicked = QtCore.pyqtSignal(list)

    def __init__(self, node : Node, name : str, graph : GGraph, iconsLib : Icons):
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
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setCacheMode(QtWidgets.QGraphicsItem.DeviceCoordinateCache)
        self.setZValue(1)
        self.setAcceptHoverEvents(True)

    # NODE UTILS

    def getInternalNode(self) -> Node:
        """
        Returns:
            Node: internal node
        """
        return self.internalNode

    def getInputGPlugs(self):
        """
        """
        return self.inputGPlugs

    def getOutputGPlugs(self):
        """
        """
        return self.outputGPlugs

    def getInputGPlug(self, name : str) -> GPlug:
        """
        """
        for gplug in self.inputGPlugs:
            if gplug.getInternalPlug().GetShortName() == name:
                return gplug

        return None
    
    def getOutputGPlug(self, name : str) -> GPlug:
        """
        """
        for gplug in self.outputGPlugs:
            if gplug.getInternalPlug().GetShortName() == name:
                return gplug

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

    # PAINT

    def paint(self, painter : QtGui.QPainter, option : QtWidgets.QStyleOptionGraphicsItem, widget : QtWidgets.QWidget) -> None:
        """
        """
        painter.setRenderHints(QtGui.QPainter.Antialiasing | 
                               QtGui.QPainter.LosslessImageRendering |
                               QtGui.QPainter.TextAntialiasing | 
                               QtGui.QPainter.SmoothPixmapTransform | 
                               QtGui.QPainter.HighQualityAntialiasing)

        ## Shadow
        shadowOffset = 10
        path = QtGui.QPainterPath()
        path.setFillRule(Qt.WindingFill)
        path.addRoundedRect(QtCore.QRectF(shadowOffset, shadowOffset, self.sizeX, self.labelSizeY), 10, 10)
        path.addRoundedRect(QtCore.QRectF(shadowOffset, self.labelSizeY, self.sizeX, self.sizeY - self.labelSizeY + shadowOffset), 10, 10)
        path.addRect(shadowOffset, self.labelSizeY, self.sizeX, self.sizeY / 2)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QtGui.QColor(0, 0, 0, 60))
        painter.drawPath(path.simplified())
        
        ## Body
        
        bodyColor = GetQColorFromPalette(ColorPalette.ACTIVE)

        # Label
        path = QtGui.QPainterPath()
        path.setFillRule(Qt.WindingFill)
        path.addRoundedRect(QtCore.QRectF(0, 0, self.sizeX, self.labelSizeY), 10, 10)
        path.addRect(0, self.labelSizeY / 2, self.sizeX, self.labelSizeY / 2)

        painter.setBrush(GetQColorFromPalette(ColorPalette.HIGHLIGHT))
        painter.setPen(Qt.NoPen)
        painter.drawPath(path.simplified())

        # Icon (if has any)
        pixMapWidth = 0

        if self.pixMap is not None:
            pixMapWidth = self.iconSize
            painter.drawPixmap(7, 7, pixMapWidth, pixMapWidth, self.pixMap)

        # Label name
        painter.setPen(GetQColorFromPalette(ColorPalette.SELECTIONFOREGROUND))
        painter.setFont(QtGui.QFont("Helvetica", 12))

        fontRect = QtCore.QRect(14 + pixMapWidth, 6, self.sizeX - 10, self.labelSizeY - 10)
        painter.drawText(fontRect, 0, self.name)

        # Body
        path = QtGui.QPainterPath()
        path.setFillRule(Qt.WindingFill)
        path.addRoundedRect(QtCore.QRectF(0, self.labelSizeY, self.sizeX, self.sizeY - self.labelSizeY), 10, 10)
        path.addRect(0, self.labelSizeY, self.sizeX, self.sizeY / 2)

        if self.isHovered or self.isSelected():
            pass

        painter.setBrush(bodyColor)
        painter.setPen(Qt.NoPen)
        painter.drawPath(path.simplified())

    # EVENTS

    @QtCore.pyqtSlot(list)
    def onPlugClicked(self, data : list) -> None:
        # print(data)
        self.plugHasBeenClicked.emit(data)
        self.hasBeenSelected.emit(self.getInternalNode().GetID())

    def hoverEnterEvent(self, ev):
        self.isHovered = True
        self.update()

    def hoverLeaveEvent(self, ev):
        self.isHovered = False
        self.update()

    def mousePressEvent(self, ev):
        pos = ev.pos()

        if self.isHovered:
            self.setSelected(True)
            self.hasBeenSelected.emit(self.id)

            for item in self.graph.items():
                item.setZValue(1)
            
            for item in self.graph.items():
                if type(item) is Edge: item.setZValue(-1)

            self.setZValue(2)

        if pos.x() < 15.0 or pos.x() > self.sizeX: 
            self.canMove = False
        else:
            self.canMove = True

    def mouseMoveEvent(self, event):
        if self.canMove and event.buttons() & Qt.LeftButton:
            origCursorPos = event.lastScenePos()
            updatedCursorPos = event.scenePos()

            origPosition = self.scenePos()

            updatedCursorX = updatedCursorPos.x() - origCursorPos.x() + origPosition.x()
            updatedCursorY = updatedCursorPos.y() - origCursorPos.y() + origPosition.y()

            if QtGui.QGuiApplication.keyboardModifiers() & Qt.ShiftModifier:
                gridSize = self.scene().gridSize

                newPos = QtCore.QPointF(round(updatedCursorX / gridSize) * gridSize, round(updatedCursorY / gridSize) * gridSize)
                self.setPos(newPos)
            else:
                self.setPos(updatedCursorX, updatedCursorY)
            
            self.adjustEdges()
        
        else:
            return super().mouseMoveEvent(event)

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


class Edge(QtWidgets.QGraphicsItem):
    """
    """
    def __init__(self, source: GPlug, dest: GPlug, parent=None):
        super().__init__(parent=parent)

        self.id = binascii.hexlify(os.urandom(16)).hex()

        self.setAcceptHoverEvents(True)

        self.source = source
        self.destination = dest
        self.source.addEdge(self)
        self.destination.addEdge(self)

        self.firstPos = self.source.scenePos()
        self.lastPos = self.destination.scenePos()

        self.isHovered = False

        self.setFlag(QtWidgets.QGraphicsItem.ItemIsFocusable, True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, True)
        self.setZValue(-1)

        self.adjust()

    def getFirstPointOffset(self) -> float:
        """
        """
        return self.source.boundingRect().width()

    def getControlPointsOffet(self) -> float:
        """
        """
        dist = math.sqrt((self.firstPos.x() - self.lastPos.x()) ** 2 + (self.firstPos.y() - self.lastPos.y()) ** 2)

        return dist / 2

    def boundingRect(self) -> QtCore.QRectF:
        """
        """
        offset = self.getControlPointsOffet()

        path = QtGui.QPainterPath()
        path.moveTo(self.firstPos.x() + self.getFirstPointOffset(), self.firstPos.y() + 7.5)
        path.cubicTo(QtCore.QPointF(self.firstPos.x() + self.getFirstPointOffset() + offset, self.firstPos.y() + 7.5),
                     QtCore.QPointF(self.lastPos.x() - offset, self.lastPos.y() + 7.5),
                     QtCore.QPointF(self.lastPos.x(), self.lastPos.y() + 7.5))

        return path.boundingRect()

    # PAINTING

    def paint(self, painter : QtGui.QPainter, option : QtWidgets.QStyleOptionGraphicsItem, widget : QtWidgets.QWidget) -> None:
        """
        """
        painter.setRenderHints(QtGui.QPainter.Antialiasing | 
                               QtGui.QPainter.LosslessImageRendering |
                               QtGui.QPainter.TextAntialiasing | 
                               QtGui.QPainter.SmoothPixmapTransform | 
                               QtGui.QPainter.HighQualityAntialiasing)

        offset = self.getControlPointsOffet()

        path = QtGui.QPainterPath()
        path.moveTo(self.firstPos.x() + self.getFirstPointOffset(), self.firstPos.y() + 7.5)
        path.cubicTo(QtCore.QPointF(self.firstPos.x() + self.getFirstPointOffset() + offset, self.firstPos.y() + 7.5),
                     QtCore.QPointF(self.lastPos.x() - offset, self.lastPos.y() + 7.5),
                     QtCore.QPointF(self.lastPos.x(), self.lastPos.y() + 7.5))

        gradient = QtGui.QLinearGradient()
        gradient.setColorAt(0.0, self.source.color)
        gradient.setColorAt(1.0, self.destination.color)
        gradient.setStart(self.firstPos)
        gradient.setFinalStop(self.lastPos)

        pen = QtGui.QPen()
        pen.setWidth(2)
        pen.setBrush(gradient)
        painter.setPen(pen)

        painter.drawPath(path)

    def adjust(self):
        """
        """
        self.prepareGeometryChange()

        self.firstPos = self.source.scenePos()
        self.lastPos = self.destination.scenePos()

        self.update(self.boundingRect())

    # EVENTS

    def mousePressEvent(self, event) -> None:
        """
        """
        if self.isHovered is True:
            self.setSelected(True)

    def hoverEnterEvent(self, event) -> None:
        """
        """
        self.isHovered = True
        self.adjust()

    def hoverLeaveEvent(self, event) -> None:
        """
        """
        self.isHovered = False
        self.adjust()