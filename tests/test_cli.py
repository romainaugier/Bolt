import json
import pathlib
import subprocess
import sys

import pytest

from bolt.cli import main
from bolt.core.graph import Graph
from bolt.core.registry import Registry
from bolt.core.serialization import save_graph

examples = pathlib.Path(__file__).resolve().parent.parent / "examples"


@pytest.fixture
def graph_file(tmp_path):
    registry = Registry()
    registry.load_plugin("bolt.stdlib")
    graph = Graph(registry)
    graph.set_variable("NAME", "world")
    graph.create_node("values.string", "greeting", values={"value": "hello $(NAME)"})
    graph.create_node("values.int", "count", values={"value": "`COUNT * 2`"})
    graph.create_node("flow.fail", "guard", values={"condition": "`COUNT > 10`", "message": "too many"})
    graph.connect("count.result", "guard.input")
    path = tmp_path / "graph.bolt"
    save_graph(graph, path)
    return path


def test_cook_prints_outputs(graph_file, capsys):
    code = main(["-q", "cook", str(graph_file), "-s", "COUNT=3", "-s", "NAME=bolt",
                 "-o", "greeting.result", "-o", "guard.result"])
    assert code == 0
    assert capsys.readouterr().out.splitlines() == ['"hello bolt"', "6"]


def test_cook_failure_exit_code(graph_file, capsys):
    assert main(["-q", "cook", str(graph_file), "-s", "COUNT=20"]) == 1


def test_cook_targets(graph_file, capsys):
    assert main(["-q", "cook", str(graph_file), "-t", "greeting", "-o", "greeting.result"]) == 0
    assert capsys.readouterr().out.strip() == '"hello world"'


def test_threaded_cook(graph_file, capsys):
    assert main(["-q", "cook", str(graph_file), "-j", "4", "-s", "COUNT=1", "-o", "count.result"]) == 0
    assert capsys.readouterr().out.strip() == "2"


def test_nodes_listing(capsys):
    assert main(["nodes", "--json"]) == 0
    types = {entry["type"]: entry for entry in json.loads(capsys.readouterr().out)}
    assert {"bolt.subgraph", "bolt.for_each", "math.add", "process.run"} <= set(types)
    assert types["math.add"]["plugs"][0] == {"name": "a", "kind": "input", "type": "float"}
    assert main(["--no-stdlib", "nodes"]) == 0
    assert "math.add" not in capsys.readouterr().out


def test_info(graph_file, capsys):
    assert main(["info", str(graph_file)]) == 0
    output = capsys.readouterr().out
    assert "NAME = 'world'" in output
    assert "input     input: any <- /count.result" in output


def test_missing_file_is_reported(tmp_path, capsys):
    assert main(["cook", str(tmp_path / "missing.bolt")]) == 1


def test_example_graph_with_plugin(capsys):
    code = main(["-q", "-p", str(examples / "plugins"), "cook", str(examples / "graphs" / "shot_paths.bolt"),
                 "-s", "PROJECT_ROOT=/mnt/prod", "-o", "report.result"])
    assert code == 0
    assert capsys.readouterr().out.strip() == '"/mnt/prod/SQ010/SH020/SH020.####.exr"'


def test_module_entry_point():
    completed = subprocess.run([sys.executable, "-m", "bolt", "--no-stdlib", "nodes"], capture_output=True, text=True,
                               cwd=examples.parent, env={"PYTHONPATH": str(examples.parent / "src")})
    assert completed.returncode == 0
    assert "bolt.for_each" in completed.stdout


def test_embed_example():
    completed = subprocess.run([sys.executable, str(examples / "embed.py")], capture_output=True, text=True,
                               env={"PYTHONPATH": str(examples.parent / "src")})
    assert completed.returncode == 0, completed.stderr
    lines = completed.stdout.splitlines()
    assert lines[0].endswith("cooked=['plate', 'flicker']")
    assert lines[2].endswith("cooked=[]")
