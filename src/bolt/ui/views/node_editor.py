from __future__ import annotations

import functools
import json
import math
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QLineF, QMimeData, QPoint, QPointF, QRect, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (QBrush, QColor, QFont, QKeyEvent, QKeySequence, QLinearGradient, QMouseEvent, QPainter,
                           QPainterPath, QPainterPathStroker, QPen, QPixmap, QWheelEvent)
from PySide6.QtWidgets import (QApplication, QFrame, QGraphicsItem, QGraphicsPathItem, QGraphicsScene,
                               QGraphicsSceneHoverEvent, QGraphicsSceneMouseEvent, QGraphicsView, QHBoxLayout,
                               QInputDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMenu,
                               QStyleOptionGraphicsItem, QToolButton, QVBoxLayout, QWidget)

from bolt.core import events
from bolt.core.graph import Connection, Graph
from bolt.core.layout import LayoutEdge, LayoutOptions, sugiyama_layout
from bolt.core.node import Node, NodeState
from bolt.core.plugs import Plug, PlugKind
from bolt.core.serialization import node_to_dict
from bolt.ui import icons, theme
from bolt.ui.commands import (InsertNodes, MoveNodes, RemoveNodes, RenameNode, SetFlag, SetPlugKind, connect_command,
                              create_node_command, disconnect_command, internal_connections)
from bolt.ui.events import CurrentDocumentChanged, CurrentGraphChanged, NodeCreationRequested, SelectionChanged
from bolt.ui.icons import bind_icon
from bolt.ui.views.base import View

if TYPE_CHECKING:
    from bolt.ui.workspace import Document, Workspace

node_type_mime = "application/x-bolt-node-type"
clipboard_mime = "application/x-bolt-nodes"

node_width = 180.0
grid_size = 20.0
grid_major = 5
header_height = 30.0
row_height = 20.0
bottom_padding = 10.0
plug_radius = 5.5
flag_size = 12.0
badge_radius = 8.0
icon_size = 18.0


@functools.lru_cache(maxsize=64)
def header_path(radius: float) -> QPainterPath:
    """The header: rounded top corners, square bottom, built explicitly rather than by combining shapes."""
    radius = min(radius, header_height / 2)
    diameter = radius * 2
    path = QPainterPath(QPointF(0, header_height))
    path.lineTo(0, radius)
    path.arcTo(QRectF(0, 0, diameter, diameter), 180, -90)
    path.lineTo(node_width - radius, 0)
    path.arcTo(QRectF(node_width - diameter, 0, diameter, diameter), 90, -90)
    path.lineTo(node_width, header_height)
    path.closeSubpath()

    return path


@functools.lru_cache(maxsize=256)
def body_path(height: float, radius: float) -> QPainterPath:
    """The body: starts under the header so no seam or corner fringe shows between them, rounded at the bottom."""
    radius = min(radius, header_height / 2, (height - header_height) / 2)
    diameter = radius * 2
    top = header_height - radius
    path = QPainterPath(QPointF(0, top))
    path.lineTo(node_width, top)
    path.lineTo(node_width, height - radius)
    path.arcTo(QRectF(node_width - diameter, height - diameter, diameter, diameter), 0, -90)
    path.lineTo(radius, height)
    path.arcTo(QRectF(0, height - diameter, diameter, diameter), 270, -90)
    path.closeSubpath()

    return path


def resized_font(font: QFont, delta: float) -> QFont:
    """A copy of font, delta points (or pixels, for fonts sized in pixels by a stylesheet) larger."""
    result = QFont(font)

    if result.pointSizeF() > 0:
        result.setPointSizeF(max(result.pointSizeF() + delta, 6))
    else:
        result.setPixelSize(max(round(result.pixelSize() + delta), 8))

    return result


def snap(value: float) -> float:
    return round(value / grid_size) * grid_size


def plug_color(plug: Plug) -> QColor:
    data_type = plug.data_type

    if data_type is None:
        return theme.muted

    return theme.type_color(data_type.name, data_type.ui)


class PlugItem(QGraphicsItem):
    def __init__(self, plug: Plug, parent: NodeItem) -> None:
        super().__init__(parent)
        self.plug = plug
        self.highlighted = False
        self.setAcceptHoverEvents(True)
        self.setToolTip(f"{plug.name}: {plug.spec.type_name}" + (" (multi)" if plug.spec.multi else ""))
        self._hovered = False

    @property
    def node_item(self) -> NodeItem:
        return self.parentItem()

    @property
    def color(self) -> QColor:
        color = plug_color(self.plug)

        if self.plug.node.disabled:
            color.setAlpha(78)

        return color

    def boundingRect(self) -> QRectF:
        extent = plug_radius + 4

        return QRectF(-extent, -extent, extent * 2, extent * 2)

    def shape(self) -> QPainterPath:
        path = QPainterPath()
        path.addEllipse(QPointF(0, 0), plug_radius + 4, plug_radius + 4)

        return path

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget | None = None) -> None:
        painter.setRenderHint(QPainter.Antialiasing)
        radius = plug_radius + (1.5 if self._hovered or self.highlighted else 0)
        painter.setPen(QPen(theme.accent if self.highlighted else theme.node_body, 2 if self.highlighted else 1.5))
        painter.setBrush(self.color)

        if self.plug.spec.multi:
            painter.drawRoundedRect(QRectF(-radius, -radius, radius * 2, radius * 2), 2.5, 2.5)
        else:
            painter.drawEllipse(QPointF(0, 0), radius, radius)

    def hoverEnterEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        self._hovered = True
        self.update()

    def hoverLeaveEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        self._hovered = False
        self.update()

    def set_highlighted(self, highlighted: bool) -> None:
        if highlighted != self.highlighted:
            self.highlighted = highlighted
            self.update()

    def scene_anchor(self) -> QPointF:
        return self.scenePos()


state_icons = {NodeState.uncooked: ("schedule", "muted"), NodeState.cooked: ("check_circle-fill", "success"),
               NodeState.failed: ("error-fill", "error"), NodeState.blocked: ("warning-fill", "warning")}


def _draw_badge(painter: QPainter, rect: QRectF, pixmap: QPixmap) -> None:
    if not pixmap.isNull():
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.drawPixmap(rect, pixmap, QRectF(pixmap.rect()))


class NodeItem(QGraphicsItem):
    def __init__(self, node: Node) -> None:
        super().__init__()
        self.node = node
        self.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable
                      | QGraphicsItem.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)
        self.plug_items: dict[str, PlugItem] = {}
        self.connections: list[ConnectionItem] = []
        self.height = header_height + row_height + bottom_padding
        self.rebuild_plugs()

        position = node.metadata.get("position")

        if position:
            self.setPos(float(position[0]), float(position[1]))

    @property
    def color(self) -> QColor:
        return theme.node_header_color(type(self.node).ui)

    def rebuild_plugs(self) -> None:
        for item in self.plug_items.values():
            item.setParentItem(None)

            if item.scene() is not None:
                item.scene().removeItem(item)

        self.plug_items = {}

        inputs = list(self.node.input_plugs())
        outputs = list(self.node.output_plugs())
        rows = max(len(inputs), len(outputs), 1)

        self.prepareGeometryChange()
        self.height = header_height + rows * row_height + bottom_padding

        for index, plug in enumerate(inputs):
            item = PlugItem(plug, self)
            item.setPos(0, header_height + row_height * (index + 0.5))
            self.plug_items[plug.name] = item

        for index, plug in enumerate(outputs):
            item = PlugItem(plug, self)
            item.setPos(node_width, header_height + row_height * (index + 0.5))
            self.plug_items[plug.name] = item

        self.update()

    def boundingRect(self) -> QRectF:
        shadow = theme.shadow_offset
        return QRectF(-2, -2, node_width + 4 + shadow, self.height + 20 + shadow)

    def display_flag_rect(self) -> QRectF:
        return QRectF(node_width - flag_size - 9, (header_height - flag_size) / 2, flag_size, flag_size)

    def disable_flag_rect(self) -> QRectF:
        return QRectF(node_width - 2 * flag_size - 14, (header_height - flag_size) / 2, flag_size, flag_size)

    def badge_center(self) -> QPointF:
        return QPointF(node_width - 2 * flag_size - 21 - badge_radius, header_height / 2)

    def badge_rect(self) -> QRectF:
        center = self.badge_center()

        return QRectF(center.x() - badge_radius, center.y() - badge_radius, 2 * badge_radius, 2 * badge_radius)

    def header_icon(self) -> QPixmap | None:
        name = type(self.node).ui.get("icon")

        if not name:
            return None

        pixmap = icons.library.pixmap(name, int(icon_size * 2), theme.node_text)

        return None if pixmap.isNull() else pixmap

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget | None = None) -> None:
        node = self.node
        radius = theme.node_radius
        outline = QRectF(0, 0, node_width, self.height)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)

        shadow = theme.shadow_offset

        if shadow > 0:
            painter.setBrush(theme.node_shadow)
            painter.drawRoundedRect(outline.translated(shadow, shadow), radius, radius)

        painter.setBrush(theme.node_body)
        painter.drawPath(body_path(self.height, radius))
        painter.setBrush(self.color)
        painter.drawPath(header_path(radius))

        title_font = resized_font(painter.font(), 1)
        painter.setFont(title_font)
        painter.setPen(theme.node_text)
        title_right = self.badge_center().x() - badge_radius - (22 if node.child_graphs() else 6)
        title_left = 12.0
        header_icon = self.header_icon()

        if header_icon is not None:
            top = (header_height - icon_size) / 2
            _draw_badge(painter, QRectF(9, top, icon_size, icon_size), header_icon)
            title_left = 9 + icon_size + 6

        title_rect = QRectF(title_left, 0, title_right - title_left, header_height)
        title = painter.fontMetrics().elidedText(node.name, Qt.ElideRight, int(title_rect.width()))
        painter.drawText(title_rect, Qt.AlignVCenter | Qt.AlignLeft, title)

        if node.child_graphs():
            painter.setPen(QPen(theme.node_text, 1.2))
            painter.setBrush(Qt.NoBrush)
            corner = QRectF(title_right + 4, header_height / 2 - 5, 9, 7)
            painter.drawRoundedRect(corner, 1.5, 1.5)
            painter.drawRoundedRect(corner.translated(3, 3), 1.5, 1.5)

        scene = self.scene()

        if node.state is NodeState.cooking and isinstance(scene, GraphScene):
            _draw_badge(painter, self.badge_rect(), scene.cooking_frame(self))
        else:
            name, role = state_icons.get(node.state, state_icons[NodeState.uncooked])
            _draw_badge(painter, self.badge_rect(), icons.library.pixmap(name, int(badge_radius * 4),
                                                                         getattr(theme, role)))

        small = resized_font(painter.font(), -2)
        painter.setFont(small)

        for name, item in self.plug_items.items():
            y = item.pos().y()
            label_rect = QRectF(12, y - row_height / 2, node_width / 2 - 12, row_height)
            painter.setPen(plug_color(item.plug))

            if item.plug.kind is PlugKind.input:
                painter.drawText(label_rect, Qt.AlignVCenter | Qt.AlignLeft, name)
            else:
                painter.drawText(label_rect.translated(node_width / 2 - 12, 0), Qt.AlignVCenter | Qt.AlignRight, name)

        if node.disabled:
            painter.setPen(Qt.NoPen)
            painter.setBrush(theme.node_veil)
            painter.drawRoundedRect(outline, radius, radius)

        border = None

        if self.isSelected():
            border = QPen(theme.node_selected, 1.5)
        elif node.displayed:
            border = QPen(theme.display, 1.5)

        if border is not None:
            painter.setPen(border)
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(outline.adjusted(0.5, 0.5, -0.5, -0.5), radius, radius)

        painter.setPen(QPen(theme.node_body, 1))

        for rect, active, color in ((self.display_flag_rect(), node.displayed, theme.display),
                                    (self.disable_flag_rect(), node.disabled, theme.warning)):
            painter.setBrush(color if active else theme.node_body)
            painter.drawRoundedRect(rect, 3, 3)

        footer = node.type_name or getattr(node, "missing_type", "")

        if node.state is NodeState.cooked and node.cook_time is not None:
            footer += f"  ·  {node.cook_time * 1000:.1f} ms"
        elif node.state is NodeState.failed and node.error:
            footer += "  ·  failed"

        painter.setPen(theme.muted)
        painter.drawText(QRectF(2, self.height + 3, node_width, 14), Qt.AlignLeft | Qt.AlignVCenter, footer)

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value: Any) -> Any:
        if change == QGraphicsItem.ItemPositionChange:
            scene = self.scene()

            if scene is not None and scene.snapping:
                return QPointF(snap(value.x()), snap(value.y()))
        elif change == QGraphicsItem.ItemPositionHasChanged:
            for connection in self.connections:
                connection.update_path()

        return super().itemChange(change, value)

    def hoverMoveEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        if self.display_flag_rect().contains(event.pos()):
            self.setToolTip("Display flag: live cooking cooks the displayed nodes (R)")
        elif self.disable_flag_rect().contains(event.pos()):
            self.setToolTip("Disable flag: the node passes its first input through (Q)")
        elif QLineF(event.pos(), self.badge_center()).length() <= badge_radius + 2:
            self.setToolTip(self.node.error or self.node.state.value)
        else:
            self.setToolTip(self.node.error or type(self.node).description)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            scene = self.scene()

            if self.display_flag_rect().contains(event.pos()):
                scene.toggle_flag(self.node, "displayed")
                event.accept()
                return

            if self.disable_flag_rect().contains(event.pos()):
                scene.toggle_flag(self.node, "disabled")
                event.accept()
                return

        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if self.node.child_graphs():
            self.scene().workspace.set_current_graph(self.node.child_graphs()[0])
            return

        super().mouseDoubleClickEvent(event)


class ConnectionItem(QGraphicsPathItem):
    def __init__(self, connection: Connection, source: PlugItem, target: PlugItem) -> None:
        super().__init__()
        self.connection = connection
        self.source = source
        self.target = target
        self.setFlags(QGraphicsItem.ItemIsSelectable)
        self.setZValue(-1)
        source.node_item.connections.append(self)
        target.node_item.connections.append(self)
        self.update_path()

    def update_path(self) -> None:
        self.setPath(curve(self.source.scene_anchor(), self.target.scene_anchor()))

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget | None = None) -> None:
        painter.setRenderHint(QPainter.Antialiasing)
        width = theme.connection_width

        if self.isSelected():
            pen = QPen(theme.node_selected, width + 0.5)
        else:
            start, end = self.source.scene_anchor(), self.target.scene_anchor()
            gradient = QLinearGradient(start, end)
            gradient.setColorAt(0.0, self.source.color)
            gradient.setColorAt(1.0, self.target.color)
            pen = QPen(QBrush(gradient), width)

        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(self.path())

    def shape(self) -> QPainterPath:
        stroker = QPainterPathStroker()
        stroker.setWidth(10)

        return stroker.createStroke(self.path())

    def detach(self) -> None:
        for item in (self.source.node_item, self.target.node_item):
            if self in item.connections:
                item.connections.remove(self)


def curve(start: QPointF, end: QPointF) -> QPainterPath:
    path = QPainterPath(start)
    offset = QLineF(start, end).length() / 2
    path.cubicTo(QPointF(start.x() + offset, start.y()), QPointF(end.x() - offset, end.y()), end)

    return path


class GraphScene(QGraphicsScene):
    """Mirrors one graph: node and connection items kept in sync with the graph events."""

    def __init__(self, workspace: Workspace) -> None:
        super().__init__()
        self.workspace = workspace
        self.document: Document | None = None
        self.graph: Graph | None = None
        self.node_items: dict[Node, NodeItem] = {}
        self.connection_items: dict[Connection, ConnectionItem] = {}
        self.snapping = False
        self.setSceneRect(-50000, -50000, 100000, 100000)
        self.cooking_items: set[NodeItem] = set()
        self.spinner = icons.Spinner(self)
        self.spinner.advanced.connect(self._next_cooking_frame)

    def cooking_frame(self, item: NodeItem) -> QPixmap:
        """The current frame of the cooking indicator, which turns while items ask for it."""
        self.cooking_items.add(item)
        self.spinner.start()

        return self.spinner.pixmap(int(badge_radius * 4), theme.warning)

    def _next_cooking_frame(self) -> None:
        for item in list(self.cooking_items):
            if item.node.state is NodeState.cooking:
                item.update(item.badge_rect())
            else:
                self.cooking_items.discard(item)
                item.update(item.badge_rect())

        if not self.cooking_items:
            self.spinner.stop()

    def show_graph(self, document: Document | None, graph: Graph | None) -> None:
        self.cooking_items.clear()
        self.clearSelection()
        self.clear()
        self.node_items = {}
        self.connection_items = {}
        self.document = document
        self.graph = graph

        if graph is None:
            return

        self._place_unpositioned(graph)

        for node in graph:
            self._add_node(node)

        for connection in graph.connections():
            self._add_connection(connection)

    def owns(self, graph: Graph) -> bool:
        return graph is self.graph

    def selected_nodes(self) -> list[Node]:
        return [item.node for item in self.selectedItems() if isinstance(item, NodeItem)]

    def selected_connections(self) -> list[Connection]:
        return [item.connection for item in self.selectedItems() if isinstance(item, ConnectionItem)]

    def select_nodes(self, nodes: Iterable[Node]) -> None:
        nodes = set(nodes)

        for node, item in self.node_items.items():
            item.setSelected(node in nodes)

    def toggle_flag(self, node: Node, flag: str) -> None:
        if self.document is not None:
            self.document.push(SetFlag(self.document, node, flag, not getattr(node, flag)))

    def on_event(self, event: events.GraphEvent) -> None:
        if not self.owns(event.graph):
            return

        if isinstance(event, events.NodeAdded):
            self._add_node(event.node)
        elif isinstance(event, events.NodeRemoved):
            self._remove_node(event.node)
        elif isinstance(event, events.Connected):
            self._add_connection(event.connection)
        elif isinstance(event, events.Disconnected):
            self._remove_connection(event.connection)
        elif isinstance(event, (events.PlugAdded, events.PlugRemoved, events.PlugKindChanged)):
            node = event.node if isinstance(event, events.PlugRemoved) else event.plug.node
            self._rebuild_node(node)
        elif isinstance(event, events.NodeChanged) and event.attribute == "position":
            item = self.node_items.get(event.node)
            position = event.node.metadata.get("position")

            if item is not None and position:
                item.setPos(float(position[0]), float(position[1]))
        elif hasattr(event, "node"):
            item = self.node_items.get(event.node)

            if item is not None:
                item.update()

    def _add_node(self, node: Node) -> None:
        if node in self.node_items:
            return

        item = NodeItem(node)

        self.addItem(item)
        self.node_items[node] = item

    def _remove_node(self, node: Node) -> None:
        item = self.node_items.pop(node, None)

        if item is not None:
            self.cooking_items.discard(item)

            for connection in list(item.connections):
                self._remove_connection(connection.connection)

            self.removeItem(item)

    def _rebuild_node(self, node: Node) -> None:
        item = self.node_items.get(node)

        if item is None:
            return

        for connection in list(item.connections):
            self._remove_connection(connection.connection)

        item.rebuild_plugs()

        for plug in node.plugs():
            for connection in plug.connections:
                self._add_connection(connection)

    def _add_connection(self, connection: Connection) -> None:
        if connection in self.connection_items:
            return

        source_item = self.node_items.get(connection.source.node)
        target_item = self.node_items.get(connection.target.node)

        if source_item is None or target_item is None:
            return

        source = source_item.plug_items.get(connection.source.name)
        target = target_item.plug_items.get(connection.target.name)

        if source is None or target is None:
            return

        item = ConnectionItem(connection, source, target)

        self.addItem(item)
        self.connection_items[connection] = item

        source.update()
        target.update()

    def _remove_connection(self, connection: Connection) -> None:
        item = self.connection_items.pop(connection, None)

        if item is None:
            return

        item.detach()

        self.removeItem(item)

        item.source.update()
        item.target.update()

    @staticmethod
    def _place_unpositioned(graph: Graph) -> None:
        depth: dict[Node, int] = {}

        for node in graph.topological_order():
            depth[node] = max((depth.get(upstream, 0) + 1 for upstream in node.upstream_nodes()), default=0)

        rows: dict[int, int] = {}

        for node in graph:
            if node.metadata.get("position"):
                continue

            column = depth.get(node, 0)
            row = rows.get(column, 0)
            rows[column] = row + 1
            node.metadata["position"] = [column * (node_width + 80), row * 120]


class NodeSearch(QFrame):
    """The Tab menu: type to filter node types, Enter to create."""

    chosen = Signal(str)

    def __init__(self, parent: QWidget, registry: Any) -> None:
        super().__init__(parent, Qt.Popup)
        self.setObjectName("pane")
        self.registry = registry
        self.field = QLineEdit()
        self.field.setPlaceholderText("Search nodes…")
        self.list = QListWidget()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(self.field)
        layout.addWidget(self.list)

        self.resize(280, 320)
        self.field.textChanged.connect(self._filter)
        self.field.returnPressed.connect(self._accept)
        self.list.itemActivated.connect(lambda item: self._accept())
        self.field.installEventFilter(self)
        self._filter("")

    def eventFilter(self, watched: Any, event: Any) -> bool:
        if isinstance(event, QKeyEvent) and event.type() == QKeyEvent.KeyPress:
            if event.key() in (Qt.Key_Down, Qt.Key_Up):
                row = self.list.currentRow() + (1 if event.key() == Qt.Key_Down else -1)
                self.list.setCurrentRow(max(0, min(row, self.list.count() - 1)))
                return True

        return super().eventFilter(watched, event)

    def _filter(self, text: str) -> None:
        self.list.clear()
        words = text.lower().split()

        for node_class in sorted(self.registry.node_classes(), key=lambda cls: (cls.category, cls.type_name)):
            if node_class.type_name.startswith("bolt.graph_"):
                continue

            haystack = f"{node_class.type_name} {node_class.category} {node_class.description}".lower()

            if all(word in haystack for word in words):
                item = QListWidgetItem(f"{node_class.type_name}")
                item.setData(Qt.UserRole, node_class.type_name)
                item.setToolTip(node_class.description)
                self.list.addItem(item)

        self.list.setCurrentRow(0)

    def _accept(self) -> None:
        item = self.list.currentItem()

        if item is not None:
            self.chosen.emit(item.data(Qt.UserRole))

        self.close()


class GraphCanvas(QGraphicsView):
    def __init__(self, editor: NodeEditorView) -> None:
        super().__init__()
        self.editor = editor
        self.workspace = editor.workspace
        self.graph_scene = GraphScene(editor.workspace)
        self.setScene(self.graph_scene)
        self.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing)
        self.setViewportUpdateMode(QGraphicsView.BoundingRectViewportUpdate)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setAcceptDrops(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self._pan_start: QPointF | None = None
        self._drag_plug: PlugItem | None = None
        self._detached: tuple[Plug, Plug] | None = None
        self._drag_path: QGraphicsPathItem | None = None
        self._move_start: dict[str, tuple[float, float]] = {}
        self.grid_visible = True
        self.graph_scene.selectionChanged.connect(self._selection_changed)

    def set_grid_visible(self, visible: bool) -> None:
        self.grid_visible = visible
        self.viewport().update()

    def drawBackground(self, painter: QPainter, rect: QRectF) -> None:
        painter.fillRect(rect, theme.canvas)

        if not self.grid_visible:
            return

        scale = self.transform().m11()
        major = grid_size * grid_major

        if grid_size * scale >= 6:
            self._draw_grid_lines(painter, rect, grid_size, theme.grid_minor, skip=major)

        self._draw_grid_lines(painter, rect, major, theme.grid_major)

    @staticmethod
    def _draw_grid_lines(painter: QPainter, rect: QRectF, step: float, color: QColor, skip: float = 0.0) -> None:
        pen = QPen(color, 1.0)
        pen.setCosmetic(True)
        painter.setPen(pen)
        lines = []
        x = math.floor(rect.left() / step) * step

        while x <= rect.right():
            if not skip or x % skip:
                lines.append(QLineF(x, rect.top(), x, rect.bottom()))

            x += step

        y = math.floor(rect.top() / step) * step

        while y <= rect.bottom():
            if not skip or y % skip:
                lines.append(QLineF(rect.left(), y, rect.right(), y))

            y += step

        painter.drawLines(lines)

    def wheelEvent(self, event: QWheelEvent) -> None:
        factor = 1.0015 ** event.angleDelta().y()
        scale = self.transform().m11() * factor

        if 0.1 < scale < 4.0:
            self.scale(factor, factor)

    def set_plug_kind(self, plug: Plug, kind: PlugKind) -> None:
        document = self.graph_scene.document

        if document is not None:
            document.push(SetPlugKind(document, plug, kind))

    def layout_nodes(self, nodes: Iterable[Node] | None = None) -> None:
        """Arrange nodes in layers (Sugiyama), the selection if any, else the whole graph, keeping their top-left
        corner where it was. Undoable."""
        scene = self.graph_scene
        document = scene.document

        if document is None or scene.graph is None:
            return

        nodes = list(nodes) if nodes is not None else scene.selected_nodes()
        whole_graph = not nodes

        if whole_graph:
            nodes = list(scene.node_items)

        items = {node: scene.node_items[node] for node in nodes if node in scene.node_items}

        if len(items) < 2:
            return

        edges = []

        for connection in scene.graph.connections():
            source = items.get(connection.source.node)
            target = items.get(connection.target.node)

            if source is not None and target is not None:
                edges.append(LayoutEdge(connection.source.node, connection.target.node,
                                        source.plug_items[connection.source.name].pos().y(),
                                        target.plug_items[connection.target.name].pos().y()))

        positions = sugiyama_layout({node: (node_width, item.height) for node, item in items.items()}, edges,
                                    {node: item.pos().y() for node, item in items.items()},
                                    LayoutOptions(grid=grid_size))

        left = snap(min(item.pos().x() for item in items.values()))
        top = snap(min(item.pos().y() for item in items.values()))
        moves = {}

        for node, item in items.items():
            before = tuple(item.pos().toTuple())
            after = (left + positions[node][0], top + positions[node][1])

            if before != after:
                moves[node.name] = (before, after)

        if moves:
            document.push(MoveNodes(document, scene.graph, moves, f"Layout {len(items)} nodes"))

        if whole_graph:
            self.frame()

    def frame(self, nodes: Iterable[Node] | None = None) -> None:
        items = [self.graph_scene.node_items[node] for node in (nodes or []) if node in self.graph_scene.node_items]
        items = items or list(self.graph_scene.node_items.values())

        if not items:
            self.resetTransform()
            self.centerOn(0, 0)
            return

        rect = items[0].sceneBoundingRect()

        for item in items[1:]:
            rect = rect.united(item.sceneBoundingRect())

        self.fitInView(rect.adjusted(-80, -80, 80, 80), Qt.KeepAspectRatio)

        if self.transform().m11() > 1.2:
            self.resetTransform()
            self.centerOn(rect.center())

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self.workspace.active_node_editor = self.editor

        if event.button() == Qt.MiddleButton or (event.button() == Qt.LeftButton
                                                 and event.modifiers() & Qt.AltModifier):
            self._pan_start = event.position()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return

        if event.button() == Qt.LeftButton:
            item = self.itemAt(event.position().toPoint())

            if isinstance(item, PlugItem):
                self._start_connection(item)
                event.accept()
                return

            self._move_start = {node.name: tuple(node_item.pos().toTuple())
                                for node, node_item in self.graph_scene.node_items.items()}

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._pan_start is not None:
            delta = event.position() - self._pan_start
            self._pan_start = event.position()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - int(delta.x()))
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - int(delta.y()))
            return

        if self._drag_plug is not None:
            self._update_drag(event.position().toPoint())
            return

        self.graph_scene.snapping = bool(event.modifiers() & Qt.ShiftModifier and event.buttons() & Qt.LeftButton)

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._pan_start is not None:
            self._pan_start = None
            self.unsetCursor()
            return

        if self._drag_plug is not None:
            self._finish_connection(self.drop_target(event.position().toPoint()))
            return

        super().mouseReleaseEvent(event)
        self.graph_scene.snapping = False
        self._commit_moves()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = event.key()

        if event.matches(QKeySequence.Copy):
            self.copy()
        elif event.matches(QKeySequence.Paste):
            self.paste()
        elif key == Qt.Key_D and event.modifiers() & Qt.ControlModifier:
            self.copy()
            self.paste(offset=40)
        elif key in (Qt.Key_Delete, Qt.Key_Backspace):
            self.delete_selection()
        elif key == Qt.Key_Tab:
            self.open_search()
        elif key == Qt.Key_F:
            self.frame(self.graph_scene.selected_nodes())
        elif key == Qt.Key_G:
            self.editor.set_grid_visible(not self.grid_visible)
        elif key == Qt.Key_L:
            self.layout_nodes()
        elif key in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_I):
            self.enter_selected()
        elif key == Qt.Key_U:
            self.editor.go_up()
        elif key == Qt.Key_R:
            for node in self.graph_scene.selected_nodes()[:1]:
                self.graph_scene.toggle_flag(node, "displayed")
        elif key == Qt.Key_Q:
            for node in self.graph_scene.selected_nodes():
                self.graph_scene.toggle_flag(node, "disabled")
        else:
            super().keyPressEvent(event)

    def focusNextPrevChild(self, next_child: bool) -> bool:
        return False

    def contextMenuEvent(self, event: Any) -> None:
        item = self.itemAt(event.pos())
        plug_item = item if isinstance(item, PlugItem) else None

        while item is not None and not isinstance(item, NodeItem):
            item = item.parentItem()

        menu = QMenu(self)

        if plug_item is not None and plug_item.plug.kind is PlugKind.input:
            plug = plug_item.plug
            action = menu.addAction(f"Make {plug.spec.label} a parameter",
                                    lambda: self.set_plug_kind(plug, PlugKind.parameter))
            bind_icon(action, "tune")
            error = plug.kind_error(PlugKind.parameter)

            if error is not None:
                action.setEnabled(False)
                action.setToolTip(error)
                menu.setToolTipsVisible(True)

            menu.addSeparator()

        if isinstance(item, NodeItem):
            if not item.isSelected():
                self.graph_scene.clearSelection()
                item.setSelected(True)

            node = item.node
            menu.addAction("Display", lambda: self.graph_scene.toggle_flag(node, "displayed")).setCheckable(True)
            menu.actions()[-1].setChecked(node.displayed)
            menu.addAction("Disable", lambda: self.graph_scene.toggle_flag(node, "disabled")).setCheckable(True)
            menu.actions()[-1].setChecked(node.disabled)
            menu.addAction("Cook this node", lambda: self.editor.cook_nodes([node]))

            if node.child_graphs():
                menu.addAction("Enter subgraph", lambda: self.workspace.set_current_graph(node.child_graphs()[0]))

            menu.addSeparator()
            menu.addAction("Rename…", lambda: self.rename(node))
            menu.addAction("Copy", self.copy)
            menu.addAction("Duplicate", lambda: (self.copy(), self.paste(offset=40)))

            bind_icon(menu.addAction("Layout selection", self.layout_nodes), "account_tree")

            menu.addAction("Delete", self.delete_selection)
        else:
            position = self.mapToScene(event.pos())

            menu.addAction("Add node…", lambda: self.open_search(position))
            menu.addAction("Paste", lambda: self.paste(at=position))
            menu.addAction("Frame all", self.frame)

            bind_icon(menu.addAction("Layout all", lambda: (self.graph_scene.clearSelection(), self.layout_nodes())),
                      "account_tree")

            grid = menu.addAction("Show grid", lambda: self.editor.set_grid_visible(not self.grid_visible))
            grid.setCheckable(True)
            grid.setChecked(self.grid_visible)

        menu.exec(event.globalPos())

    def dragEnterEvent(self, event: Any) -> None:
        mime = event.mimeData()

        if mime.hasFormat(node_type_mime) or (mime.hasUrls() and any(
                url.toLocalFile().endswith(".bolt") for url in mime.urls())):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    dragMoveEvent = dragEnterEvent

    def dropEvent(self, event: Any) -> None:
        mime = event.mimeData()

        if mime.hasFormat(node_type_mime):
            type_name = bytes(mime.data(node_type_mime)).decode()
            self.create_node(type_name, self.mapToScene(event.position().toPoint()))
            event.acceptProposedAction()
            return

        for url in mime.urls():
            path = url.toLocalFile()

            if path.endswith(".bolt"):
                self.workspace.open(path)

        event.acceptProposedAction()

    def create_node(self, type_name: str, position: QPointF | None = None) -> None:
        document = self.graph_scene.document
        graph = self.graph_scene.graph

        if document is None or graph is None:
            return

        if position is None:
            position = self.mapToScene(self.viewport().rect().center())

        command = create_node_command(document, graph, type_name, (position.x() - node_width / 2, position.y()))
        document.push(command)
        node = graph.find_node(command.names[0])

        if node is not None:
            self.graph_scene.select_nodes([node])

    def open_search(self, position: QPointF | None = None) -> None:
        if position is None:
            position = self.mapToScene(self.mapFromGlobal(self.cursor().pos()))

        search = NodeSearch(self, self.workspace.registry)
        search.chosen.connect(lambda type_name: self.create_node(type_name, position))
        search.move(self.mapToGlobal(self.mapFromScene(position)))
        search.show()
        search.field.setFocus()

    def delete_selection(self) -> None:
        document = self.graph_scene.document
        graph = self.graph_scene.graph

        if document is None or graph is None:
            return

        nodes = self.graph_scene.selected_nodes()
        connections = [c for c in self.graph_scene.selected_connections()
                       if c.source.node not in nodes and c.target.node not in nodes]

        if not nodes and not connections:
            return

        document.undo_stack.beginMacro("Delete")

        for connection in connections:
            document.push(disconnect_command(document, connection.source, connection.target))

        if nodes:
            document.push(RemoveNodes(document, graph, nodes))

        document.undo_stack.endMacro()

    def copy(self) -> None:
        nodes = self.graph_scene.selected_nodes()

        if not nodes:
            return

        data = {"nodes": [node_to_dict(node) for node in nodes if node.removable],
                "connections": internal_connections(nodes)}

        mime = QMimeData()
        mime.setData(clipboard_mime, json.dumps(data).encode())
        mime.setText(json.dumps(data, indent=2))

        QApplication.clipboard().setMimeData(mime)

    def paste(self, offset: float = 0.0, at: QPointF | None = None) -> None:
        document = self.graph_scene.document
        graph = self.graph_scene.graph
        mime = QApplication.clipboard().mimeData()

        if document is None or graph is None or mime is None or not mime.hasFormat(clipboard_mime):
            return

        data = json.loads(bytes(mime.data(clipboard_mime)).decode())
        nodes = data.get("nodes", [])

        if not nodes:
            return

        positions = [node.get("metadata", {}).get("position", [0, 0]) for node in nodes]
        origin = (min(p[0] for p in positions), min(p[1] for p in positions))
        target = (at.x(), at.y()) if at is not None else (origin[0] + offset, origin[1] + offset)

        for node, position in zip(nodes, positions):
            node.setdefault("metadata", {})["position"] = [position[0] - origin[0] + target[0],
                                                           position[1] - origin[1] + target[1]]

        command = InsertNodes(document, graph, nodes, data.get("connections", []), text="Paste")
        document.push(command)

        self.graph_scene.select_nodes(graph.find_node(name) for name in command.names)

    def rename(self, node: Node) -> None:
        name, accepted = QInputDialog.getText(self, "Rename node", "Name", text=node.name)
        document = self.graph_scene.document

        if accepted and name and name != node.name and document is not None:
            try:
                document.push(RenameNode(document, node, name))
            except Exception as error:
                self.editor.show_message(str(error))

    def enter_selected(self) -> None:
        for node in self.graph_scene.selected_nodes():
            if node.child_graphs():
                self.workspace.set_current_graph(node.child_graphs()[0])
                return

    def _selection_changed(self) -> None:
        if self.graph_scene.document is self.workspace.current:
            self.workspace.select(self.graph_scene.selected_nodes())

    def _commit_moves(self) -> None:
        start = self._move_start
        self._move_start = {}
        document = self.graph_scene.document

        if not start or document is None:
            return

        moves = {}

        for node, item in self.graph_scene.node_items.items():
            before = start.get(node.name)
            after = tuple(item.pos().toTuple())

            if before is not None and before != after:
                moves[node.name] = (before, after)

        if moves:
            document.push(MoveNodes(document, self.graph_scene.graph, moves))

    def _start_connection(self, plug_item: PlugItem) -> None:
        plug = plug_item.plug

        self._detached = None

        if plug.kind is PlugKind.input and plug.connections:
            connection = plug.connections[-1]
            self._detached = (connection.source, plug)
            source_item = self.graph_scene.node_items[connection.source.node].plug_items[connection.source.name]
            existing = self.graph_scene.connection_items.get(connection)

            if existing is not None:
                existing.setVisible(False)

            plug_item = source_item

        self._drag_plug = plug_item
        self._drag_path = QGraphicsPathItem()
        self._drag_path.setPen(QPen(plug_item.color, 2, Qt.DashLine))
        self._drag_path.setZValue(10)
        self.graph_scene.addItem(self._drag_path)
        self._highlight_targets(plug_item.plug)
        self._update_drag(self.mapFromScene(plug_item.scene_anchor()))

    def drop_target(self, position: QPoint, radius: int = 12) -> PlugItem | None:
        """The compatible plug nearest to a view position while dragging a connection.

        Plugs are searched around the cursor rather than taken from itemAt(), whose topmost item there is the dragged
        curve itself."""
        area = QRect(position.x() - radius, position.y() - radius, radius * 2, radius * 2)
        candidates = [item for item in self.items(area) if isinstance(item, PlugItem) and item.highlighted]

        if not candidates:
            return None

        point = self.mapToScene(position)

        return min(candidates, key=lambda item: QLineF(item.scene_anchor(), point).length())

    def _update_drag(self, position: QPoint) -> None:
        target = self.drop_target(position)
        end = target.scene_anchor() if target is not None else self.mapToScene(position)
        pen = self._drag_path.pen()
        pen.setStyle(Qt.SolidLine if target is not None else Qt.DashLine)
        self._drag_path.setPen(pen)
        anchor = self._drag_plug.scene_anchor()

        if self._drag_plug.plug.kind is PlugKind.output:
            self._drag_path.setPath(curve(anchor, end))
        else:
            self._drag_path.setPath(curve(end, anchor))

    def _highlight_targets(self, plug: Plug | None) -> None:
        graph = self.graph_scene.graph

        for node_item in self.graph_scene.node_items.values():
            for item in node_item.plug_items.values():
                candidate = item.plug

                if plug is None or graph is None:
                    item.set_highlighted(False)
                elif plug.kind is PlugKind.output:
                    item.set_highlighted(graph.can_connect(plug, candidate))
                else:
                    item.set_highlighted(graph.can_connect(candidate, plug))

    def _finish_connection(self, item: PlugItem | None) -> None:
        start = self._drag_plug.plug
        detached = self._detached

        self.graph_scene.removeItem(self._drag_path)
        self._drag_path = None
        self._drag_plug = None
        self._detached = None
        self._highlight_targets(None)

        document = self.graph_scene.document
        graph = self.graph_scene.graph

        if detached is not None:
            existing = next((c for c in detached[1].connections if c.source is detached[0]), None)

            if existing is not None and existing in self.graph_scene.connection_items:
                self.graph_scene.connection_items[existing].setVisible(True)

        if document is None or graph is None:
            return

        target = item.plug if isinstance(item, PlugItem) else None

        if start.kind is PlugKind.output:
            source, destination = start, target
        else:
            source, destination = target, start

        valid = source is not None and destination is not None and graph.can_connect(source, destination)

        if detached is not None and valid and destination is detached[1]:
            return

        if detached is None and not valid:
            return

        document.undo_stack.beginMacro("Connect" if valid else "Disconnect")

        if detached is not None:
            document.push(disconnect_command(document, *detached))

        if valid:
            document.push(connect_command(document, source, destination))

        document.undo_stack.endMacro()


class NodeEditorView(View):
    view_type = "node_editor"
    label = "Node editor"
    description = "Edit the current graph: nodes, connections, flags and subgraphs."

    def __init__(self, workspace: Workspace, parent: QWidget | None = None) -> None:
        super().__init__(workspace, parent)

        self.canvas = GraphCanvas(self)
        self.breadcrumbs = QHBoxLayout()
        self.breadcrumbs.setSpacing(2)
        self.message = QLabel()
        self.message.setObjectName("muted")

        up = QToolButton()

        bind_icon(up, "arrow_upward")

        up.setToolTip("Go to the parent graph (U)")
        up.clicked.connect(self.go_up)

        self.grid_button = QToolButton()

        bind_icon(self.grid_button, "grid_4x4")

        self.grid_button.setCheckable(True)
        self.grid_button.setChecked(True)
        self.grid_button.setToolTip("Show the grid (G). Hold Shift while moving nodes to snap them to it.")
        self.grid_button.toggled.connect(self.set_grid_visible)

        bar = QHBoxLayout()
        bar.setContentsMargins(6, 4, 6, 4)
        bar.addWidget(up)
        bar.addLayout(self.breadcrumbs)
        bar.addStretch(1)
        bar.addWidget(self.message)

        layout_button = QToolButton()

        bind_icon(layout_button, "account_tree")

        layout_button.setToolTip("Layout the selected nodes, or the whole graph when none is selected (L)")
        layout_button.clicked.connect(lambda: self.canvas.layout_nodes())

        bar.addWidget(layout_button)
        bar.addWidget(self.grid_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addLayout(bar)
        layout.addWidget(self.canvas, 1)

        self.subscribe(events.GraphEvent, self.canvas.graph_scene.on_event)
        self._refresh_pending = False
        self.subscribe(CurrentDocumentChanged, lambda event: self.refresh())
        self.subscribe(CurrentGraphChanged, lambda event: self.refresh())
        self.subscribe(SelectionChanged, self._selection_changed)
        self.subscribe(NodeCreationRequested, self._creation_requested)

        if getattr(workspace, "active_node_editor", None) is None:
            workspace.active_node_editor = self

        theme.notifier().changed.connect(self._theme_changed)

        self._refresh_now()

    def _theme_changed(self) -> None:
        self.canvas.graph_scene.update()
        self.canvas.viewport().update()

    def refresh(self) -> None:
        """Show the current graph once control returns to the event loop: switching graphs deletes every item of the
        scene, and the switch is often requested by one of them (double-click), which must outlive its handler."""
        if not self._refresh_pending:
            self._refresh_pending = True
            QTimer.singleShot(0, self, self._refresh_now)

    def _refresh_now(self) -> None:
        self._refresh_pending = False
        document = self.workspace.current
        graph = document.current_graph if document is not None else None
        scene = self.canvas.graph_scene

        if scene.document is document and scene.graph is graph:
            return

        scene.show_graph(document, graph)

        self._update_breadcrumbs()

        if document is not None:
            scene.select_nodes(document.selection)

        QTimer.singleShot(0, self, self.canvas.frame)

    def set_grid_visible(self, visible: bool) -> None:
        self.canvas.set_grid_visible(visible)

        if self.grid_button.isChecked() != visible:
            self.grid_button.blockSignals(True)
            self.grid_button.setChecked(visible)
            self.grid_button.blockSignals(False)

    def save_state(self) -> dict[str, Any]:
        return {"grid": self.canvas.grid_visible}

    def restore_state(self, state: dict[str, Any]) -> None:
        self.set_grid_visible(bool(state.get("grid", True)))

    def go_up(self) -> None:
        graph = self.canvas.graph_scene.graph

        if graph is not None and graph.parent is not None:
            owner = graph.owner
            self.workspace.set_current_graph(graph.parent)
            self.workspace.select([owner])

    def cook_nodes(self, nodes: list[Node]) -> None:
        document = self.canvas.graph_scene.document

        if document is not None and nodes and nodes[0].graph is document.graph:
            document.live.cook(nodes)
        elif nodes:
            self.show_message("Only nodes of the top-level graph can be cooked on their own")

    def show_message(self, text: str) -> None:
        self.message.setText(text)

    def close_view(self) -> None:
        if getattr(self.workspace, "active_node_editor", None) is self:
            self.workspace.active_node_editor = None

        super().close_view()

    def _update_breadcrumbs(self) -> None:
        while self.breadcrumbs.count():
            widget = self.breadcrumbs.takeAt(0).widget()

            if widget is not None:
                widget.deleteLater()

        graph = self.canvas.graph_scene.graph
        chain = []

        while graph is not None:
            chain.append(graph)
            graph = graph.parent

        document = self.canvas.graph_scene.document

        for index, graph in enumerate(reversed(chain)):
            if index:
                separator = QLabel("›")
                separator.setObjectName("muted")
                self.breadcrumbs.addWidget(separator)

            button = QToolButton()
            button.setText(document.name if graph.owner is None and document is not None else graph.owner.name)
            button.clicked.connect(lambda checked=False, graph=graph: self.workspace.set_current_graph(graph))

            self.breadcrumbs.addWidget(button)

    def _selection_changed(self, event: SelectionChanged) -> None:
        scene = self.canvas.graph_scene

        if event.document is scene.document and set(scene.selected_nodes()) != set(event.nodes):
            scene.blockSignals(True)
            scene.select_nodes(event.nodes)
            scene.blockSignals(False)

    def _creation_requested(self, event: NodeCreationRequested) -> None:
        if self.workspace.active_node_editor is self:
            self.canvas.create_node(event.type_name, event.position)
