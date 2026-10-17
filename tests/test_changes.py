import pytest

from bolt.core.changes import (ChangeKind, MappingDelta, SequenceDelta, apply_mapping, copy_with, diff_mapping,
                               merge_mapping)
from bolt.core.datatypes import dict_type, list_type
from bolt.core.graph import Graph
from bolt.core.node import Node
from bolt.core.plugs import Input, Output, Parameter
from bolt.core.registry import Registry
from bolt.core.serialization import dumps, loads


def test_mapping_delta_round_trip():
    a, b, c = object(), object(), object()
    old = {"a": a, "b": b, "c": c}
    new = {"a": a, "b": object(), "d": object()}
    delta = diff_mapping(old, new)
    assert set(delta.added) == {"d"}
    assert delta.removed == frozenset({"c"})
    assert set(delta.modified) == {"b"}
    assert apply_mapping(old, delta) == new


def _states():
    a, b, c, d = object(), object(), object(), object()
    return [
        ({"x": a}, {"x": a, "y": b}, {"y": b}),
        ({"x": a}, {}, {"x": b}),
        ({"x": a}, {"x": b, "y": c}, {"x": d, "y": c}),
        ({}, {"x": a}, {"x": b}),
        ({"x": a, "y": b}, {"x": c}, {"x": c, "y": d}),
    ]


@pytest.mark.parametrize("first, second, third", _states())
def test_merged_mapping_deltas_match_direct_diff(first, second, third):
    merged = merge_mapping(diff_mapping(first, second), diff_mapping(second, third))
    assert apply_mapping(first, merged) == third


def test_sequence_delta():
    a, b = object(), object()
    delta = list_type.diff([a, b], [a, 3])
    assert delta == SequenceDelta({1: 3})
    assert list_type.apply([a, b], delta) == [a, 3]
    assert list_type.diff([a], [a, b]) is None


def test_copy_with_shares_untouched_items():
    first, second = object(), object()
    mapping = {"a": first, "b": second}
    copied = copy_with(mapping, {"c": 1}, removed=("b",))
    assert copied == {"a": first, "c": 1} and copied["a"] is first and mapping == {"a": first, "b": second}
    assert copy_with([first, second], {1: 5}) == [first, 5]
    assert copy_with([first, second, 3], removed=(0, 2)) == [second]


def test_fingerprints():
    item = object()
    assert dict_type.fingerprint({"a": item}) == dict_type.fingerprint({"a": item})
    assert dict_type.fingerprint({"a": item}) != dict_type.fingerprint({"a": object()})
    assert list_type.fingerprint(None) is None


class Objects(Node):
    type_name = "test.objects"
    parameters = (Parameter("count", "int", 3), Parameter("changed", "int", -1))
    outputs = (Output("scene", "dict"),)

    def cook(self, ctx):
        previous = self.plug("scene").value or {}
        count = ctx.get("changed")
        scene = {f"object{index}": previous.get(f"object{index}") or object() for index in range(ctx.get("count"))}
        if count >= 0:
            scene[f"object{count}"] = object()
        ctx.set("scene", scene)


class Watcher(Node):
    type_name = "test.watcher"
    inputs = (Input("scene", "dict"),)
    parameters = (Parameter("label", "string", "a"),)
    outputs = (Output("count", "int"),)

    def __init__(self, name=None):
        super().__init__(name)
        self.seen = []

    def cook(self, ctx):
        change = ctx.change("scene")
        self.seen.append((change.kind, change.delta, ctx.changed()))
        ctx.set("count", len(change.value))


@pytest.fixture
def graph():
    registry = Registry()
    for node_class in (Objects, Watcher):
        registry.register_node(node_class)
    graph = Graph(registry)
    graph.create_node("test.objects", "objects")
    graph.create_node("test.watcher", "watcher")
    graph.connect("objects.scene", "watcher.scene")
    return graph


def test_consumer_receives_deltas(graph):
    objects = graph.node("objects")
    watcher = graph.node("watcher")
    graph.evaluate()
    assert watcher.seen[-1][0] is ChangeKind.replaced
    assert sorted(watcher.seen[-1][2]) == ["label", "scene"]

    objects.set("changed", 1)
    graph.evaluate()
    kind, delta, changed = watcher.seen[-1]
    assert kind is ChangeKind.delta
    assert set(delta.modified) == {"object1"} and not delta.added and not delta.removed
    assert changed == ["scene"]

    objects.set("count", 4)
    objects.set("changed", -1)
    graph.evaluate()
    kind, delta, _ = watcher.seen[-1]
    assert set(delta.added) == {"object3"} and not delta.modified

    watcher.set("label", "b")
    graph.evaluate()
    kind, delta, changed = watcher.seen[-1]
    assert kind is ChangeKind.unchanged and changed == ["label"]


def test_skipped_evaluations_merge_deltas(graph):
    objects = graph.node("objects")
    watcher = graph.node("watcher")
    graph.evaluate()
    graph.evaluate()
    objects.set("changed", 0)
    graph.evaluate("objects")
    objects.set("count", 2)
    objects.set("changed", -1)
    graph.evaluate("objects")
    graph.evaluate()
    kind, delta, _ = watcher.seen[-1]
    assert kind is ChangeKind.delta
    assert delta.removed == frozenset({"object2"}) and set(delta.modified) == {"object0"}


def test_history_overflow_falls_back_to_replaced(graph):
    objects = graph.node("objects")
    watcher = graph.node("watcher")
    graph.evaluate()
    graph.evaluate()
    for index in range(40):
        objects.set("changed", index % 3)
        graph.evaluate("objects")
    graph.evaluate()
    assert watcher.seen[-1][0] is ChangeKind.replaced


def test_failed_cook_keeps_unseen_changes(graph):
    watcher = graph.node("watcher")
    objects = graph.node("objects")
    graph.evaluate()
    graph.evaluate()
    objects.set("changed", 0)
    original = Watcher.cook

    def failing(self, ctx):
        raise RuntimeError("boom")

    Watcher.cook = failing
    try:
        graph.evaluate()
    finally:
        Watcher.cook = original
    objects.set("changed", 2)
    graph.evaluate()
    kind, delta, _ = watcher.seen[-1]
    assert kind is ChangeKind.delta and set(delta.modified) == {"object0", "object2"}


def test_producer_delta_wins(graph):
    class Explicit(Node):
        type_name = "test.explicit"
        parameters = (Parameter("step", "int", 0),)
        outputs = (Output("scene", "dict"),)

        def cook(self, ctx):
            ctx.set("scene", {"value": ctx.get("step")}, delta=MappingDelta(modified={"value": ctx.get("step")}))

    graph.registry.register_node(Explicit)
    explicit = graph.create_node("test.explicit")
    graph.connect("explicit.scene", "watcher.scene")
    watcher = graph.node("watcher")
    graph.evaluate()
    graph.evaluate()
    explicit.set("step", 1)
    graph.evaluate()
    assert watcher.seen[-1][1] == MappingDelta(modified={"value": 1})


def test_strict_mode_detects_mutated_inputs(graph):
    class Mutator(Node):
        type_name = "test.mutator"
        inputs = (Input("scene", "dict"),)

        def cook(self, ctx):
            ctx.get("scene")["sneaky"] = 1

    graph.registry.register_node(Mutator)
    mutator = graph.create_node("test.mutator")
    graph.connect("objects.scene", "mutator.scene")
    result = graph.evaluate(strict=True)
    assert "modified its input 'scene' in place" in result.failed[mutator]


def test_strict_mode_detects_wrong_deltas(graph):
    class Liar(Node):
        type_name = "test.liar"
        parameters = (Parameter("step", "int", 0),)
        outputs = (Output("scene", "dict"),)

        def cook(self, ctx):
            ctx.set("scene", {"value": ctx.get("step")}, delta=MappingDelta())

    graph.registry.register_node(Liar)
    liar = graph.create_node("test.liar")
    graph.evaluate(strict=True)
    liar.set("step", 1)
    result = graph.evaluate(strict=True)
    assert "does not turn the previous value into the new one" in result.failed[liar]


def test_deltas_cross_subgraph_boundaries(graph):
    graph.disconnect("objects.scene", "watcher.scene")
    sub = graph.create_node("bolt.subgraph", "group")
    sub.add_subgraph_input("scene", "dict")
    sub.add_subgraph_output("count", "int")
    inner = sub.subgraph
    inner_watcher = inner.create_node("test.watcher", "inner")
    inner.connect("inputs.scene", "inner.scene")
    inner.connect("inner.count", "outputs.count")
    graph.connect("objects.scene", "group.scene")
    graph.evaluate()
    graph.evaluate()
    graph.node("objects").set("changed", 2)
    graph.evaluate()
    kind, delta, _ = inner_watcher.seen[-1]
    assert kind is ChangeKind.delta and set(delta.modified) == {"object2"}


def test_unchanged_upstream_reports_unchanged(graph):
    watcher = graph.node("watcher")
    graph.evaluate()
    watcher.set("label", "z")
    graph.evaluate()
    assert watcher.seen[-1][0] is ChangeKind.unchanged


def test_display_flag_and_context(graph):
    watcher = graph.node("watcher")
    watcher.displayed = True
    assert graph.displayed_nodes() == [watcher]
    loaded = loads(dumps(graph), graph.registry, context="host")
    assert loaded.node("watcher").displayed
    assert loaded.context == "host"
    sub = loaded.create_node("bolt.subgraph")
    assert sub.subgraph.context == "host"

    received = []

    class ReadsContext(Node):
        type_name = "test.reads_context"

        def cook(self, ctx):
            received.append(ctx.context)

    loaded.registry.register_node(ReadsContext)
    sub.subgraph.create_node("test.reads_context")
    sub.subgraph.evaluate()
    assert received == ["host"]
