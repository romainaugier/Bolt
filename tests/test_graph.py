import pytest

from bolt.core import events
from bolt.core.datatypes import DataType
from bolt.core.errors import (GraphError, InvalidConnectionError, InvalidNameError, InvalidValueError,
                              NodeNotFoundError, PlugNotFoundError, RegistryError, UnknownNodeTypeError,
                              UnknownTypeError)
from bolt.core.graph import Graph
from bolt.core.node import Node
from bolt.core.plugs import Input, Output, Parameter, PlugKind
from bolt.core.registry import Registry
from support import AddNode


def test_node_class_declaration_is_validated():
    with pytest.raises(TypeError, match="duplicate plug name"):
        class Duplicate(Node):
            inputs = (Input("x"),)
            outputs = (Output("x"),)

    with pytest.raises(TypeError, match="must be declared as Output"):
        class WrongKind(Node):
            outputs = (Input("x"),)

    with pytest.raises(InvalidNameError):
        class BadTypeName(Node):
            type_name = "not a type"


def test_default_names_are_unique(graph):
    names = [graph.create_node("test.add").name for _ in range(3)]
    assert names == ["add", "add_1", "add_2"]
    graph.remove_node("add_1")
    assert graph.create_node("test.add").name == "add_3"


def test_explicit_name_conflicts_raise(graph):
    graph.create_node("test.add", "sum")
    with pytest.raises(GraphError):
        graph.create_node("test.add", "sum")
    with pytest.raises(InvalidNameError):
        graph.create_node("test.add", "bad name")


def test_unknown_node_type(graph):
    with pytest.raises(UnknownNodeTypeError):
        graph.create_node("nope.nope")


def test_values_are_coerced_on_set(graph):
    node = graph.create_node("test.add", values={"a": "3", "scale": 2})
    assert node.get("a") == 3.0
    assert node.get("scale") == 2.0
    with pytest.raises(InvalidValueError):
        node.set("b", "not a number")
    with pytest.raises(InvalidValueError):
        node.set("result", 1.0)


def test_expressions_are_stored_raw(graph):
    node = graph.create_node("test.add", values={"a": "`FRAME * 2`"})
    assert node.plug("a").is_expression
    assert node.get("a") == "`FRAME * 2`"


def test_plug_lookup(graph):
    node = graph.create_node("test.add")
    assert node["a"] is node.plug("a")
    assert [plug.name for plug in node.input_plugs()] == ["a", "b"]
    assert [plug.name for plug in node.parameter_plugs()] == ["scale"]
    assert [plug.name for plug in node.output_plugs()] == ["result"]
    assert graph.plug("add.result").kind is PlugKind.output
    with pytest.raises(PlugNotFoundError):
        node.plug("missing")


def test_connect_validates_direction_and_cycles(graph):
    first = graph.create_node("test.add")
    second = graph.create_node("test.add")
    graph.connect(first["result"], second["a"])
    with pytest.raises(InvalidConnectionError, match="not an output"):
        graph.connect(second["a"], first["b"])
    with pytest.raises(InvalidConnectionError, match="cycle"):
        graph.connect(second["result"], first["a"])
    with pytest.raises(InvalidConnectionError, match="cycle"):
        graph.connect(first["result"], first["a"])


def test_connect_replaces_single_input_and_appends_to_multi(graph):
    a = graph.create_node("test.text")
    b = graph.create_node("test.text")
    concat = graph.create_node("test.concat")
    add = graph.create_node("test.add")
    graph.connect("text.result", "concat.parts")
    graph.connect("text_1.result", "concat.parts")
    assert [connection.source.node for connection in concat["parts"].connections] == [a, b]

    first = graph.create_node("test.add")
    second = graph.create_node("test.add")
    graph.connect(first["result"], add["a"])
    graph.connect(second["result"], add["a"])
    assert [connection.source.node for connection in add["a"].connections] == [second]
    assert not first["result"].connections


def test_connection_type_compatibility(registry):
    registry.register_type(DataType("image"))
    registry.register_type(DataType("mesh"))

    class MakeImage(Node):
        type_name = "test.make_image"
        outputs = (Output("image", "image"),)

    class UseMesh(Node):
        type_name = "test.use_mesh"
        inputs = (Input("mesh", "mesh"),)

    registry.register_node(MakeImage)
    registry.register_node(UseMesh)
    graph = Graph(registry)
    graph.create_node("test.make_image")
    graph.create_node("test.use_mesh")
    with pytest.raises(InvalidConnectionError, match="cannot connect"):
        graph.connect("make_image.image", "use_mesh.mesh")

    registry.register_conversion("image", "mesh", lambda image: ("mesh", image))
    connection = graph.connect("make_image.image", "use_mesh.mesh")
    assert connection.convert("img") == ("mesh", "img")


def test_builtin_conversions(graph):
    graph.create_node("test.text")
    graph.create_node("test.add")
    graph.create_node("test.concat")
    with pytest.raises(InvalidConnectionError):
        graph.connect("text.result", "add.a")
    connection = graph.connect("add.result", "concat.parts")
    assert connection.convert(1.5) == "1.5"


def test_remove_node_disconnects(graph):
    first = graph.create_node("test.add")
    second = graph.create_node("test.add")
    graph.connect(first["result"], second["a"])
    graph.remove_node(first)
    assert not second["a"].connections
    assert first.graph is None
    with pytest.raises(NodeNotFoundError):
        graph.node("add")


def test_rename_node(graph):
    node = graph.create_node("test.add")
    graph.create_node("test.add")
    node.name = "renamed"
    assert graph.node("renamed") is node
    assert node.path == "/renamed"
    with pytest.raises(GraphError):
        node.name = "add_1"
    assert [n.name for n in graph] == ["renamed", "add_1"]


def test_dynamic_plugs(graph):
    node = graph.create_node("test.add")
    plug = node.add_plug(Parameter("offset", "int", 3))
    assert plug.dynamic and node.get("offset") == 3
    with pytest.raises(GraphError):
        node.add_plug(Parameter("offset"))
    with pytest.raises(GraphError):
        node.remove_plug("a")
    with pytest.raises(UnknownTypeError):
        node.add_plug(Parameter("bad", "unknown_type"))
    node.remove_plug("offset")
    assert not node.has_plug("offset")


def test_topological_order(graph):
    c = graph.create_node("test.add", "c")
    a = graph.create_node("test.add", "a")
    b = graph.create_node("test.add", "b")
    graph.connect("a.result", "b.a")
    graph.connect("b.result", "c.a")
    assert graph.topological_order() == [a, b, c]


def test_graph_events(graph):
    received = []
    graph.events.subscribe(events.GraphEvent, lambda event: received.append(type(event).__name__))
    node = graph.create_node("test.add", values={"a": 1})
    other = graph.create_node("test.add")
    graph.connect(node["result"], other["a"])
    node.name = "first"
    node.disabled = True
    graph.disconnect(node["result"], other["a"])
    graph.set_variable("SHOT", "sh010")
    graph.remove_node(node)
    assert received == ["NodeAdded", "ValueChanged", "NodeAdded", "Connected", "NodeRenamed", "NodeChanged",
                        "Disconnected", "VariableChanged", "NodeRemoved"]


def test_registry_rejects_duplicates():
    registry = Registry()
    registry.register_node(AddNode)
    registry.register_node(AddNode)

    class OtherAdd(Node):
        type_name = "test.add"

    with pytest.raises(RegistryError):
        registry.register_node(OtherAdd)
    registry.register_node(OtherAdd, replace=True)
    assert registry.node_class("test.add") is OtherAdd
    with pytest.raises(RegistryError):
        registry.register_type(DataType("int"))


def test_can_connect(graph):
    first = graph.create_node("test.add")
    second = graph.create_node("test.add")
    text = graph.create_node("test.text")
    assert graph.can_connect(first["result"], second["a"])
    graph.connect(first["result"], second["a"])
    assert not graph.can_connect(second["result"], first["a"])
    assert not graph.can_connect(first["a"], second["b"])
    assert not graph.can_connect(text["result"], second["b"])
    assert not graph.can_connect(first["result"], first["b"])
