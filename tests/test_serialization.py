import json

import pytest

from bolt.core.errors import SerializationError
from bolt.core.graph import Graph
from bolt.core.node import Node
from bolt.core.plugs import Output, Parameter
from bolt.core.registry import Registry
from bolt.core.serialization import MissingNode, dumps, graph_to_dict, load_graph, loads, save_graph
from support import test_nodes


def build(graph):
    graph.set_variable("SHOT", "sh010")
    graph.create_node("test.add", "first", values={"a": 1, "b": "`FRAME`"})
    second = graph.create_node("test.add", "second")
    second.metadata["position"] = [120, 40]
    second.disabled = True
    graph.create_node("test.text", "label", values={"text": "$(SHOT)"})
    concat = graph.create_node("test.concat", "concat")
    concat.add_plug(Parameter("separator", "string", "-"))
    graph.connect("first.result", "second.a")
    graph.connect("label.result", "concat.parts")
    graph.connect("first.result", "concat.parts")
    sub = graph.create_node("bolt.subgraph", "group")
    sub.add_subgraph_input("value", "float")
    sub.add_subgraph_output("result", "float")
    sub.subgraph.create_node("test.add", "inner", values={"scale": 4})
    sub.subgraph.connect("inputs.value", "inner.a")
    sub.subgraph.connect("inner.result", "outputs.result")
    graph.connect("first.result", "group.value")
    return graph


def test_round_trip(graph, registry):
    build(graph)
    text = dumps(graph)
    loaded = loads(text, registry)
    assert graph_to_dict(loaded) == graph_to_dict(graph)
    assert loaded.variables == {"SHOT": "sh010"}
    assert loaded.node("first").get("b") == "`FRAME`"
    assert loaded.node("second").disabled
    assert loaded.node("second").metadata == {"position": [120, 40]}
    assert loaded.node("concat").plug("separator").dynamic
    assert [c.source.node.name for c in loaded.node("concat")["parts"].connections] == ["label", "first"]
    assert loaded.node("group").subgraph.node("inner").get("scale") == 4.0
    assert loaded.pull("group.result", variables={"FRAME": 1}) == 8.0


def test_file_round_trip(graph, registry, tmp_path):
    build(graph)
    path = tmp_path / "nested" / "graph.bolt"
    save_graph(graph, path)
    assert json.loads(path.read_text())["format"] == "bolt.graph"
    assert not (tmp_path / "nested" / "graph.bolt.tmp").exists()
    loaded = load_graph(path, registry)
    assert len(loaded) == len(graph)


def test_rejects_foreign_files(registry):
    with pytest.raises(SerializationError):
        loads("{}", registry)
    with pytest.raises(SerializationError):
        loads("not json", registry)
    with pytest.raises(SerializationError, match="newer"):
        loads(json.dumps({"format": "bolt.graph", "version": 99, "graph": {}}), registry)


def test_missing_node_types_are_preserved(graph, registry):
    build(graph)
    text = dumps(graph)
    partial = Registry()
    for node_class in test_nodes:
        if node_class.type_name != "test.text":
            partial.register_node(node_class)
    loaded = loads(text, partial)
    missing = loaded.node("label")
    assert isinstance(missing, MissingNode)
    assert missing.missing_type == "test.text"
    result = loaded.evaluate()
    assert "not available" in result.failed[missing]
    assert loaded.node("concat") in result.blocked

    reloaded = loads(dumps(loaded), registry)
    assert graph_to_dict(reloaded) == graph_to_dict(graph)


def test_migrations(registry):
    class Scale(Node):
        type_name = "test.scale"
        version = 1
        parameters = (Parameter("factor", "float", 1.0),)

    registry.register_node(Scale)
    graph = Graph(registry)
    graph.create_node("test.scale", values={"factor": 3})
    text = dumps(graph)

    class ScaleV2(Node):
        type_name = "test.scale"
        version = 2
        parameters = (Parameter("multiplier", "float", 1.0),)

        @classmethod
        def migrate(cls, data, from_version):
            if from_version < 2:
                data["values"] = {"multiplier": data["values"].pop("factor")}
            return data

    registry.register_node(ScaleV2, replace=True)
    loaded = loads(text, registry)
    assert loaded.node("scale").get("multiplier") == 3.0
    assert graph_to_dict(loaded)["nodes"][0]["version"] == 2


def test_dropped_plugs_and_bad_values_are_skipped(registry, caplog):
    data = {"format": "bolt.graph", "version": 1, "graph": {"name": "root", "nodes": [
        {"name": "add", "type": "test.add", "values": {"a": "oops", "gone": 1}},
        {"name": "other", "type": "test.add"},
    ], "connections": [["add", "result", "other", "a"], ["add", "nope", "other", "b"]]}}
    graph = loads(json.dumps(data), registry)
    assert graph.node("add").get("a") == 0.0
    assert graph.node("other")["a"].connections
    assert "no plug 'gone'" in caplog.text
    assert "cannot restore connection add.nope" in caplog.text


def test_custom_type_serialization():
    from bolt.core.datatypes import DataType

    class Vector(DataType):
        __slots__ = ()

        def coerce(self, value):
            return None if value is None else tuple(value)

        def serialize(self, value):
            return list(value)

        def deserialize(self, data):
            return tuple(data)

    class Point(Node):
        type_name = "test.point"
        parameters = (Parameter("position", "vector"),)
        outputs = (Output("position_out", "vector"),)

    registry = Registry()
    registry.register_type(Vector("vector", tuple, default=(0, 0, 0)))
    registry.register_node(Point)
    graph = Graph(registry)
    graph.create_node("test.point", values={"position": [1, 2, 3]})
    data = graph_to_dict(graph)
    assert data["nodes"][0]["values"]["position"] == [1, 2, 3]
    assert loads(dumps(graph), registry).node("point").get("position") == (1, 2, 3)
