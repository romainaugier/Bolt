from qt_support import wait_until

from bolt.core.plugs import Input, Output
from bolt.core.serialization import node_to_dict
from bolt.ui.commands import (AddUserPlug, InsertNodes, MoveNodes, RemoveNodes, RemoveUserPlug, RenameNode, SetFlag,
                              SetValue, SetVariable, connect_command, create_node_command, disconnect_command,
                              internal_connections)


def build(document):
    graph = document.graph
    for name, value in (("a", 1), ("b", 2), ("c", 3)):
        document.push(create_node_command(document, graph, "values.int", (0, 0), {"value": value}, name=name))
    document.push(create_node_command(document, graph, "math.sum", (200, 0), name="total"))
    for name in ("a", "b", "c"):
        document.push(connect_command(document, graph.node(name)["result"], graph.node("total")["values"]))
    return graph


def sources(plug):
    return [connection.source.node.name for connection in plug.connections]


def test_create_and_connect_undo(document):
    graph = build(document)
    assert sources(graph.node("total")["values"]) == ["a", "b", "c"]
    assert graph.node("a").metadata["position"] == [0.0, 0.0]
    stack = document.undo_stack
    stack.undo()
    assert sources(graph.node("total")["values"]) == ["a", "b"]
    stack.undo()
    stack.undo()
    stack.undo()
    assert graph.find_node("total") is None
    while stack.canRedo():
        stack.redo()
    assert sources(graph.node("total")["values"]) == ["a", "b", "c"]
    assert graph.pull("total.result") == 6.0


def test_remove_restores_connection_order(document):
    graph = build(document)
    document.push(RemoveNodes(document, graph, [graph.node("b")]))
    assert sources(graph.node("total")["values"]) == ["a", "c"]
    document.undo_stack.undo()
    assert sources(graph.node("total")["values"]) == ["a", "b", "c"]
    assert graph.node("b").get("value") == 2


def test_disconnect_and_single_input_replacement(document):
    graph = build(document)
    document.push(disconnect_command(document, graph.node("b")["result"], graph.node("total")["values"]))
    assert sources(graph.node("total")["values"]) == ["a", "c"]
    document.undo_stack.undo()
    assert sources(graph.node("total")["values"]) == ["a", "b", "c"]

    document.push(create_node_command(document, graph, "math.add", name="add"))
    document.push(connect_command(document, graph.node("a")["result"], graph.node("add")["a"]))
    document.push(connect_command(document, graph.node("b")["result"], graph.node("add")["a"]))
    assert sources(graph.node("add")["a"]) == ["b"]
    document.undo_stack.undo()
    assert sources(graph.node("add")["a"]) == ["a"]


def test_set_value_merges_continuous_edits_only(document):
    graph = build(document)
    plug = graph.node("a")["value"]
    count = document.undo_stack.count()
    for value in (5, 6, 7):
        document.push(SetValue(document, plug, value))
    assert document.undo_stack.count() == count + 1
    document.push(SetValue(document, plug, "`FRAME`"))
    document.push(SetValue(document, plug, "`FRAME + 1`"))
    assert document.undo_stack.count() == count + 3
    document.undo_stack.undo()
    document.undo_stack.undo()
    assert plug.raw == 7
    document.undo_stack.undo()
    assert plug.raw == 1


def test_rename_flags_move(document):
    graph = build(document)
    node = graph.node("a")
    document.push(RenameNode(document, node, "first"))
    assert graph.node("first") is node
    document.push(SetFlag(document, node, "displayed", True))
    document.push(MoveNodes(document, graph, {"first": ((0, 0), (50, 60))}))
    assert node.displayed and node.metadata["position"] == [50, 60]
    for _ in range(3):
        document.undo_stack.undo()
    assert node.name == "a" and not node.displayed and node.metadata["position"] == [0, 0]


def test_user_plugs_on_script_and_subgraph(document):
    graph = document.graph
    document.push(create_node_command(document, graph, "python.script", name="script"))
    script = graph.node("script")
    document.push(AddUserPlug(document, script, Input("x", "int")))
    document.push(SetValue(document, script["x"], 4))
    document.push(AddUserPlug(document, script, Output("y", "int")))
    document.push(SetValue(document, script["code"], "y = x * 10"))
    assert graph.pull("script.y") == 40
    document.push(RemoveUserPlug(document, script, "x"))
    assert not script.has_plug("x")
    document.undo_stack.undo()
    assert script.get("x") == 4

    document.push(create_node_command(document, graph, "bolt.subgraph", name="group"))
    group = graph.node("group")
    document.push(AddUserPlug(document, group, Input("value", "float")))
    assert group.subgraph.node("inputs").has_plug("value")
    document.undo_stack.undo()
    assert not group.has_plug("value") and not group.subgraph.node("inputs").has_plug("value")


def test_commands_inside_subgraphs(document):
    graph = document.graph
    document.push(create_node_command(document, graph, "bolt.subgraph", name="group"))
    inner = graph.node("group").subgraph
    document.push(create_node_command(document, inner, "values.int", name="inner_value"))
    assert inner.find_node("inner_value") is not None
    document.undo_stack.undo()
    assert inner.find_node("inner_value") is None


def test_paste_renames_and_keeps_internal_connections(document):
    graph = build(document)
    nodes = [graph.node("a"), graph.node("total")]
    command = InsertNodes(document, graph, [node_to_dict(node) for node in nodes], internal_connections(nodes))
    document.push(command)
    assert command.names == ["a_1", "total_1"]
    assert sources(graph.node("total_1")["values"]) == ["a_1"]
    document.undo_stack.undo()
    assert graph.find_node("a_1") is None


def test_variables(document):
    graph = document.graph
    document.push(SetVariable(document, graph, "SHOT", "sh010"))
    document.push(SetVariable(document, graph, "SHOT", "sh020"))
    assert graph.variables["SHOT"] == "sh020"
    document.undo_stack.undo()
    assert graph.variables["SHOT"] == "sh010"
    document.undo_stack.undo()
    assert "SHOT" not in graph.variables
    document.undo_stack.redo()
    document.push(SetVariable(document, graph, "SHOT", None, remove=True))
    assert "SHOT" not in graph.variables
    document.undo_stack.undo()
    assert graph.variables["SHOT"] == "sh010"


def test_structural_commands_wait_for_running_cook(document):
    graph = document.graph
    document.push(create_node_command(document, graph, "flow.sleep", values={"seconds": 0.3}, name="slow"))
    document.live.cook()
    assert wait_until(lambda: document.live.busy, 5)
    document.push(create_node_command(document, graph, "values.int", name="later"))
    assert graph.find_node("later") is None
    assert wait_until(lambda: graph.find_node("later") is not None, 5)
