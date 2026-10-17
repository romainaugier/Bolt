from __future__ import annotations

import enum
import itertools
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from collections import deque
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import IO, TYPE_CHECKING, Any

from bolt.core import events
from bolt.core.evaluation import Control
from bolt.core.events import Event, EventBus
from bolt.core.serialization import save_graph

if TYPE_CHECKING:
    from bolt.core.graph import Graph
    from bolt.core.registry import Registry

logger = logging.getLogger("bolt.jobs")

log_limit = 2000


def serialize_event(event: Event) -> dict[str, Any] | None:
    if isinstance(event, events.EvaluationStarted):
        return {"event": "started", "nodes": event.node_count}
    if isinstance(event, events.EvaluationProgress):
        return {"event": "progress", "done": event.done, "total": event.total}
    if isinstance(event, events.NodeCookStarted):
        return {"event": "node_started", "node": event.node.path}
    if isinstance(event, events.NodeCooked):
        return {"event": "node_cooked", "node": event.node.path, "duration": event.duration}
    if isinstance(event, events.NodeCookFailed):
        return {"event": "node_failed", "node": event.node.path, "error": event.error}
    if isinstance(event, events.NodeBlocked):
        return {"event": "node_blocked", "node": event.node.path}
    if isinstance(event, events.NodeLog):
        return {"event": "log", "node": event.node.path, "level": event.level, "message": event.message}
    if isinstance(event, events.NodeProgress):
        return {"event": "node_progress", "node": event.node.path, "fraction": event.fraction}
    if isinstance(event, events.EvaluationFinished):
        result = event.result
        return {"event": "finished", "status": result.status.value, "duration": result.duration,
                "cooked": len(result.cooked), "failed": {node.path: error for node, error in result.failed.items()},
                "blocked": [node.path for node in result.blocked]}
    return None


class EventStream:
    """Writes the evaluation events of a root graph as JSON lines, the format jobs read from their child process."""

    streamed = (events.EvaluationStarted, events.EvaluationProgress, events.NodeCookStarted, events.NodeCooked,
                events.NodeCookFailed, events.NodeBlocked, events.NodeLog, events.NodeProgress,
                events.EvaluationFinished)

    def __init__(self, graph: Graph, stream: IO[str]) -> None:
        self.graph = graph
        self.stream = stream
        self._lock = threading.Lock()
        self._subscriptions = [graph.events.subscribe(event_type, self._write) for event_type in self.streamed]

    def write(self, data: Mapping[str, Any]) -> None:
        line = json.dumps(data, default=repr)

        with self._lock:
            self.stream.write(line + "\n")
            self.stream.flush()

    def close(self) -> None:
        for subscription in self._subscriptions:
            subscription.close()

    def _write(self, event: Event) -> None:
        if isinstance(event, (events.EvaluationStarted, events.EvaluationProgress, events.EvaluationFinished)):
            if event.graph is not self.graph:
                return

        data = serialize_event(event)

        if data is not None:
            self.write(data)


def follow_control_commands(control: Control, stream: IO[str]) -> threading.Thread:
    """Read pause, resume and cancel commands, one per line. The end of the stream cancels."""

    def read() -> None:
        commands = {"pause": control.pause, "resume": control.resume, "cancel": control.cancel}

        for line in stream:
            command = commands.get(line.strip())

            if command is not None:
                command()

        control.cancel()

    thread = threading.Thread(target=read, name="bolt-control", daemon=True)
    thread.start()

    return thread


class JobStatus(enum.Enum):
    queued = "queued"
    running = "running"
    paused = "paused"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"

    @property
    def finished(self) -> bool:
        return self in (JobStatus.succeeded, JobStatus.failed, JobStatus.cancelled)


@dataclass(frozen=True, slots=True, eq=False)
class JobEvent(Event):
    job: Job


@dataclass(frozen=True, slots=True, eq=False)
class JobAdded(JobEvent):
    pass


@dataclass(frozen=True, slots=True, eq=False)
class JobChanged(JobEvent):
    pass


@dataclass(frozen=True, slots=True, eq=False)
class JobLog(JobEvent):
    level: int
    message: str
    node: str | None


@dataclass(frozen=True, slots=True, eq=False)
class JobRemoved(JobEvent):
    pass


_job_ids = itertools.count(1)


class Job:
    """A snapshot of a graph cooked by `bolt cook` in a child process."""

    def __init__(self,
                 manager: JobManager,
                 name: str,
                 graph_path: str,
                 directory: str,
                 targets: Iterable[str] = (),
                 variables: Mapping[str, Any] | None = None,
                 force: bool = False,
                 threads: int = 1) -> None:
        self.id = next(_job_ids)
        self.name = name
        self.graph_path = graph_path
        self.directory = directory
        self.targets = list(targets)
        self.variables = dict(variables) if variables else {}
        self.force = force
        self.threads = threads
        self.status = JobStatus.queued
        self.done = 0
        self.total = 0
        self.current_node: str | None = None
        self.failed: dict[str, str] = {}
        self.blocked: list[str] = []
        self.log: deque[tuple[int, str, str | None]] = deque(maxlen=log_limit)
        self.return_code: int | None = None
        self.submitted_at = time.time()
        self.started_at: float | None = None
        self.finished_at: float | None = None
        self._manager = manager
        self._process: subprocess.Popen[str] | None = None
        self._finished = threading.Event()
        self._lock = threading.Lock()

    @property
    def progress(self) -> float:
        return self.done / self.total if self.total else (1.0 if self.status is JobStatus.succeeded else 0.0)

    @property
    def duration(self) -> float | None:
        if self.started_at is None:
            return None

        return (self.finished_at or time.time()) - self.started_at

    def pause(self) -> None:
        if self.status is JobStatus.running and self._send("pause"):
            self._set_status(JobStatus.paused)

    def resume(self) -> None:
        if self.status is JobStatus.paused and self._send("resume"):
            self._set_status(JobStatus.running)

    def cancel(self) -> None:
        if self.status is JobStatus.queued:
            self._manager._dequeue(self)
            self._finish(JobStatus.cancelled)
            return

        if self.status.finished or self._process is None:
            return

        if not self._send("cancel"):
            self._process.terminate()

        threading.Timer(10, self._kill_if_alive).start()

    def wait(self, timeout: float | None = None) -> bool:
        return self._finished.wait(timeout)

    def command(self) -> list[str]:
        command = [sys.executable, "-m", "bolt", "--no-stdlib"]

        for source in self._manager.plugin_sources:
            command += ["--plugin", source]

        command += ["cook", self.graph_path, "--events", "--control"]

        for target in self.targets:
            command += ["--target", target]

        for name, value in self.variables.items():
            command += ["--set", f"{name}={json.dumps(value)}"]

        if self.force:
            command.append("--force")

        if self.threads > 1:
            command += ["--jobs", str(self.threads)]

        return command

    def _start(self) -> None:
        environment = dict(os.environ)
        package_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        environment["PYTHONPATH"] = os.pathsep.join(filter(None, (package_root, environment.get("PYTHONPATH"))))
        environment["PYTHONUNBUFFERED"] = "1"
        self.started_at = time.time()

        try:
            self._process = subprocess.Popen(self.command(), cwd=self.directory, env=environment,
                                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                             text=True, errors="replace", bufsize=1)
        except OSError as error:
            self._add_log(logging.ERROR, f"cannot start the job process: {error}", None)
            self._finish(JobStatus.failed)
            return

        self._set_status(JobStatus.running)
        threading.Thread(target=self._read_stderr, name=f"bolt-job-{self.id}-stderr", daemon=True).start()
        threading.Thread(target=self._read_events, name=f"bolt-job-{self.id}", daemon=True).start()

    def _read_events(self) -> None:
        process = self._process
        status = None

        for line in process.stdout:
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                self._add_log(logging.INFO, line.rstrip("\n"), None)
                continue

            status = self._handle(data) or status

        return_code = process.wait()
        self.return_code = return_code

        if status is None:
            status = JobStatus.succeeded if return_code == 0 else JobStatus.failed

        self._finish(status)

    def _read_stderr(self) -> None:
        for line in self._process.stderr:
            self._add_log(logging.WARNING, line.rstrip("\n"), None)

    def _handle(self, data: Mapping[str, Any]) -> JobStatus | None:
        kind = data.get("event")

        if kind == "started":
            self.total = data.get("nodes", 0)
        elif kind == "progress":
            self.done = data.get("done", 0)
            self.total = data.get("total", self.total)
        elif kind == "node_started":
            self.current_node = data.get("node")
        elif kind == "log":
            self._add_log(data.get("level", logging.INFO), data.get("message", ""), data.get("node"))
            return None
        elif kind == "node_failed":
            self.failed[data["node"]] = data.get("error", "")
            self._add_log(logging.ERROR, f"{data['node']} failed: {data.get('error', '')}", data["node"])
        elif kind == "node_blocked":
            self.blocked.append(data["node"])
        elif kind == "finished":
            return JobStatus(data.get("status", "failed"))
        else:
            return None

        self._manager._emit(JobChanged, self)

        return None

    def _add_log(self, level: int, message: str, node: str | None) -> None:
        self.log.append((level, message, node))
        self._manager._emit(JobLog, self, level, message, node)

    def _send(self, command: str) -> bool:
        process = self._process

        if process is None or process.poll() is not None or process.stdin is None:
            return False

        try:
            process.stdin.write(command + "\n")
            process.stdin.flush()
            return True
        except (BrokenPipeError, OSError, ValueError):
            return False

    def _kill_if_alive(self) -> None:
        if self._process is not None and self._process.poll() is None:
            self._process.kill()

    def _set_status(self, status: JobStatus) -> None:
        self.status = status
        self._manager._emit(JobChanged, self)

    def _finish(self, status: JobStatus) -> None:
        with self._lock:
            if self._finished.is_set():
                return

            self.finished_at = time.time()
            self.current_node = None

            if self._process is not None and self._process.stdin is not None:
                try:
                    self._process.stdin.close()
                except OSError:
                    pass

            self.status = status
            self._finished.set()

        self._manager._emit(JobChanged, self)
        self._manager._job_finished(self)

    def __repr__(self) -> str:
        return f"<Job {self.id} {self.name!r} {self.status.value}>"


class JobManager:
    """Runs graph snapshots in child processes, a limited number at a time, and reports their progress as events."""

    def __init__(self,
                 registry: Registry | None = None,
                 *,
                 max_running: int = 2,
                 directory: str | None = None,
                 events: EventBus | None = None) -> None:
        self.events = events if events is not None else EventBus()
        self.max_running = max_running
        self.directory = directory or os.path.join(tempfile.gettempdir(), "bolt_jobs")
        self.plugin_sources = registry.plugin_sources() if registry is not None else []
        self._jobs: list[Job] = []
        self._queue: deque[Job] = deque()
        self._lock = threading.Lock()

    def jobs(self) -> list[Job]:
        with self._lock:
            return list(self._jobs)

    def submit(self,
               graph: Graph | str | os.PathLike[str],
               *,
               name: str | None = None,
               targets: Iterable[str] = (),
               variables: Mapping[str, Any] | None = None,
               force: bool = False,
               threads: int = 1) -> Job:
        job_directory = tempfile.mkdtemp(prefix="job_", dir=self._ensure_directory())
        graph_path = os.path.join(job_directory, "graph.bolt")

        if isinstance(graph, (str, os.PathLike)):
            shutil.copyfile(graph, graph_path)
            default_name = os.path.splitext(os.path.basename(os.fspath(graph)))[0]
        else:
            save_graph(graph, graph_path)
            default_name = graph.name

        job = Job(self, name or default_name, graph_path, job_directory, targets, variables, force, threads)

        with self._lock:
            self._jobs.append(job)
            self._queue.append(job)

        self._emit(JobAdded, job)
        self._schedule()

        return job

    def remove(self, job: Job) -> None:
        if not job.status.finished:
            raise ValueError(f"job {job.id} is still {job.status.value}")

        with self._lock:
            if job not in self._jobs:
                return

            self._jobs.remove(job)

        shutil.rmtree(job.directory, ignore_errors=True)
        self._emit(JobRemoved, job)

    def clear_finished(self) -> None:
        for job in self.jobs():
            if job.status.finished:
                self.remove(job)

    def cancel_all(self) -> None:
        for job in self.jobs():
            job.cancel()

    def wait(self, timeout: float | None = None) -> bool:
        deadline = None if timeout is None else time.monotonic() + timeout

        for job in self.jobs():
            remaining = None if deadline is None else max(0.0, deadline - time.monotonic())

            if not job.wait(remaining):
                return False

        return True

    def _ensure_directory(self) -> str:
        os.makedirs(self.directory, exist_ok=True)

        return self.directory

    def _schedule(self) -> None:
        to_start = []

        with self._lock:
            running = sum(1 for job in self._jobs if job.status in (JobStatus.running, JobStatus.paused)
                          or (job.started_at is not None and not job.status.finished))

            while self._queue and running < self.max_running:
                job = self._queue.popleft()
                job.started_at = time.time()
                to_start.append(job)
                running += 1

        for job in to_start:
            job._start()

    def _dequeue(self, job: Job) -> None:
        with self._lock:
            if job in self._queue:
                self._queue.remove(job)

    def _job_finished(self, job: Job) -> None:
        self._schedule()

    def _emit(self, event_type: type[JobEvent], *args: Any) -> None:
        self.events.emit(event_type, *args)
