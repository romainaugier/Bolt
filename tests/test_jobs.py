import json
import pathlib
import subprocess
import sys
import time

import pytest

from bolt.core.graph import Graph
from bolt.core.jobs import JobAdded, JobChanged, JobLog, JobManager, JobRemoved, JobStatus
from bolt.core.registry import Registry
from bolt.core.serialization import save_graph

root = pathlib.Path(__file__).resolve().parent.parent


@pytest.fixture
def registry():
    registry = Registry()
    registry.load_plugin("bolt.stdlib")
    return registry


@pytest.fixture
def manager(registry, tmp_path):
    manager = JobManager(registry, directory=str(tmp_path / "jobs"))
    yield manager
    manager.cancel_all()
    manager.wait(15)


def sleeper(registry, seconds=0.0, fail=False):
    graph = Graph(registry, name="sleeper")
    graph.create_node("flow.sleep", "wait", values={"seconds": seconds})
    graph.create_node("flow.log", "say", values={"message": "slept $(LABEL)"})
    graph.connect("wait.result", "say.input")
    if fail:
        graph.create_node("flow.fail", "boom", values={"message": "it broke"})
        graph.connect("say.result", "boom.input")
    graph.set_variable("LABEL", "default")
    return graph


def test_job_success_reports_progress_and_logs(registry, manager):
    events = []
    manager.events.subscribe(JobAdded, lambda event: events.append("added"))
    manager.events.subscribe(JobLog, lambda event: events.append(event.message))
    job = manager.submit(sleeper(registry), variables={"LABEL": "well"})
    assert job.wait(30)
    assert job.status is JobStatus.succeeded
    assert job.return_code == 0
    assert (job.done, job.total) == (2, 2) and job.progress == 1.0
    assert "slept well" in [message for _, message, _ in job.log]
    assert events[0] == "added" and "slept well" in events


def test_job_failure(registry, manager):
    job = manager.submit(sleeper(registry, fail=True))
    assert job.wait(30)
    assert job.status is JobStatus.failed
    assert job.failed == {"/boom": "it broke"}


def test_job_from_file_and_targets(registry, manager, tmp_path):
    path = tmp_path / "graph.bolt"
    save_graph(sleeper(registry, fail=True), path)
    job = manager.submit(path, targets=["say"])
    assert job.wait(30)
    assert job.status is JobStatus.succeeded
    assert job.name == "graph"


def test_cancel_and_pause(registry, manager):
    job = manager.submit(sleeper(registry, seconds=20))
    deadline = time.monotonic() + 20
    while job.current_node is None and time.monotonic() < deadline:
        time.sleep(0.02)
    job.pause()
    assert job.status is JobStatus.paused
    job.resume()
    assert job.status is JobStatus.running
    job.cancel()
    assert job.wait(15)
    assert job.status is JobStatus.cancelled


def test_queue_respects_max_running(registry, tmp_path):
    manager = JobManager(registry, max_running=1, directory=str(tmp_path / "jobs"))
    first = manager.submit(sleeper(registry, seconds=0.5))
    second = manager.submit(sleeper(registry))
    assert second.status is JobStatus.queued
    assert manager.wait(60)
    assert second.started_at >= first.finished_at - 0.05
    assert {first.status, second.status} == {JobStatus.succeeded}


def test_cancel_queued_job_and_remove(registry, tmp_path):
    manager = JobManager(registry, max_running=1, directory=str(tmp_path / "jobs"))
    removed = []
    manager.events.subscribe(JobRemoved, lambda event: removed.append(event.job))
    first = manager.submit(sleeper(registry, seconds=0.3))
    second = manager.submit(sleeper(registry))
    second.cancel()
    assert second.status is JobStatus.cancelled and second.started_at is None
    with pytest.raises(ValueError):
        manager.remove(first)
    assert manager.wait(30)
    manager.clear_finished()
    assert manager.jobs() == [] and removed == [first, second]


def test_plugins_are_reloaded_in_the_child(tmp_path):
    registry = Registry()
    registry.load_plugin("bolt.stdlib")
    registry.load_plugin(root / "examples" / "plugins" / "shots.py")
    graph = Graph(registry)
    graph.create_node("shots.make", "shot")
    manager = JobManager(registry, directory=str(tmp_path / "jobs"))
    changes = []
    manager.events.subscribe(JobChanged, lambda event: changes.append(event.job.status))
    job = manager.submit(graph)
    assert job.wait(30)
    assert job.status is JobStatus.succeeded, list(job.log)
    assert JobStatus.running in changes


def test_cli_event_stream_and_control(registry, tmp_path):
    path = tmp_path / "graph.bolt"
    save_graph(sleeper(registry, seconds=0.2), path)
    process = subprocess.Popen([sys.executable, "-m", "bolt", "cook", str(path), "--events", "--control",
                                "-o", "say.result"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
                               cwd=root, env={"PYTHONPATH": str(root / "src")})
    output, _ = process.communicate("pause\nresume\n", timeout=30)
    lines = [json.loads(line) for line in output.splitlines()]
    kinds = [line["event"] for line in lines]
    assert kinds[0] == "started" and "finished" in kinds
    finished = next(line for line in lines if line["event"] == "finished")
    assert finished["status"] == "cancelled"
    assert process.returncode == 130

    completed = subprocess.run([sys.executable, "-m", "bolt", "cook", str(path), "--events", "-o", "say.result"],
                               capture_output=True, text=True, cwd=root, env={"PYTHONPATH": str(root / "src")})
    lines = [json.loads(line) for line in completed.stdout.splitlines()]
    assert lines[-1] == {"event": "output", "plug": "say.result", "value": None}
    assert any(line["event"] == "log" and line["message"] == "slept default" for line in lines)
    assert completed.returncode == 0
