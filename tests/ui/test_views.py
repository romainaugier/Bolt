import logging

import pytest
from PySide6.QtCore import QPointF
from qt_support import pump, wait_until

import bolt
from bolt.core.plugs import PlugKind
from bolt.ui.commands import create_node_command
from bolt.ui.events import NodeCreationRequested
from bolt.ui.parameters import BoolEditor, LineEditor, NumberEditor, TextBlockEditor
from bolt.ui.views import JobsView, LogView, NodeEditorView, NodeLibraryView, ParametersView, VariablesView
from bolt.ui.views.node_editor import ConnectionItem, NodeItem


@pytest.fixture
def editor(workspace, document):
    view = NodeEditorView(workspace)
    view.resize(900, 600)
    view.show()
    pump()
    yield view
    view.close_view()


def add(document, type_name, name, values=None, position=(0, 0)):
    document.push(create_node_command(document, document.graph, type_name, position, values, name=name))
    return document.graph.node(name)


def test_node_editor_mirrors_graph(editor, document):
    scene = editor.canvas.graph_scene
    a = add(document, "values.int", "a", {"value": 2})
    total = add(document, "math.sum", "total", position=(250, 0))
    graph = document.graph
    graph.connect("a.result", "total.values")
    items = [item for item in scene.items() if isinstance(item, ConnectionItem)]
    assert len(items) == 1 and isinstance(scene.node_items[a], NodeItem)
    assert scene.node_items[total].pos().x() == 250

    scene.select_nodes([a])
    editor.canvas.delete_selection()
    assert graph.find_node("a") is None and a not in scene.node_items
    assert not [item for item in scene.items() if isinstance(item, ConnectionItem)]
    document.undo_stack.undo()
    restored = graph.node("a")
    assert restored in scene.node_items
    assert len([item for item in scene.items() if isinstance(item, ConnectionItem)]) == 1


def test_connection_drag(editor, document):
    scene = editor.canvas.graph_scene
    a = add(document, "values.int", "a")
    total = add(document, "math.add", "total", position=(250, 0))
    canvas = editor.canvas
    source_item = scene.node_items[a].plug_items["result"]
    target_item = scene.node_items[total].plug_items["a"]
    canvas._start_connection(source_item)
    assert target_item.highlighted and not scene.node_items[total].plug_items["result"].highlighted
    canvas._finish_connection(target_item)
    assert total["a"].connections and total["a"].connections[0].source is a["result"]

    canvas._start_connection(target_item)
    canvas._finish_connection(None)
    assert not total["a"].connections
    document.undo_stack.undo()
    assert total["a"].connections


def test_copy_paste_and_flags(editor, document):
    scene = editor.canvas.graph_scene
    a = add(document, "values.int", "a", {"value": 7})
    scene.select_nodes([a])
    editor.canvas.copy()
    editor.canvas.paste(offset=40)
    pasted = document.graph.node("a_1")
    assert pasted.get("value") == 7 and pasted.metadata["position"] == [40, 40]
    scene.toggle_flag(pasted, "displayed")
    assert pasted.displayed


def test_subgraph_navigation(editor, workspace, document):
    sub = add(document, "bolt.subgraph", "group")
    workspace.set_current_graph(sub.subgraph)
    pump()
    assert editor.canvas.graph_scene.graph is sub.subgraph
    assert {node.name for node in editor.canvas.graph_scene.node_items} == {"inputs", "outputs"}
    editor.go_up()
    assert wait_until(lambda: editor.canvas.graph_scene.graph is document.graph)
    assert editor.canvas.graph_scene.selected_nodes() == [sub]


def test_library_requests_creation(editor, workspace, document):
    library = NodeLibraryView(workspace)
    library.search.setText("math.sub")
    assert library.tree.topLevelItemCount() == 1
    workspace.active_node_editor = editor
    workspace.events.dispatch(NodeCreationRequested("math.subtract", QPointF(10, 10)))
    assert document.graph.find_node("subtract") is not None
    library.close_view()


def test_parameters_view_edits_values(workspace, document):
    view = ParametersView(workspace)
    node = add(document, "python.script", "script")
    node.add_plug(bolt.Input("count", "int", 1))
    node.add_plug(bolt.Parameter("enabled", "bool", True))
    workspace.select([node])
    pump()
    editors = {name: editor for name, (editor, _) in view.editors.items()}
    assert isinstance(editors["count"], NumberEditor)
    assert isinstance(editors["enabled"], BoolEditor)
    assert isinstance(editors["code"], TextBlockEditor)
    editors["count"].box.setValue(5)
    assert node.get("count") == 5
    view._toggle_expression(node.plug("count"), True)
    assert node.plug("count").is_expression and node.get("count") == "`5`"
    assert wait_until(lambda: isinstance(view.editors["count"][0], LineEditor))
    document.undo_stack.undo()
    assert node.get("count") == 5
    assert wait_until(lambda: isinstance(view.editors["count"][0], NumberEditor))
    view._add_plug("output", "result", "int")
    assert node.plug("result").spec.kind is PlugKind.output
    view._rename("renamed")
    assert node.name == "renamed"
    view.close_view()


def test_parameters_view_shows_errors(workspace, document):
    view = ParametersView(workspace)
    node = add(document, "flow.fail", "boom", {"message": "broken on purpose"})
    workspace.select([node])
    document.live.cook()
    assert wait_until(lambda: view.error.text() == "broken on purpose" and not view.error.isHidden())
    view.close_view()


def test_variables_view(workspace, document):
    view = VariablesView(workspace)
    view._set_graph("SHOT", "sh010")
    view._set_live("FRAME", 12)
    assert document.graph.variables["SHOT"] == "sh010"
    assert document.live.variables == {"FRAME": 12}
    assert wait_until(lambda: view.graph_table.table.rowCount() == 1 and view.live_table.table.rowCount() == 1)
    view._remove_graph("SHOT")
    assert "SHOT" not in document.graph.variables
    assert wait_until(lambda: view.graph_table.table.rowCount() == 0)
    view.close_view()


def test_log_view_collects_records(workspace, qapp):
    view = LogView(workspace)
    logging.getLogger("bolt").setLevel(logging.INFO)
    logging.getLogger("bolt.node").info("/node: hello from a node")
    logging.getLogger("bolt.node").debug("hidden at info level")
    assert wait_until(lambda: "hello from a node" in view.text.toPlainText())
    assert "hidden" not in view.text.toPlainText()
    view.close_view()


def test_jobs_view(workspace, document):
    view = JobsView(workspace)
    add(document, "flow.log", "say", {"message": "hello job"}).displayed = True
    view._submit()
    assert wait_until(lambda: len(view.items) == 1)
    job = next(iter(view.items))
    assert wait_until(lambda: view.items[job].text(1) == "succeeded", 30)
    assert wait_until(lambda: "hello job" in view.log.toPlainText(), 5)
    workspace.jobs.clear_finished()
    assert wait_until(lambda: not view.items)
    view.close_view()


def test_switching_plugs_between_input_and_parameter(editor, workspace, document):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from bolt.ui.commands import connect_command
    view = ParametersView(workspace)
    source = add(document, "math.add", "source", {"a": 2})
    value = add(document, "values.float", "value", {"value": 1.5}, position=(300, 0))
    workspace.select([value])
    pump()
    assert set(view.kind_buttons) == {"value"}
    assert view.kind_buttons["value"].toolTip().startswith("Make it an input")
    QTest.mouseClick(view.kind_buttons["value"], Qt.LeftButton)
    plug = value.plug("value")
    assert plug.kind is PlugKind.input and plug.raw == 1.5
    assert wait_until(lambda: "value" in editor.canvas.graph_scene.node_items[value].plug_items)

    document.push(connect_command(document, source.plug("result"), plug))
    assert wait_until(lambda: view.kind_buttons.get("value") is not None
                      and "disconnects" in view.kind_buttons["value"].toolTip())
    QTest.mouseClick(view.kind_buttons["value"], Qt.LeftButton)
    assert plug.kind is PlugKind.parameter and not plug.connections
    assert wait_until(lambda: "value" not in editor.canvas.graph_scene.node_items[value].plug_items)
    document.undo_stack.undo()
    assert plug.kind is PlugKind.input and plug.connections[0].source is source.plug("result")

    workspace.select([source])
    pump()
    assert set(view.kind_buttons) == {"a", "b"}
    editor.canvas.set_plug_kind(source.plug("a"), PlugKind.parameter)
    assert source.plug("a").kind is PlugKind.parameter
    assert wait_until(lambda: "a" not in editor.canvas.graph_scene.node_items[source].plug_items)
    view.close_view()
