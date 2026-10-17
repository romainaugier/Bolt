from __future__ import annotations

import enum
import logging
import os
import threading
import time
import traceback
from collections import ChainMap
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from bolt.core import events
from bolt.core.changes import Change, ChangeKind
from bolt.core.errors import BoltError, Cancelled, CookError, ExpressionError, InvalidValueError
from bolt.core.expressions import Expander, missing
from bolt.core.node import Node, NodeState, next_stamp
from bolt.core.plugs import Plug, PlugKind, unset

if TYPE_CHECKING:
    from bolt.core.executors import Executor
    from bolt.core.graph import Connection, Graph, TargetRef

logger = logging.getLogger("bolt.evaluation")
node_logger = logging.getLogger("bolt.node")


class Control:
    """Lets another thread pause, resume or cancel a running evaluation."""

    __slots__ = ("_cancelled", "_running")

    def __init__(self) -> None:
        self._cancelled = False
        self._running = threading.Event()
        self._running.set()

    @property
    def cancelled(self) -> bool:
        return self._cancelled

    @property
    def paused(self) -> bool:
        return not self._running.is_set()

    def cancel(self) -> None:
        self._cancelled = True
        self._running.set()

    def pause(self) -> None:
        if not self._cancelled:
            self._running.clear()

    def resume(self) -> None:
        self._running.set()

    def checkpoint(self) -> None:
        self._running.wait()
        if self._cancelled:
            raise Cancelled("evaluation cancelled")


class EvaluationStatus(enum.Enum):
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"


@dataclass(slots=True, eq=False)
class EvaluationResult:
    status: EvaluationStatus
    cooked: list[Node] = field(default_factory=list)
    fresh: list[Node] = field(default_factory=list)
    failed: dict[Node, str] = field(default_factory=dict)
    blocked: list[Node] = field(default_factory=list)
    duration: float = 0.0

    @property
    def succeeded(self) -> bool:
        return self.status is EvaluationStatus.succeeded

    @property
    def cancelled(self) -> bool:
        return self.status is EvaluationStatus.cancelled


class CookContext:
    """What a node sees while cooking: its input values, its outputs, the variables, logging and progress."""

    __slots__ = ("node", "evaluation", "variables", "used", "_expander")

    def __init__(self, node: Node, evaluation: Evaluation) -> None:
        self.node = node
        self.evaluation = evaluation
        self.variables = evaluation.variables_for(node.graph)
        self.used: dict[str, Any] = {name: self.variables.get(name, missing) for name in node.context_dependencies}
        self._expander: Expander | None = None

    @property
    def graph(self) -> Graph:
        return self.node.graph

    @property
    def cancelled(self) -> bool:
        return self.evaluation.control.cancelled

    def get(self, name: str) -> Any:
        plug = self.node.plug(name)
        kind = plug.kind

        if kind is PlugKind.output:
            return plug.value

        if kind is PlugKind.input:
            connections = plug.connections

            if connections:
                if plug.spec.multi:
                    return [_pull(connection) for connection in connections]

                return _pull(connections[0])

            if plug.spec.required:
                raise CookError(f"required input {plug.path} is not connected")

            if plug.spec.multi:
                return []

        return self.resolve(plug)

    def resolve(self, plug: Plug) -> Any:
        if not plug.is_expression:
            return plug.raw

        try:
            return plug.data_type.resolve(plug.raw, self.expander)
        except (ExpressionError, InvalidValueError) as error:
            raise CookError(f"{plug.path}: {error}") from error

    def connection_count(self, name: str) -> int:
        return len(self.node.plug(name).connections)

    def get_item(self, name: str, index: int) -> Any:
        return _pull(self.node.plug(name).connections[index])

    def set(self, name: str, value: Any, delta: Any = unset) -> None:
        """Write an output. Pass delta when the node knows what changed, otherwise the data type diffs the values."""
        plug = self.node.plug(name)

        if plug.kind is not PlugKind.output:
            raise CookError(f"{plug.path} is not an output")

        previous = plug.value
        recorded = plug.publish(value, delta)

        if recorded is not None and self.evaluation.strict:
            _verify_delta(plug, previous, value, recorded)

    def change(self, name: str) -> Change:
        """The value of an input or parameter and how it changed since this node last cooked successfully."""
        plug = self.node.plug(name)

        if plug.kind is PlugKind.input and plug.connections:
            if plug.spec.multi:
                raise CookError(f"{plug.path} accepts several connections, use changes()")

            return _connection_change(plug.connections[0])

        return self._local_change(plug)

    def changes(self, name: str) -> list[Change]:
        """One change per connection of a multi input, in connection order."""
        plug = self.node.plug(name)

        return [_connection_change(connection) for connection in plug.connections]

    def changed(self) -> list[str]:
        """Names of the inputs and parameters whose value may have changed since this node last cooked."""
        names = []

        for plug in self.node.plugs():
            kind = plug.kind

            if kind is PlugKind.output:
                continue

            if kind is PlugKind.input and plug.connections:
                if any(connection.seen != connection.source.version for connection in plug.connections):
                    names.append(plug.name)
            elif plug.seen != plug.version or plug.is_expression:
                names.append(plug.name)

        return names

    @property
    def context(self) -> Any:
        return self.node.graph.context

    def _local_change(self, plug: Plug) -> Change:
        value = self.get(plug.name)

        if plug.seen == plug.version and not plug.is_expression:
            return Change(ChangeKind.unchanged, value)

        return Change(ChangeKind.replaced, value)

    def variable(self, name: str, default: Any = None) -> Any:
        value = self.variables.get(name, missing)
        self.used[name] = value
        return default if value is missing else value

    @property
    def expander(self) -> Expander:
        if self._expander is None:
            self._expander = Expander(self.variables, self.used)

        return self._expander

    def expand(self, text: str) -> Any:
        return self.expander(text)

    def checkpoint(self) -> None:
        self.evaluation.control.checkpoint()

    def progress(self, fraction: float) -> None:
        self.node.graph.events.emit(events.NodeProgress, self.node.graph, self.node, min(max(fraction, 0.0), 1.0))

    def log(self, level: int, message: str) -> None:
        node_logger.log(level, "%s: %s", self.node.path, message)
        self.node.graph.events.emit(events.NodeLog, self.node.graph, self.node, level, message)

    def debug(self, message: str) -> None:
        self.log(logging.DEBUG, message)

    def info(self, message: str) -> None:
        self.log(logging.INFO, message)

    def warning(self, message: str) -> None:
        self.log(logging.WARNING, message)

    def error(self, message: str) -> None:
        self.log(logging.ERROR, message)


def _pull(connection: Connection) -> Any:
    value = connection.source.value
    convert = connection.convert

    return value if convert is None else convert(value)


def _connection_change(connection: Connection) -> Change:
    source = connection.source
    value = _pull(connection)
    seen = connection.seen

    if seen == source.version:
        return Change(ChangeKind.unchanged, value)

    history = source.history

    if history is None:
        source.track()
        return Change(ChangeKind.replaced, value)

    if connection.convert is not None or seen < 0 or not history or history[0][0] > seen + 1:
        return Change(ChangeKind.replaced, value)

    merge = source.data_type.merge
    delta = None

    for version, step in history:
        if version <= seen:
            continue

        if step is None:
            return Change(ChangeKind.replaced, value)

        delta = step if delta is None else merge(delta, step)

        if delta is None:
            return Change(ChangeKind.replaced, value)

    return Change(ChangeKind.delta, value, delta)


def _verify_delta(plug: Plug, previous: Any, value: Any, delta: Any) -> None:
    data_type = plug.data_type
    expected = data_type.apply(previous, delta)

    if expected is NotImplemented:
        return

    fingerprint = data_type.fingerprint
    expected_print = fingerprint(expected)
    matches = expected_print == fingerprint(value) if expected_print is not None else expected == value

    if not matches:
        raise CookError(f"the delta written to {plug.path} does not turn the previous value into the new one")


def _input_fingerprints(evaluation: Evaluation, node: Node) -> list[tuple[Connection, Any]]:
    fingerprints = []

    for connection in evaluation.active_inbound(node):
        source = connection.source

        if source.data_type is None:
            continue

        fingerprint = source.data_type.fingerprint(source.value)

        if fingerprint is not None:
            fingerprints.append((connection, fingerprint))

    return fingerprints


class Evaluation:
    """One evaluation pass over a graph: plans the nodes to visit, decides which are stale and cooks them."""

    def __init__(self,
                 graph: Graph,
                 *,
                 variables: Mapping[str, Any] | None = None,
                 control: Control | None = None,
                 force: bool = False,
                 strict: bool = False) -> None:
        self.graph = graph
        self.variables: dict[str, Any] = dict(variables) if variables else {}
        self.control = control if control is not None else Control()
        self.force = force
        self.strict = strict
        self._chains: dict[Graph, ChainMap[str, Any]] = {}
        self._active: dict[Node, list[Connection]] = {}
        self._unusable: set[Node] = set()
        self._lock = threading.Lock()
        self._done = 0
        self._total = 0
        self.result = EvaluationResult(EvaluationStatus.succeeded)

    def variables_for(self, graph: Graph) -> ChainMap[str, Any]:
        chain = self._chains.get(graph)

        if chain is None:
            maps: list[Mapping[str, Any]] = [self.variables]
            current: Graph | None = graph

            while current is not None:
                maps.append(current._variables)
                current = current.parent

            maps.append(os.environ)
            chain = ChainMap(*maps)
            self._chains[graph] = chain

        return chain

    def parameter(self, node: Node, name: str) -> Any:
        return CookContext(node, self).get(name)

    def active_inbound(self, node: Node) -> list[Connection]:
        active = self._active.get(node)

        if active is None:
            try:
                selected = node.active_connections(self)
            except BoltError:
                selected = None

            if selected is None:
                active = [connection for plug in node.input_plugs() for connection in plug.connections]
            else:
                active = list(selected)

            self._active[node] = active

        return active

    def plan(self, targets: TargetRef | Iterable[TargetRef] | None = None) -> list[Node]:
        roots = self._resolve_targets(targets)
        order: list[Node] = []
        visited: set[Node] = set()

        for root in roots:
            if root in visited:
                continue

            visited.add(root)
            stack = [(root, iter(self.active_inbound(root)))]

            while stack:
                node, upstream = stack[-1]

                for connection in upstream:
                    source = connection.source.node

                    if source not in visited:
                        visited.add(source)
                        stack.append((source, iter(self.active_inbound(source))))
                        break
                else:
                    stack.pop()
                    order.append(node)

        return order

    def is_stale(self, node: Node) -> bool:
        if self.force or node.always_cook or node.state is not NodeState.cooked:
            return True

        stamp = node._cooked_at

        if node._modified_at > stamp:
            return True

        for connection in self.active_inbound(node):
            if connection.source.node._cooked_at > stamp:
                return True

        if node._snapshot:
            variables = self.variables_for(node.graph)

            for name, value in node._snapshot.items():
                if variables.get(name, missing) != value:
                    return True

        return node.has_internal_changes(self, stamp)

    def stale_nodes(self, targets: TargetRef | Iterable[TargetRef] | None = None) -> list[Node]:
        stale: list[Node] = []
        stale_set: set[Node] = set()

        for node in self.plan(targets):
            if self.is_stale(node) or any(connection.source.node in stale_set for connection in self.active_inbound(node)):
                stale.append(node)
                stale_set.add(node)

        return stale

    def execute(self, targets: TargetRef | Iterable[TargetRef] | None = None, executor: Executor | None = None) -> EvaluationResult:
        from bolt.core.executors import SerialExecutor

        graph = self.graph
        start = time.perf_counter()
        graph._begin_evaluation()

        try:
            plan = self.plan(targets)
            self._total = len(plan)
            graph.events.emit(events.EvaluationStarted, graph, len(plan))
            (executor or SerialExecutor()).run(self, plan)

            if self.result.failed or self.result.blocked:
                self.result.status = EvaluationStatus.failed

        except Cancelled:
            self.result.status = EvaluationStatus.cancelled
        finally:
            graph._end_evaluation()
            self.result.duration = time.perf_counter() - start

        graph.events.emit(events.EvaluationFinished, graph, self.result)

        return self.result

    def child(self, graph: Graph) -> Evaluation:
        return Evaluation(graph, variables=self.variables, control=self.control, force=self.force, strict=self.strict)

    def process(self, node: Node) -> None:
        self.control.checkpoint()

        if any(connection.source.node in self._unusable for connection in self.active_inbound(node)):
            self._block(node)
        elif self.is_stale(node):
            self.cook(node)
        else:
            with self._lock:
                self.result.fresh.append(node)

        self._advance()

    def cook(self, node: Node) -> None:
        graph = node.graph
        stamp = next_stamp()
        node.state = NodeState.cooking
        node.error = None
        graph.events.emit(events.NodeCookStarted, graph, node)
        ctx = CookContext(node, self)
        fingerprints = _input_fingerprints(self, node) if self.strict else None
        start = time.perf_counter()
        error: str | None = None

        try:
            if node.disabled:
                node._passthrough(ctx)
            else:
                node.cook(ctx)
            if fingerprints:
                for connection, fingerprint in fingerprints:
                    source = connection.source

                    if source.data_type.fingerprint(source.value) != fingerprint:
                        raise CookError(f"{node.path} modified its input '{connection.target.name}' in place, "
                                        "inputs must be copied before being changed")
        except Cancelled:
            node.state = NodeState.uncooked
            raise
        except (CookError, ExpressionError) as exception:
            error = str(exception)
        except Exception:
            error = traceback.format_exc().rstrip()

        duration = time.perf_counter() - start
        node.cook_time = duration
        node._cooked_at = stamp
        node._snapshot = ctx.used

        if error is None:
            node.state = NodeState.cooked
            self._mark_seen(node)

            with self._lock:
                self.result.cooked.append(node)

            graph.events.emit(events.NodeCooked, graph, node, duration)
        else:
            node.state = NodeState.failed
            node.error = error

            with self._lock:
                self.result.failed[node] = error
                self._unusable.add(node)

            logger.error("%s failed: %s", node.path, error)
            graph.events.emit(events.NodeCookFailed, graph, node, error)

    def _mark_seen(self, node: Node) -> None:
        for plug in node.plugs():
            if plug.kind is not PlugKind.output:
                plug.seen = plug.version

        for connection in self.active_inbound(node):
            connection.seen = connection.source.version

    def _block(self, node: Node) -> None:
        node.state = NodeState.blocked

        with self._lock:
            self.result.blocked.append(node)
            self._unusable.add(node)

        node.graph.events.emit(events.NodeBlocked, node.graph, node)

    def _advance(self) -> None:
        with self._lock:
            self._done += 1
            done = self._done

        self.graph.events.emit(events.EvaluationProgress, self.graph, done, self._total)

    def _resolve_targets(self, targets: TargetRef | Iterable[TargetRef] | None) -> list[Node]:
        graph = self.graph

        if targets is None:
            return graph.nodes()

        if isinstance(targets, (Node, Plug, str)):
            targets = (targets,)

        nodes: list[Node] = []

        for target in targets:
            if isinstance(target, Node):
                nodes.append(graph._resolve_node(target))
            elif isinstance(target, Plug):
                nodes.append(graph.plug(target).node)
            elif "." in target:
                nodes.append(graph.plug(target).node)
            else:
                nodes.append(graph.node(target))

        return nodes
