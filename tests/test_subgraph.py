import pytest

from bolt.core.errors import GraphError
from bolt.core.subgraph import ForEachNode, SubgraphNode
from support import cooks


@pytest.fixture
def doubler(graph):
    sub = graph.create_node("bolt.subgraph", "doubler")
    sub.add_subgraph_input("value", "float")
    sub.add_subgraph_output("doubled", "float")
    inner = sub.subgraph
    inner.create_node("test.add", "twice", values={"scale": 2})
    inner.connect("inputs.value", "twice.a")
    inner.connect("twice.result", "outputs.doubled")
    return sub


def test_subgraph_evaluates_inner_graph(graph, doubler):
    graph.create_node("test.add", "source", values={"a": 3})
    graph.connect("source.result", "doubler.value")
    assert graph.pull("doubler.doubled") == 6.0
    assert doubler.subgraph.node("twice").path == "/doubler/twice"
    assert [node.name for node in graph.walk()] == ["doubler", "inputs", "outputs", "twice", "source"]


def test_subgraph_caching(graph, doubler):
    source = graph.create_node("test.add", "source", values={"a": 3})
    graph.connect("source.result", "doubler.value")
    graph.evaluate()
    cooks.clear()
    graph.evaluate()
    assert cooks.names == []

    doubler.subgraph.node("twice").set("scale", 3)
    graph.evaluate()
    assert cooks.names == ["twice"]
    assert doubler.get("doubled") == 9.0

    cooks.clear()
    source.set("a", 1)
    graph.evaluate()
    assert cooks.names == ["source", "twice"]
    assert doubler.get("doubled") == 3.0


def test_subgraph_unchanged_inputs_do_not_recook_inner_nodes(graph, doubler):
    source = graph.create_node("test.add", "source", values={"a": 3})
    graph.connect("source.result", "doubler.value")
    graph.evaluate()
    cooks.clear()
    source.set("b", 0)
    graph.evaluate()
    assert cooks.names == ["source"]


def test_inner_variables_trigger_recook(graph, doubler):
    doubler.subgraph.node("twice").set("b", "`FRAME`")
    graph.evaluate(variables={"FRAME": 1})
    cooks.clear()
    graph.evaluate(variables={"FRAME": 1})
    assert cooks.names == []
    graph.evaluate(variables={"FRAME": 5})
    assert cooks.names == ["twice"]
    assert doubler.get("doubled") == 10.0


def test_subgraph_variables_shadow_parent_variables(graph):
    graph.set_variable("NAME", "outer")
    sub = graph.create_node("bolt.subgraph")
    sub.add_subgraph_output("text", "string")
    sub.subgraph.set_variable("NAME", "inner")
    sub.subgraph.create_node("test.text", values={"text": "$(NAME)"})
    sub.subgraph.connect("text.result", "outputs.text")
    graph.create_node("test.text", values={"text": "$(NAME)"})
    graph.evaluate()
    assert sub.get("text") == "inner"
    assert graph.node("text").get("result") == "outer"


def test_inner_failure_fails_the_subgraph_node(graph, doubler):
    inner = doubler.subgraph
    inner.create_node("test.fail")
    inner.connect("twice.result", "fail.input")
    inner.connect("fail.result", "outputs.doubled")
    result = graph.evaluate()
    assert "/doubler/fail failed" in result.failed[doubler]


def test_io_nodes_cannot_be_removed(doubler):
    with pytest.raises(GraphError):
        doubler.subgraph.remove_node("inputs")


def test_remove_subgraph_plugs(doubler):
    doubler.remove_subgraph_input("value")
    assert not doubler.has_plug("value")
    assert not doubler.input_node.has_plug("value")
    assert not doubler.subgraph.node("twice")["a"].connections


def test_for_each(graph):
    items = graph.create_node("test.text", values={"text": "abc"})
    loop = graph.create_node("bolt.for_each", "loop")
    assert isinstance(loop, ForEachNode) and isinstance(loop, SubgraphNode)
    loop.add_subgraph_input("offset", "float", 10)
    body = loop.subgraph
    body.create_node("test.add", "body")
    body.connect("inputs.index", "body.a")
    body.connect("inputs.offset", "body.b")
    body.connect("body.result", "outputs.result")
    with pytest.raises(Exception):
        graph.connect(items["result"], loop["items"])

    graph.remove_node(items)
    from bolt.core.node import Node
    from bolt.core.plugs import Output

    class Items(Node):
        type_name = "test.items"
        outputs = (Output("items", "list"),)

        def cook(self, ctx):
            ctx.set("items", ["a", "b", "c"])

    graph.registry.register_node(Items)
    graph.create_node("test.items")
    graph.connect("items.items", "loop.items")
    assert graph.pull("loop.results") == [10.0, 11.0, 12.0]
    assert cooks.names == ["body", "body", "body"]

    cooks.clear()
    graph.evaluate()
    assert cooks.names == []
    loop.set("offset", 0)
    assert graph.pull("loop.results") == [0.0, 1.0, 2.0]


def test_for_each_failure_reports_iteration(graph):
    loop = graph.create_node("bolt.for_each", "loop")
    loop.set("items", [1, 2])
    loop.subgraph.create_node("test.fail")
    loop.subgraph.connect("inputs.item", "fail.input")
    loop.subgraph.connect("fail.result", "outputs.result")
    result = graph.evaluate()
    assert result.failed[loop].startswith("iteration 0: /loop/fail failed")
