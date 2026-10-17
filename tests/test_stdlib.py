import os
import sys
import threading

import pytest

from bolt.core.evaluation import Control, EvaluationStatus
from bolt.core.graph import Graph
from bolt.core.plugs import Input, Output
from bolt.core.registry import Registry


@pytest.fixture
def graph():
    registry = Registry()
    registry.load_plugin("bolt.stdlib")
    return Graph(registry)


def test_load_stdlib_by_module_name():
    registry = Registry()
    registry.load_plugin("bolt.stdlib")
    registry.load_plugin("bolt.stdlib")
    assert registry.has_node_type("math.add")
    assert registry.plugins == ["bolt.stdlib"]


def test_values_and_math(graph):
    graph.create_node("values.int", "count", values={"value": 4})
    graph.create_node("values.float", "half", values={"value": 0.5})
    graph.create_node("math.multiply", "product")
    graph.create_node("math.add", "total", values={"b": "`FRAME`"})
    graph.connect("count.result", "product.a")
    graph.connect("half.result", "product.b")
    graph.connect("product.result", "total.a")
    assert graph.pull("total.result", variables={"FRAME": 10}) == 12.0


def test_divide_by_zero(graph):
    node = graph.create_node("math.divide", values={"a": 1})
    assert graph.evaluate().failed[node] == "division by zero"


def test_sum_accepts_many_inputs(graph):
    for value in (1, 2, 3):
        graph.create_node("values.int", f"v{value}", values={"value": value})
    graph.create_node("math.sum")
    for value in (1, 2, 3):
        graph.connect(f"v{value}.result", "sum.values")
    assert graph.pull("sum.result") == 6.0


def test_strings(graph):
    graph.create_node("values.dict", "fields", values={"value": {"shot": "sh010", "frame": "$(FRAME)"}})
    graph.create_node("string.format", "name", values={"template": "{shot}_{frame}.exr"})
    graph.connect("fields.result", "name.values")
    assert graph.pull("name.result", variables={"FRAME": 1001}) == "sh010_1001.exr"

    graph.create_node("values.list", "parts", values={"value": ["a", 1, "c"]})
    graph.create_node("string.join", "joined", values={"separator": "/"})
    graph.connect("parts.result", "joined.items")
    graph.create_node("string.replace", "replaced", values={"old": "/", "new": "\\"})
    graph.connect("joined.result", "replaced.text")
    assert graph.pull("replaced.result") == "a\\1\\c"


def test_switch_only_cooks_selected_branch(graph):
    graph.create_node("values.string", "left", values={"value": "left"})
    graph.create_node("flow.fail", "right", values={"message": "should not run"})
    switch = graph.create_node("flow.switch", values={"index": 0})
    graph.connect("left.result", "switch.inputs")
    graph.connect("right.result", "switch.inputs")
    assert graph.pull("switch.result") == "left"
    switch.set("index", "`USE_RIGHT`")
    result = graph.evaluate(variables={"USE_RIGHT": 1})
    assert result.failed[graph.node("right")] == "should not run"
    switch.set("index", 5)
    assert "out of range" in graph.evaluate().failed[switch]


def test_merge_and_passthrough(graph):
    graph.create_node("values.list", "a", values={"value": [1, 2]})
    graph.create_node("values.int", "b", values={"value": 3})
    merge = graph.create_node("flow.merge")
    graph.connect("a.result", "merge.inputs")
    graph.connect("b.result", "merge.inputs")
    graph.create_node("flow.passthrough")
    graph.connect("merge.result", "passthrough.input")
    assert graph.pull("passthrough.result") == [[1, 2], 3]
    merge.set("flatten", True)
    assert graph.pull("passthrough.result") == [1, 2, 3]


def test_log(graph, caplog):
    caplog.set_level("INFO", logger="bolt.node")
    graph.create_node("values.string", "shot", values={"value": "sh010"})
    graph.create_node("flow.log", values={"message": "processing {value}", "level": "warning"})
    graph.connect("shot.result", "log.input")
    assert graph.pull("log.result") == "sh010"
    assert "/log: processing sh010" in caplog.text


def test_files(graph, tmp_path):
    source = tmp_path / "source"
    (source / "nested").mkdir(parents=True)
    for name in ("b.exr", "a.exr", "notes.txt"):
        (source / name).write_text(name)
    (source / "nested" / "c.exr").write_text("c")

    listing = graph.create_node("files.list_directory", values={"directory": str(source), "pattern": "*.exr"})
    assert graph.pull("list_directory.paths") == [str(source / "a.exr"), str(source / "b.exr")]
    listing.set("recursive", True)
    assert graph.pull("list_directory.paths")[-1] == str(source / "nested" / "c.exr")

    graph.create_node("files.join_path", "target", values={"directory": str(tmp_path), "name": "copy/dir"})
    graph.create_node("files.make_directory", "mkdir")
    graph.connect("target.path", "mkdir.path")
    graph.create_node("values.path", "file", values={"value": str(source / "a.exr")})
    graph.create_node("files.copy", "copy")
    graph.connect("file.result", "copy.source")
    graph.connect("mkdir.path_out", "copy.destination")
    copied = graph.pull("copy.path")
    assert copied == str(tmp_path / "copy" / "dir" / "a.exr")
    assert os.path.isfile(copied)

    graph.create_node("files.exists", values={"path": copied})
    assert graph.pull("exists.exists") is True

    missing = graph.create_node("files.list_directory", "missing", values={"directory": str(tmp_path / "nope")})
    assert "does not exist" in graph.evaluate(missing).failed[missing]


def test_process_run(graph):
    run = graph.create_node("process.run", values={
        "command": [sys.executable, "-c", "import os, sys; print(os.environ['BOLT_TEST']); print(sys.argv[1])"],
        "environment": {"BOLT_TEST": "$(SHOT)"},
    })
    graph.create_node("values.list", "args", values={"value": ["extra"]})
    graph.connect("args.result", "run.arguments")
    result = graph.evaluate(variables={"SHOT": "sh010"})
    assert result.succeeded, result.failed
    assert run.get("return_code") == 0
    assert run.get("output").split() == ["sh010", "extra"]

    run.set("environment", {})
    run.set("command", [sys.executable, "-c", "raise SystemExit(3)"])
    assert graph.evaluate().failed[run] == f"{sys.executable} exited with code 3"
    run.set("check", False)
    assert graph.evaluate().succeeded and run.get("return_code") == 3


def test_process_run_cancel(graph):
    graph.create_node("process.run", values={"command": [sys.executable, "-c", "import time; time.sleep(30)"]})
    control = Control()
    threading.Timer(0.3, control.cancel).start()
    assert graph.evaluate(control=control).status is EvaluationStatus.cancelled


def test_process_run_missing_program(graph):
    node = graph.create_node("process.run", values={"command": ["bolt-no-such-program"]})
    assert "cannot start" in graph.evaluate().failed[node]


def test_python_script(graph):
    script = graph.create_node("python.script", values={"code": "total = a * 2 + 1  # `not expanded` $(NOR_THIS)\nctx.info('done')"})
    script.add_plug(Input("a", "int", 4))
    script.add_plug(Output("total", "int"))
    script.add_plug(Output("unset", "string"))
    graph.evaluate()
    assert script.get("total") == 9
    assert script.get("unset") == ""

    script.set("code", "total = (")
    assert "syntax error line 1" in graph.evaluate().failed[script]
