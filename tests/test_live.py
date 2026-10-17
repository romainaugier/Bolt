import threading
import time

import pytest

from bolt.core.graph import Graph
from bolt.core.live import EditPolicy, LiveCooker, LiveMode, LiveStateChanged
from bolt.core.node import Node
from bolt.core.plugs import Input, Output, Parameter
from bolt.core.registry import Registry


class Slow(Node):
    type_name = "test.slow"
    inputs = (Input("input", "float"),)
    parameters = (Parameter("seconds", "float", 0.0), Parameter("value", "float", 0.0))
    outputs = (Output("result", "float"),)
    started = threading.Event()
    log: list[str] = []

    def cook(self, ctx):
        Slow.log.append(f"start {self.name} {ctx.get('value')}")
        Slow.started.set()
        deadline = time.monotonic() + ctx.get("seconds")
        while time.monotonic() < deadline:
            ctx.checkpoint()
            time.sleep(0.005)
        Slow.log.append(f"end {self.name} {ctx.get('value')}")
        ctx.set("result", ctx.get("input") + ctx.get("value"))


@pytest.fixture
def graph():
    Slow.log = []
    Slow.started.clear()
    registry = Registry()
    registry.register_node(Slow)
    graph = Graph(registry)
    graph.create_node("test.slow", "source")
    sink = graph.create_node("test.slow", "sink")
    graph.connect("source.result", "sink.input")
    sink.displayed = True
    return graph


@pytest.fixture
def cookers():
    created = []
    yield created
    for cooker in created:
        cooker.close()


def make(graph, cookers, **kwargs):
    cooker = LiveCooker(graph, debounce=0.01, **kwargs)
    cookers.append(cooker)
    return cooker


def test_auto_mode_cooks_displayed_nodes_after_edits(graph, cookers):
    cooker = make(graph, cookers)
    graph.node("source").set("value", 2)
    assert cooker.wait(5)
    assert graph.node("sink").get("result") == 2.0
    graph.node("sink").set("value", 1)
    assert cooker.wait(5)
    assert graph.node("sink").get("result") == 3.0


def test_auto_mode_without_displayed_nodes_does_nothing(graph, cookers):
    graph.node("sink").displayed = False
    cooker = make(graph, cookers)
    graph.node("source").set("value", 2)
    assert cooker.wait(5)
    assert cooker.last_result is None


def test_manual_mode_waits_for_cook(graph, cookers):
    cooker = make(graph, cookers, mode=LiveMode.manual)
    graph.node("source").set("value", 5)
    assert cooker.wait(5)
    assert cooker.last_result is None
    cooker.cook()
    assert cooker.wait(5)
    assert graph.node("sink").get("result") == 5.0


def test_manual_mode_cooks_everything_without_display(graph, cookers):
    graph.node("sink").displayed = False
    graph.create_node("test.slow", "other", values={"value": 7})
    cooker = make(graph, cookers, mode=LiveMode.manual)
    cooker.cook()
    assert cooker.wait(5)
    assert graph.node("other").get("result") == 7.0


def test_restart_policy_cancels_running_cook(graph, cookers):
    graph.node("source").set("seconds", 2)
    cooker = make(graph, cookers, policy=EditPolicy.restart)
    assert Slow.started.wait(5)
    start = time.monotonic()
    graph.node("source").set("seconds", 0)
    graph.node("source").set("value", 4)
    assert cooker.wait(5)
    assert time.monotonic() - start < 1.5
    assert graph.node("sink").get("result") == 4.0
    assert "end source 0.0" not in Slow.log


def test_finish_policy_lets_cook_end_then_recooks(graph, cookers):
    graph.node("source").set("seconds", 0.3)
    cooker = make(graph, cookers, policy=EditPolicy.finish)
    assert Slow.started.wait(5)
    graph.node("source").set("value", 4)
    assert cooker.wait(5)
    assert Slow.log[0] == "start source 0.0" and Slow.log[1].startswith("end source")
    assert Slow.log.count("start sink 0.0") == 2
    assert graph.node("sink").get("result") == 4.0


def test_structural_edits_are_queued_during_cook(graph, cookers):
    graph.node("source").set("seconds", 0.3)
    cooker = make(graph, cookers, policy=EditPolicy.finish)
    assert Slow.started.wait(5)
    applied = cooker.edit(lambda: graph.disconnect("source.result", "sink.input"))
    assert applied is False
    assert graph.node("sink")["input"].connections
    assert cooker.wait(5)
    assert not graph.node("sink")["input"].connections
    assert graph.node("sink").get("result") == 0.0


def test_edits_run_immediately_when_idle(graph, cookers):
    cooker = make(graph, cookers, mode=LiveMode.manual)
    assert cooker.edit(lambda: graph.create_node("test.slow", "added"))
    assert graph.find_node("added") is not None


def test_queued_edits_use_call_soon(graph, cookers):
    calls = []
    pending = []
    graph.node("source").set("seconds", 0.2)
    cooker = make(graph, cookers, policy=EditPolicy.finish, call_soon=pending.append)
    assert Slow.started.wait(5)
    cooker.edit(lambda: calls.append("edited"))
    deadline = time.monotonic() + 5
    while not pending and time.monotonic() < deadline:
        time.sleep(0.01)
    assert calls == []
    pending.pop()()
    assert calls == ["edited"]
    assert cooker.wait(5)


def test_variables_trigger_cooks(graph, cookers):
    graph.node("source").set("value", "`FRAME`")
    cooker = make(graph, cookers)
    cooker.set_variables({"FRAME": 3})
    assert cooker.wait(5)
    assert graph.node("sink").get("result") == 3.0


def test_state_events(graph, cookers):
    states = []
    graph.events.subscribe(LiveStateChanged, lambda event: states.append((event.mode, event.busy)))
    cooker = make(graph, cookers, mode=LiveMode.manual)
    cooker.mode = LiveMode.auto
    assert cooker.wait(5)
    assert (LiveMode.auto, True) in states
    assert states[-1] == (LiveMode.auto, False)


def test_cook_specific_targets_once(graph, cookers):
    graph.create_node("test.slow", "other", values={"value": 7})
    cooker = make(graph, cookers, mode=LiveMode.manual)
    cooker.cook([graph.node("other")])
    assert cooker.wait(5)
    assert graph.node("other").get("result") == 7.0
    assert graph.node("sink").state.value == "uncooked"
