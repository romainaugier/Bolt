import binascii
import os, math

from enum import Enum

from FlashApi.Core.Node import *

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt

from FlashApp.Interface.Icons import *

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
    if plugType == PlugType.BOOL: return QtGui.QColor("#f78c6c")
    if plugType == PlugType.LIST: return QtGui.QColor("#ffcb6b")
    if plugType == PlugType.DICT: return QtGui.QColor("#c792ea")
    if plugType == PlugType.CUSTOM: return QtGui.QColor("#f07178")


def GetFontRect(text : str) -> QtCore.QRect:
    """
    Gets size of a text

    Args:
        text (str): text

    Returns:
        QtCore.QRect: bounding box of the text
    """
    metric = QtGui.QFontMetrics(QtGui.QFont("Helvetica", 8))
    return metric.boundingRect(text)


class GPlug(QtWidgets.QGraphicsItem):
    """
    """
    def __init__(self, x: int, y: int, plug : Plug, node: Node, graph : GGraph, input=True, parent=None):
        super().__init__(parent=parent)

        self.id = binascii.hexlify(os.urandom(16)).hex()

        self.internalPlug = plug
        self.node = node
        self.graph = graph
        self.closestGPlug = None
        self.isInput = input

        self.color = GetPlugColor(self.getInternalPlug().GetType())

        self.edges = []

        self.radius = 15

        malus = 0

        if not input:
            malus = self.radius / 2.0

        self.labelRect = GetFontRect(self.getInternalPlug().GetShortName())

        newPosX = self.pos().x() - self.labelRect.width() - 3
        self.setPos(newPosX, self.pos().y())

        self._x = x - malus
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
            return QtCore.QRectF(0, 0, self.radius + self.labelRect.width() + 3, self.radius)
        else:
            return QtCore.QRectF(0, 0, self.radius + self.labelRect.width() + 3, self.radius)

    def paint(self, painter : QtGui.QPainter, option : QtWidgets.QStyleOptionGraphicsItem, widget : QtWidgets.QWidget) -> None:
        """
        """
        pen = QtGui.QPen()
        pen.setBrush(Qt.black)
        pen.setWidth(0.01)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)

        painter.setPen(Qt.NoPen)

        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        painter.setBrush(self.color)

        painter.drawEllipse(0, 0, self.radius, self.radius)

        painter.drawRect(0, 0, 100, 100)

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
    
    def mouseMoveEvent(self, ev) -> None:
        x = ev.scenePos().x()
        y = ev.scenePos().y()

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

    def mouseReleaseEvent(self, ev) -> None:
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

            if condition1 and condition2 and condition3:
                self.graph.addEdge(self, self.closestGPlug)
            

    def addEdge(self, edge : GEdge) -> None:
        """
        """
        self.edges.append(edge)


class GNode(QtWidgets.QGraphicsObject):
    """
    """

    hasBeenSelected = QtCore.pyqtSignal(str)

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

        self.sizeX = 250
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
            self.inputGPlugs.append(newGPlug)

            i += 1
        
        for outputName, output in self.getInternalNode().GetOutputs().items():
            positionX = self.pos().x() + self.sizeX - 12.5
            positionY = self.pos().y() + self.labelSizeY + bodySizeYPerPlug
            
            newGPlug = GPlug(positionX, positionY, output, self, self.graph, input=False, parent=self)
            self.outputGPlugs.append(newGPlug)

        self.numInputs = numInputs
        self.numOuputs = numOutputs
        self.color = QtGui.QColor(self.internalNode.GetColor()[0], self.internalNode.GetColor()[1], self.internalNode.GetColor()[2])

        self.canMove = True
        self.isHovered = False
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsFocusable, True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setCacheMode(QtWidgets.QGraphicsItem.DeviceCoordinateCache)
        self.setZValue(1)
        self.setAcceptHoverEvents(True)

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

    def boundingRect(self):
        """
        """
        adjust = 10
        return QtCore.QRectF(-adjust, -adjust, self.sizeX + adjust * 2, self.sizeY + adjust * 2)

    def paint(self, painter : QtGui.QPainter, option : QtWidgets.QStyleOptionGraphicsItem, widget : QtWidgets.QWidget) -> None:
        """
        """
        ## Shadow
        shadowOffset = 10
        path = QtGui.QPainterPath()
        path.setFillRule(Qt.WindingFill)
        path.addRoundedRect(QtCore.QRectF(shadowOffset, shadowOffset, self.sizeX, self.labelSizeY), 10, 10)
        path.addRoundedRect(QtCore.QRectF(shadowOffset, self.labelSizeY, self.sizeX, self.sizeY - self.labelSizeY + shadowOffset), 10, 10)
        path.addRect(shadowOffset, self.labelSizeY, self.sizeX, self.sizeY / 2)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QtGui.QColor(0, 0, 0, 127))
        painter.drawPath(path.simplified())
        
        ## Body

        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        
        bodyColor = QtGui.QColor(48, 46, 54, 255)

        # Label
        path = QtGui.QPainterPath()
        path.setFillRule(Qt.WindingFill)
        path.addRoundedRect(QtCore.QRectF(0, 0, self.sizeX, self.labelSizeY), 10, 10)
        path.addRect(0, self.labelSizeY / 2, self.sizeX, self.labelSizeY / 2)
        
        painter.setBrush(self.color)

        labelGradient = QtGui.QLinearGradient()
        labelGradient.setStart(0, 0)
        labelGradient.setFinalStop(self.sizeX, self.labelSizeY)
        labelGradient.setColorAt(0.0, bodyColor)
        labelGradient.setColorAt(1.0, self.color)

        painter.setBrush(labelGradient)
        painter.setPen(Qt.NoPen)
        painter.drawPath(path.simplified())

        # Icon (if has any)
        pixMapWidth = 0

        if self.pixMap is not None:
            pixMapWidth = 18
            painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
            painter.setRenderHint(QtGui.QPainter.LosslessImageRendering)
            painter.drawPixmap(7, 7, pixMapWidth, pixMapWidth, self.pixMap)

        # Label name
        painter.setPen(QtGui.QColor(224, 227, 227, 255))
        painter.setFont(QtGui.QFont("Helvetica", 12))

        fontRect = QtCore.QRect(14 + pixMapWidth, 6, self.sizeX - 10, self.labelSizeY - 10)
        painter.drawText(fontRect, 0, self.name)

        # Body
        path = QtGui.QPainterPath()
        path.setFillRule(Qt.WindingFill)
        path.addRoundedRect(QtCore.QRectF(0, self.labelSizeY, self.sizeX, self.sizeY - self.labelSizeY), 10, 10)
        path.addRect(0, self.labelSizeY, self.sizeX, self.sizeY / 2)


        if self.isHovered or self.isSelected():
            bodyColor = QtGui.QColor(58, 56, 64, 255)

        painter.setBrush(bodyColor)
        painter.setPen(Qt.NoPen)
        painter.drawPath(path.simplified())
        
        # self.errorPixmap = self.iconsLib.GetPixmap("node-error")
        # painter.drawPixmap(0, 0, 48, 48, self.errorPixmap)

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

    def mouseMoveEvent(self, ev):
        if self.canMove:
            origCursorPos = ev.lastScenePos()
            updatedCursorPos = ev.scenePos()

            origPosition = self.scenePos()

            updatedCursorX = updatedCursorPos.x() - origCursorPos.x() + origPosition.x()
            updatedCursorY = updatedCursorPos.y() - origCursorPos.y() + origPosition.y()

            self.setPos(updatedCursorX, updatedCursorY)

            for inputSock in self.inputGPlugs:
                for edge in inputSock.edges:
                    edge.adjust()
            
            for outputSock in self.outputGPlugs:
                for edge in outputSock.edges:
                    edge.adjust()   

    def mouseReleaseEvent(self, ev):
        pass


class Edge(QtWidgets.QGraphicsLineItem):
    """
    """
    def __init__(self, source: GPlug, dest: GPlug, parent=None):
        super().__init__(parent=parent)

        self.id = binascii.hexlify(os.urandom(16)).hex()

        self.source = source
        self.destination = dest
        self.source.addEdge(self)
        self.destination.addEdge(self)

        self.isHovered = False

        self.setFlag(QtWidgets.QGraphicsItem.ItemIsFocusable, True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, True)
        self.setZValue(-1)

        self.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 125), 1.0))

        self.adjust()

    def adjust(self):
        """
        """
        self.prepareGeometryChange()

        first = self.source.scenePos()
        last = self.destination.scenePos()

        offset = self.source.radius / 2.0

        color = QtGui.QColor(224, 227, 227, 51)

        if self.isHovered is True:
            color = QtGui.QColor(224, 227, 227, 255)

        pen = QtGui.QPen()
        pen.setWidth(5)
        pen.setColor(color)
        self.setPen(pen)

        self.setLine(first.x() + offset, first.y() + offset, last.x() + offset, last.y() + offset)

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