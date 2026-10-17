import threading
import time

import pytest

from bolt.core import events
from bolt.core.errors import Cancelled, CookError, GraphBusyError
from bolt.core.evaluation import Control, EvaluationStatus
from bolt.core.executors import ThreadedExecutor
from bolt.core.graph import Graph
from bolt.core.node import Node, NodeState
from bolt.core.plugs import Input, Output, Parameter
from support import cooks


def chain(graph, count=3):
    nodes = [graph.create_node("test.add", f"n{index}", values={"b": 1}) for index in range(count)]
    for upstream, downstream in zip(nodes, nodes[1:]):
        graph.connect(upstream["result"], downstream["a"])
    return nodes


def test_evaluate_and_cache(graph):
    nodes = chain(graph)
    result = graph.evaluate()
    assert result.succeeded
    assert cooks.names == ["n0", "n1", "n2"]
    assert nodes[2].get("result") == 3.0
    assert all(node.state is NodeState.cooked for node in nodes)

    cooks.clear()
    result = graph.evaluate()
    assert cooks.names == []
    assert result.fresh == nodes


def test_changes_only_recook_downstream(graph):
    nodes = chain(graph)
    graph.evaluate()
    cooks.clear()
    nodes[1].set("b", 10)
    graph.evaluate()
    assert cooks.names == ["n1", "n2"]
    assert nodes[2].get("result") == 12.0


def test_targets_limit_evaluation(graph):
    chain(graph)
    graph.create_node("test.add", "unrelated")
    graph.evaluate("n1")
    assert cooks.names == ["n0", "n1"]
    cooks.clear()
    graph.evaluate("n2.result")
    assert cooks.names == ["n2"]


def test_stale_nodes_are_transitive(graph):
    nodes = chain(graph)
    graph.evaluate()
    nodes[0].set("b", 5)
    assert graph.stale_nodes() == nodes
    assert graph.stale_nodes("n0") == [nodes[0]]


def test_pull(graph):
    chain(graph)
    assert graph.pull("n2.result") == 3.0
    with pytest.raises(Exception):
        graph.pull("n2.a")


def test_connection_change_recooks(graph):
    nodes = chain(graph)
    graph.evaluate()
    cooks.clear()
    graph.disconnect("n0.result", "n1.a")
    graph.evaluate()
    assert cooks.names == ["n1", "n2"]
    assert nodes[2].get("result") == 2.0


def test_variables_invalidate_dependent_nodes_only(graph):
    framed = graph.create_node("test.add", "framed", values={"a": "`FRAME`"})
    static = graph.create_node("test.add", "static", values={"a": 1})
    graph.evaluate(variables={"FRAME": 1})
    cooks.clear()
    graph.evaluate(variables={"FRAME": 1})
    assert cooks.names == []
    graph.evaluate(variables={"FRAME": 2})
    assert cooks.names == ["framed"]
    assert framed.get("result") == 2.0
    assert static.get("result") == 1.0


def test_graph_variables_and_environment(graph, monkeypatch):
    monkeypatch.setenv("BOLT_TEST_ROOT", "/env")
    text = graph.create_node("test.text", values={"text": "$(BOLT_TEST_ROOT)/$(SHOT)"})
    graph.set_variable("SHOT", "sh010")
    graph.evaluate()
    assert text.get("result") == "/env/sh010"
    cooks.clear()
    graph.set_variable("SHOT", "sh020")
    graph.evaluate()
    assert cooks.names == ["text"]
    assert graph.pull("text.result", variables={"BOLT_TEST_ROOT": "/override"}) == "/override/sh020"


def test_context_dependencies_are_tracked():
    class FrameNode(Node):
        type_name = "test.frame"
        context_dependencies = frozenset({"FRAME"})
        outputs = (Output("frame", "int"),)

        def cook(self, ctx):
            cooks.names.append(self.name)
            ctx.set("frame", ctx.variables.get("FRAME", 0))

    from bolt.core.registry import Registry
    registry = Registry()
    registry.register_node(FrameNode)
    graph = Graph(registry)
    graph.create_node("test.frame")
    assert graph.pull("frame.frame", variables={"FRAME": 3}) == 3
    assert graph.pull("frame.frame", variables={"FRAME": 3}) == 3
    assert graph.pull("frame.frame", variables={"FRAME": 4}) == 4
    assert cooks.names == ["frame", "frame"]


def test_failure_blocks_downstream(graph):
    graph.create_node("test.add", "source")
    failing = graph.create_node("test.fail", "failing")
    after = graph.create_node("test.add", "after")
    independent = graph.create_node("test.add", "independent")
    graph.connect("source.result", "failing.input")
    graph.connect("failing.result", "after.a")
    result = graph.evaluate()
    assert result.status is EvaluationStatus.failed
    assert list(result.failed) == [failing]
    assert "RuntimeError: boom" in result.failed[failing]
    assert result.blocked == [after]
    assert after.state is NodeState.blocked
    assert independent.state is NodeState.cooked
    with pytest.raises(CookError, match="failing failed"):
        graph.pull("after.result")


def test_cook_error_messages_have_no_traceback(graph, registry):
    class Clean(Node):
        type_name = "test.clean_error"

        def cook(self, ctx):
            raise CookError("file missing")

    registry.register_node(Clean)
    node = graph.create_node("test.clean_error")
    result = graph.evaluate()
    assert result.failed[node] == "file missing"
    assert node.error == "file missing"


def test_required_inputs(graph, registry):
    class Needs(Node):
        type_name = "test.needs"
        inputs = (Input("value", "any", required=True),)

        def cook(self, ctx):
            ctx.get("value")

    registry.register_node(Needs)
    node = graph.create_node("test.needs")
    result = graph.evaluate()
    assert "not connected" in result.failed[node]


def test_bad_expression_fails_the_node(graph):
    node = graph.create_node("test.add", values={"a": "`UNDEFINED + 1`"})
    result = graph.evaluate()
    assert "undefined variable 'UNDEFINED'" in result.failed[node]


def test_disabled_node_passes_through(graph):
    nodes = chain(graph)
    nodes[1].disabled = True
    graph.evaluate()
    assert cooks.names == ["n0", "n2"]
    assert nodes[1].get("result") == 1.0
    assert nodes[2].get("result") == 2.0


def test_force(graph):
    chain(graph)
    graph.evaluate()
    cooks.clear()
    graph.evaluate(force=True)
    assert cooks.names == ["n0", "n1", "n2"]


def test_always_cook(graph, registry):
    class Volatile(Node):
        type_name = "test.volatile"
        always_cook = True
        outputs = (Output("value", "float"),)

        def cook(self, ctx):
            cooks.names.append(self.name)
            ctx.set("value", 1.0)

    registry.register_node(Volatile)
    graph.create_node("test.volatile")
    graph.create_node("test.add")
    graph.connect("volatile.value", "add.a")
    graph.evaluate()
    graph.evaluate()
    assert cooks.names == ["volatile", "add", "volatile", "add"]


def test_lazy_connections(graph, registry):
    class Choose(Node):
        type_name = "test.choose"
        inputs = (Input("inputs", "float", multi=True),)
        parameters = (Parameter("index", "int", 0),)
        outputs = (Output("result", "float"),)

        def active_connections(self, evaluation):
            connections = self.plug("inputs").connections
            return connections[evaluation.parameter(self, "index"):][:1]

        def cook(self, ctx):
            ctx.set("result", ctx.get_item("inputs", ctx.get("index")))

    registry.register_node(Choose)
    graph.create_node("test.add", "left", values={"a": 1})
    graph.create_node("test.add", "right", values={"a": 2})
    choose = graph.create_node("test.choose")
    graph.connect("left.result", "choose.inputs")
    graph.connect("right.result", "choose.inputs")
    assert graph.pull("choose.result") == 1.0
    assert cooks.names == ["left"]
    choose.set("index", 1)
    assert graph.pull("choose.result") == 2.0
    assert cooks.names == ["left", "right"]


def test_structure_is_locked_while_evaluating(graph, registry):
    errors = []

    class Editor(Node):
        type_name = "test.editor"

        def cook(self, ctx):
            try:
                ctx.graph.create_node("test.add")
            except GraphBusyError as error:
                errors.append(error)

    registry.register_node(Editor)
    graph.create_node("test.editor")
    graph.evaluate()
    assert len(errors) == 1
    graph.create_node("test.add")


def test_evaluation_events(graph):
    chain(graph, 2)
    received = []
    graph.events.subscribe(events.Event, lambda event: received.append(type(event).__name__))
    graph.evaluate()
    assert received == ["EvaluationStarted",
                        "NodeCookStarted", "NodeCooked", "EvaluationProgress",
                        "NodeCookStarted", "NodeCooked", "EvaluationProgress",
                        "EvaluationFinished"]


def test_node_logs_and_progress_are_events(graph, registry):
    class Chatty(Node):
        type_name = "test.chatty"

        def cook(self, ctx):
            ctx.info("hello")
            ctx.progress(0.5)

    registry.register_node(Chatty)
    graph.create_node("test.chatty")
    logs = []
    progress = []
    graph.events.subscribe(events.NodeLog, lambda event: logs.append(event.message))
    graph.events.subscribe(events.NodeProgress, lambda event: progress.append(event.fraction))
    graph.evaluate()
    assert logs == ["hello"] and progress == [0.5]


class SleepNode(Node):
    type_name = "test.sleep"
    inputs = (Input("input", "any"),)
    parameters = (Parameter("seconds", "float", 0.2),)
    outputs = (Output("result", "any"),)

    def cook(self, ctx):
        deadline = time.monotonic() + ctx.get("seconds")
        while time.monotonic() < deadline:
            ctx.checkpoint()
            time.sleep(0.01)
        cooks.names.append(self.name)
        ctx.set("result", self.name)


def test_threaded_executor_runs_branches_in_parallel(graph, registry):
    registry.register_node(SleepNode)
    for index in range(4):
        graph.create_node("test.sleep", f"sleep{index}")
    merge = graph.create_node("test.concat")
    for index in range(4):
        graph.connect(f"sleep{index}.result", "concat.parts")
    start = time.monotonic()
    result = graph.evaluate(executor=ThreadedExecutor(4))
    elapsed = time.monotonic() - start
    assert result.succeeded
    assert elapsed < 0.6
    assert cooks.names[-1] == "concat"
    assert merge.get("result") == "sleep0sleep1sleep2sleep3"


def test_threaded_executor_respects_dependencies_and_failures(graph):
    nodes = chain(graph, 4)
    failing = graph.create_node("test.fail")
    after = graph.create_node("test.add", "after")
    graph.connect("n3.result", "fail.input")
    graph.connect("fail.result", "after.a")
    result = graph.evaluate(executor=ThreadedExecutor(4))
    assert cooks.names[:4] == ["n0", "n1", "n2", "n3"]
    assert list(result.failed) == [failing]
    assert result.blocked == [after]
    assert nodes[3].get("result") == 4.0


@pytest.mark.parametrize("executor", [None, ThreadedExecutor(2)])
def test_cancel(graph, registry, executor):
    registry.register_node(SleepNode)
    first = graph.create_node("test.sleep", "first", values={"seconds": 5})
    second = graph.create_node("test.sleep", "second")
    graph.connect("first.result", "second.input")
    control = Control()
    threading.Timer(0.1, control.cancel).start()
    start = time.monotonic()
    result = graph.evaluate(control=control, executor=executor)
    assert time.monotonic() - start < 2
    assert result.status is EvaluationStatus.cancelled
    assert first.state is NodeState.uncooked
    assert second.state is NodeState.uncooked
    assert not graph.is_evaluating


def test_pause_and_resume(graph, registry):
    registry.register_node(SleepNode)
    graph.create_node("test.sleep", values={"seconds": 0.05})
    control = Control()
    control.pause()
    finished = threading.Event()
    thread = threading.Thread(target=lambda: (graph.evaluate(control=control), finished.set()))
    thread.start()
    assert not finished.wait(0.2)
    control.resume()
    assert finished.wait(2)
    thread.join()


def test_control_checkpoint():
    control = Control()
    control.checkpoint()
    control.cancel()
    with pytest.raises(Cancelled):
        control.checkpoint()
