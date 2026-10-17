"""Real mouse and keyboard input on the editor widgets.

Edits made through a widget often rebuild the view that owns it. These tests click and type like a user would, so a
widget destroyed while Qt is still handling its signal crashes the test run instead of going unnoticed."""

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QCheckBox, QLineEdit, QToolButton
from qt_support import pump, wait_until

import bolt
from bolt.ui.commands import create_node_command
from bolt.ui.views import NodeEditorView, ParametersView, VariablesView


@pytest.fixture
def parameters(workspace, document):
    view = ParametersView(workspace)
    view.resize(500, 700)
    view.show()
    pump()
    yield view
    view.close_view()


def add(document, type_name, name, values=None, position=(0, 0)):
    document.push(create_node_command(document, document.graph, type_name, position, values, name=name))
    return document.graph.node(name)


def visible(view, widget_type, predicate):
    assert wait_until(lambda: any(predicate(widget) for widget in view.findChildren(widget_type)
                                  if widget.isVisible()))
    return next(widget for widget in view.findChildren(widget_type) if widget.isVisible() and predicate(widget))


@pytest.mark.parametrize("label, flag", [("Disable", "disabled"), ("Display", "displayed")])
def test_flag_checkboxes(workspace, document, parameters, label, flag):
    node = add(document, "values.int", "value")
    workspace.select([node])
    for expected in (True, False, True):
        box = visible(parameters, QCheckBox, lambda widget: widget.text() == label)
        QTest.mouseClick(box, Qt.LeftButton)
        pump()
        assert getattr(node, flag) is expected
        assert box.isChecked() is expected


def test_flag_changes_elsewhere_update_the_checkbox(workspace, document, parameters):
    node = add(document, "values.int", "value")
    workspace.select([node])
    box = visible(parameters, QCheckBox, lambda widget: widget.text() == "Disable")
    node.disabled = True
    assert box.isChecked()


def test_expression_toggle_button(workspace, document, parameters):
    node = add(document, "values.int", "value", {"value": 3})
    workspace.select([node])
    toggle = visible(parameters, QToolButton, lambda widget: widget.text() == "ƒ")
    QTest.mouseClick(toggle, Qt.LeftButton)
    pump()
    assert node.plug("value").is_expression and node.get("value") == "`3`"
    toggle = visible(parameters, QToolButton, lambda widget: widget.text() == "ƒ")
    QTest.mouseClick(toggle, Qt.LeftButton)
    pump()
    assert not node.plug("value").is_expression


def test_rename_field(workspace, document, parameters):
    node = add(document, "values.int", "value")
    workspace.select([node])
    field = visible(parameters, QLineEdit, lambda widget: widget.text() == "value")
    field.setFocus()
    field.selectAll()
    QTest.keyClicks(field, "renamed")
    QTest.keyClick(field, Qt.Key_Return)
    pump()
    assert node.name == "renamed"
    assert visible(parameters, QLineEdit, lambda widget: widget.text() == "renamed")


def test_value_field(workspace, document, parameters):
    node = add(document, "values.string", "text")
    workspace.select([node])
    field = visible(parameters, QLineEdit, lambda widget: widget.text() == "" and widget.objectName() != "heading")
    field.setFocus()
    QTest.keyClicks(field, "$(SHOT)")
    QTest.keyClick(field, Qt.Key_Return)
    pump()
    assert node.get("value") == "$(SHOT)" and node.plug("value").is_expression


def test_user_plug_buttons(workspace, document, parameters):
    node = add(document, "python.script", "script")
    node.add_plug(bolt.Input("x", "int"))
    workspace.select([node])
    remove = visible(parameters, QToolButton, lambda widget: widget.toolTip() == "Remove x")
    QTest.mouseClick(remove, Qt.LeftButton)
    pump()
    assert not node.has_plug("x")
    name = visible(parameters, QLineEdit, lambda widget: widget.placeholderText() == "name")
    QTest.keyClicks(name, "y")
    add_button = visible(parameters, QToolButton, lambda widget: widget.toolTip() == "Add the plug")
    QTest.mouseClick(add_button, Qt.LeftButton)
    pump()
    assert node.has_plug("y")


def test_double_click_enters_subgraph(workspace, document):
    editor = NodeEditorView(workspace)
    editor.resize(900, 600)
    editor.show()
    pump()
    group = add(document, "bolt.subgraph", "group")
    canvas = editor.canvas
    item = canvas.graph_scene.node_items[group]
    canvas.centerOn(item)
    point = canvas.mapFromScene(item.mapToScene(item.boundingRect().center()))
    QTest.mouseDClick(canvas.viewport(), Qt.LeftButton, Qt.NoModifier, point)
    assert wait_until(lambda: canvas.graph_scene.graph is group.subgraph)
    QTest.keyClick(canvas, Qt.Key_U)
    assert wait_until(lambda: canvas.graph_scene.graph is document.graph)
    assert canvas.graph_scene.selected_nodes() == [group]
    editor.close_view()


def test_header_flags(workspace, document):
    editor = NodeEditorView(workspace)
    editor.resize(900, 600)
    editor.show()
    pump()
    node = add(document, "values.int", "value")
    canvas = editor.canvas
    item = canvas.graph_scene.node_items[node]
    canvas.centerOn(item)
    for rect, flag in ((item.disable_flag_rect(), "disabled"), (item.display_flag_rect(), "displayed")):
        point = canvas.mapFromScene(item.mapToScene(rect.center()))
        QTest.mouseClick(canvas.viewport(), Qt.LeftButton, Qt.NoModifier, point)
        pump()
        assert getattr(node, flag)
    editor.close_view()


def test_variable_table_edit(workspace, document):
    view = VariablesView(workspace)
    view.resize(500, 400)
    view.show()
    document.graph.set_variable("SHOT", "sh010")
    assert wait_until(lambda: view.graph_table.table.rowCount() == 1)
    table = view.graph_table.table
    table.editItem(table.item(0, 1))
    pump()
    editor = table.findChild(QLineEdit)
    assert editor is not None and editor.isVisible()
    editor.selectAll()
    QTest.keyClicks(editor, "sh020")
    QTest.keyClick(editor, Qt.Key_Return)
    assert wait_until(lambda: document.graph.variables["SHOT"] == "sh020")
    assert wait_until(lambda: table.item(0, 1) is not None and table.item(0, 1).text() == "sh020")
    view.close_view()


@pytest.fixture
def wired(workspace, document):
    editor = NodeEditorView(workspace)
    editor.resize(1000, 600)
    editor.show()
    pump()
    add(document, "values.int", "first", position=(0, 0))
    add(document, "values.string", "text", position=(0, 140))
    add(document, "math.add", "add", position=(260, 20))
    add(document, "math.add", "other", position=(260, 160))
    canvas = editor.canvas
    canvas.resetTransform()
    canvas.centerOn(220, 120)
    pump()
    yield canvas
    editor.close_view()


def plug_point(canvas, document, node, plug, offset=(0, 0)):
    item = canvas.graph_scene.node_items[document.graph.node(node)].plug_items[plug]
    return canvas.mapFromScene(item.scene_anchor()) + QPoint(*offset)


def mouse_drag(canvas, start, end, steps=8):
    viewport = canvas.viewport()
    QTest.mousePress(viewport, Qt.LeftButton, Qt.NoModifier, start)
    for step in range(1, steps + 1):
        QTest.mouseMove(viewport, start + (end - start) * step / steps)
    QTest.mouseRelease(viewport, Qt.LeftButton, Qt.NoModifier, end)
    pump()


def sources(document, node, plug):
    return [connection.source.path for connection in document.graph.node(node).plug(plug).connections]


def test_drag_output_to_input(wired, document):
    mouse_drag(wired, plug_point(wired, document, "first", "result"), plug_point(wired, document, "add", "a"))
    assert sources(document, "add", "a") == ["/first.result"]
    document.undo_stack.undo()
    assert sources(document, "add", "a") == []


def test_drag_input_to_output(wired, document):
    mouse_drag(wired, plug_point(wired, document, "add", "b"), plug_point(wired, document, "first", "result"))
    assert sources(document, "add", "b") == ["/first.result"]


def test_drop_near_a_plug(wired, document):
    mouse_drag(wired, plug_point(wired, document, "first", "result"), plug_point(wired, document, "add", "a", (7, -6)))
    assert sources(document, "add", "a") == ["/first.result"]


def test_drop_on_incompatible_plug_or_empty_space_does_nothing(wired, document):
    mouse_drag(wired, plug_point(wired, document, "text", "result"), plug_point(wired, document, "add", "a"))
    mouse_drag(wired, plug_point(wired, document, "first", "result"), plug_point(wired, document, "add", "a", (0, 80)))
    assert sources(document, "add", "a") == []
    assert document.undo_stack.count() == 4


def test_drag_existing_connection_away_and_to_another_input(wired, document):
    mouse_drag(wired, plug_point(wired, document, "first", "result"), plug_point(wired, document, "add", "a"))
    mouse_drag(wired, plug_point(wired, document, "add", "a"), plug_point(wired, document, "other", "b"))
    assert sources(document, "add", "a") == [] and sources(document, "other", "b") == ["/first.result"]
    mouse_drag(wired, plug_point(wired, document, "other", "b"), plug_point(wired, document, "other", "b", (90, 90)))
    assert sources(document, "other", "b") == []
    document.undo_stack.undo()
    assert sources(document, "other", "b") == ["/first.result"]
    connection = document.graph.node("other").plug("b").connections[0]
    assert wired.graph_scene.connection_items[connection].isVisible()
