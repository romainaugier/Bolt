import pytest

from bolt.core import events
from bolt.core.datatypes import DataType
from bolt.core.errors import GraphError, InvalidConnectionError
from bolt.core.node import Node
from bolt.core.plugs import Input, Output, PlugKind
from bolt.core.serialization import dumps, graph_to_dict, loads
from support import cooks


class Blob:
    pass


class BlobNode(Node):
    type_name = "test.blob"
    inputs = (Input("blob", "blob"), Input("count", "int", 2))
    outputs = (Output("result", "any"),)

    def cook(self, ctx) -> None:
        ctx.set("result", (ctx.get("blob"), ctx.get("count")))


@pytest.fixture
def blob_registry(registry):
    registry.register_type(DataType("blob", Blob))
    registry.register_node(BlobNode)
    return registry


def test_parameter_promoted_to_input_can_be_connected(graph):
    graph.create_node("test.add", "source", values={"a": 2})
    target = graph.create_node("test.add", "target", values={"a": 1, "scale": 3})
    with pytest.raises(InvalidConnectionError):
        graph.connect("source.result", "target.scale")
    received = []
    graph.events.subscribe(events.PlugKindChanged, received.append)

    plug = target.set_plug_kind("scale", PlugKind.input)
    assert plug.kind is PlugKind.input and plug.promoted and received[-1].plug is plug
    assert [plug.name for plug in target.input_plugs()] == ["a", "b", "scale"]
    assert graph.pull("target.result") == 3.0
    graph.connect("source.result", "target.scale")
    assert graph.pull("target.result") == 2.0

    graph.disconnect_plug(plug)
    assert graph.pull("target.result") == 3.0
    target.set_plug_kind("scale", PlugKind.parameter)
    assert not plug.promoted and list(target.parameter_plugs()) == [plug]


def test_input_made_parameter_keeps_its_value_and_recooks(graph):
    node = graph.create_node("test.add", "node", values={"a": 4})
    assert graph.pull("node.result") == 4.0
    cooks.clear()
    node.set_plug_kind("a", PlugKind.parameter)
    assert graph.pull("node.result") == 4.0 and cooks.names == ["node"]
    node.set("a", "`2 * 5`")
    assert graph.pull("node.result") == 10.0
    graph.create_node("test.add", "source")
    with pytest.raises(InvalidConnectionError):
        graph.connect("source.result", "node.a")


def test_rules(graph, blob_registry):
    blob = graph.create_node("test.blob", "blob")
    concat = graph.create_node("test.concat", "concat")
    add = graph.create_node("test.add", "add")
    graph.create_node("test.add", "source")
    graph.connect("source.result", "add.a")
    with pytest.raises(GraphError, match="cannot be edited"):
        blob.set_plug_kind("blob", PlugKind.parameter)
    assert blob.plug("count").kind_error(PlugKind.parameter) is None
    with pytest.raises(GraphError, match="several connections"):
        concat.set_plug_kind("parts", PlugKind.parameter)
    with pytest.raises(GraphError, match="disconnect"):
        add.set_plug_kind("a", PlugKind.parameter)
    with pytest.raises(GraphError, match="output"):
        add.set_plug_kind("result", PlugKind.input)
    with pytest.raises(GraphError, match="output"):
        add.set_plug_kind("scale", PlugKind.output)


def test_kinds_are_saved(graph, registry):
    graph.create_node("test.add", "source", values={"a": 5})
    target = graph.create_node("test.add", "target", values={"b": 7})
    target.set_plug_kind("scale", PlugKind.input)
    target.set_plug_kind("b", PlugKind.parameter)
    graph.connect("source.result", "target.scale")
    assert graph_to_dict(graph)["nodes"][1]["kinds"] == {"b": "parameter", "scale": "input"}
    assert "kinds" not in graph_to_dict(graph)["nodes"][0]

    loaded = loads(dumps(graph), registry)
    node = loaded.node("target")
    assert node.plug("scale").kind is PlugKind.input and node.plug("b").kind is PlugKind.parameter
    assert node.plug("scale").connections and loaded.pull("target.result") == 35.0


def test_passthrough_and_subgraphs_use_declared_inputs(graph):
    node = graph.create_node("test.add", "node", values={"a": 6})
    node.set_plug_kind("a", PlugKind.parameter)
    node.disabled = True
    assert graph.pull("node.result") == 6.0

    sub = graph.create_node("bolt.subgraph", "sub")
    sub.add_subgraph_input("value", "float", 1.5)
    sub.add_subgraph_output("doubled", "float")
    sub.subgraph.create_node("test.add", "twice", values={"scale": 2})
    sub.subgraph.connect("inputs.value", "twice.a")
    sub.subgraph.connect("twice.result", "outputs.doubled")
    sub.set_plug_kind("value", PlugKind.parameter)
    sub.set("value", 4)
    assert graph.pull("sub.doubled") == 8.0
