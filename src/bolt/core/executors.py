from __future__ import annotations

import os
from collections import deque
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from typing import TYPE_CHECKING

from bolt.core.errors import Cancelled

if TYPE_CHECKING:
    from bolt.core.evaluation import Evaluation
    from bolt.core.node import Node


class Executor:
    """Decides in which order and on which threads the planned nodes are processed."""

    def run(self, evaluation: Evaluation, plan: list[Node]) -> None:
        raise NotImplementedError


class SerialExecutor(Executor):
    def run(self, evaluation: Evaluation, plan: list[Node]) -> None:
        for node in plan:
            evaluation.process(node)


class ThreadedExecutor(Executor):
    """Cooks independent branches concurrently. Worth it when nodes release the GIL (subprocesses, I/O, native code)."""

    def __init__(self, max_workers: int | None = None) -> None:
        self.max_workers = max_workers or min(32, (os.cpu_count() or 1) + 4)

    def run(self, evaluation: Evaluation, plan: list[Node]) -> None:
        planned = set(plan)
        pending: dict[Node, int] = {}
        dependents: dict[Node, list[Node]] = {node: [] for node in plan}

        for node in plan:
            upstream = {connection.source.node
                        for connection in evaluation.active_inbound(node)
                        if connection.source.node in planned}
            pending[node] = len(upstream)

            for source in upstream:
                dependents[source].append(node)

        ready = deque(node for node in plan if pending[node] == 0)
        running: dict[Future[None], Node] = {}
        stop: BaseException | None = None

        with ThreadPoolExecutor(max_workers=self.max_workers, thread_name_prefix="bolt") as pool:
            while ready or running:
                while ready and stop is None:
                    node = ready.popleft()
                    running[pool.submit(evaluation.process, node)] = node

                if not running:
                    break

                done, _ = wait(running, return_when=FIRST_COMPLETED)

                for future in done:
                    node = running.pop(future)
                    exception = future.exception()

                    if exception is not None:
                        if stop is None or isinstance(stop, Cancelled):
                            stop = exception

                        continue

                    for dependent in dependents[node]:
                        pending[dependent] -= 1

                        if pending[dependent] == 0:
                            ready.append(dependent)

        if stop is not None:
            raise stop
