import pytest
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QColor, QImage, QMouseEvent, QPainter
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QStyleOptionGraphicsItem
from qt_support import pump

from bolt.core import events
from bolt.ui import theme
from bolt.ui.commands import create_node_command
from bolt.ui.views import NodeEditorView
from bolt.ui.views.node_editor import grid_size, header_height, node_width


@pytest.fixture
def editor(workspace, document):
    view = NodeEditorView(workspace)
    view.resize(900, 600)
    view.show()
    pump()
    yield view
    view.close_view()


def add(document, name, position):
    document.push(create_node_command(document, document.graph, "math.add", position, name=name))
    return document.graph.node(name)


def render(item) -> QImage:
    image = QImage(int(node_width) + 20, int(item.height) + 40, QImage.Format_ARGB32)
    image.fill(theme.canvas)
    painter = QPainter(image)
    painter.translate(10, 10)
    item.paint(painter, QStyleOptionGraphicsItem(), None)
    painter.end()
    return image


def same(first: QColor, second: QColor) -> bool:
    return all(abs(a - b) <= 2 for a, b in zip(first.getRgb()[:3], second.getRgb()[:3]))


def test_header_is_filled_down_to_the_body(editor, document):
    node = add(document, "node", (0, 0))
    item = editor.canvas.graph_scene.node_items[node]
    image = render(item)
    for x in (10 + node_width / 2, 10 + 4, 10 + node_width - 4):
        for y in (10 + header_height - 1, 10 + header_height - 4, 10 + header_height / 2 + 6):
            assert same(image.pixelColor(int(x), int(y)), item.color), (x, y)
    assert same(image.pixelColor(int(10 + node_width / 2), int(10 + header_height + 2)), theme.node_body)
    assert same(image.pixelColor(10, 10), theme.canvas)


def test_disabled_nodes_are_dimmed_not_transparent(editor, document):
    node = add(document, "node", (0, 0))
    node.disabled = True
    item = editor.canvas.graph_scene.node_items[node]
    header = render(item).pixelColor(int(10 + node_width / 2), int(10 + header_height - 2))
    assert not same(header, item.color) and not same(header, theme.canvas)


def drag(canvas, item, delta, modifiers=Qt.NoModifier):
    start = canvas.mapFromScene(item.mapToScene(30, 10))
    end = start + delta
    QTest.mousePress(canvas.viewport(), Qt.LeftButton, Qt.NoModifier, start)
    move = QMouseEvent(QEvent.MouseMove, QPointF(end), QPointF(canvas.viewport().mapToGlobal(end)), Qt.NoButton,
                       Qt.LeftButton, modifiers)
    QApplication.sendEvent(canvas.viewport(), move)
    QTest.mouseRelease(canvas.viewport(), Qt.LeftButton, Qt.NoModifier, end)
    pump()


def test_shift_drag_snaps_to_the_grid(editor, document):
    canvas = editor.canvas
    canvas.resetTransform()
    node = add(document, "node", (3, 7))
    other = add(document, "other", (200, 13))
    item = canvas.graph_scene.node_items[node]
    canvas.centerOn(item)
    pump()

    drag(canvas, item, QPoint(37, 23))
    assert item.pos().toTuple() == (40.0, 30.0)
    assert node.metadata["position"] == [40.0, 30.0]

    canvas.graph_scene.select_nodes([node, other])
    drag(canvas, item, QPoint(11, 26), Qt.ShiftModifier)
    for moved in (node, other):
        x, y = moved.metadata["position"]
        assert x % grid_size == 0 and y % grid_size == 0, moved.name
    assert node.metadata["position"] == [60.0, 60.0]

    document.undo_stack.undo()
    assert node.metadata["position"] == [40.0, 30.0] and other.metadata["position"] == [200.0, 13.0]

    node.metadata["position"] = [5.0, 5.0]
    document.graph.events.emit(events.NodeChanged, document.graph, node, "position")
    assert item.pos().toTuple() == (5.0, 5.0)


def test_grid_toggle(editor):
    canvas = editor.canvas
    assert canvas.grid_visible and editor.grid_button.isChecked()
    QTest.mouseClick(editor.grid_button, Qt.LeftButton)
    assert not canvas.grid_visible
    assert editor.save_state() == {"grid": False}
    QTest.keyClick(canvas, Qt.Key_G)
    assert canvas.grid_visible and editor.grid_button.isChecked()
    editor.restore_state({"grid": False})
    assert not canvas.grid_visible and not editor.grid_button.isChecked()
    image = canvas.grab().toImage()
    editor.restore_state({"grid": True})
    gridded = canvas.grab().toImage()
    assert image != gridded


def test_layout_shortcut(editor, document):
    from bolt.ui.commands import connect_command
    graph = document.graph
    nodes = [add(document, name, position) for name, position in
             (("first", (300, 200)), ("second", (-200, 50)), ("third", (40, -300)), ("alone", (500, 500)))]
    document.push(connect_command(document, graph.node("first").plug("result"), graph.node("second").plug("a")))
    document.push(connect_command(document, graph.node("second").plug("result"), graph.node("third").plug("a")))
    canvas = editor.canvas
    canvas.setFocus()
    positions = {node.name: list(node.metadata["position"]) for node in nodes}

    canvas.graph_scene.select_nodes([graph.node("first"), graph.node("second")])
    QTest.keyClick(canvas, Qt.Key_L)
    first, second = graph.node("first").metadata["position"], graph.node("second").metadata["position"]
    assert second[0] > first[0] and first[1] + 40 == second[1] + 40
    assert graph.node("third").metadata["position"] == positions["third"]
    assert graph.node("alone").metadata["position"] == positions["alone"]
    assert document.undo_stack.undoText() == "Layout 2 nodes"

    canvas.graph_scene.clearSelection()
    QTest.keyClick(canvas, Qt.Key_L)
    x = [graph.node(name).metadata["position"][0] for name in ("first", "second", "third")]
    assert x[0] < x[1] < x[2]
    assert all(value % grid_size == 0 for node in nodes for value in node.metadata["position"])
    document.undo_stack.undo()
    document.undo_stack.undo()
    assert {node.name: list(node.metadata["position"]) for node in nodes} == positions
