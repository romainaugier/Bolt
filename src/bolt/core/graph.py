from __future__ import annotations

import threading
from collections import deque
from collections.abc import Callable, Iterable, Iterator, Mapping
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Union

from bolt.core import events
from bolt.core.errors import GraphBusyError, GraphError, InvalidConnectionError, NodeNotFoundError
from bolt.core.events import EventBus
from bolt.core.names import name_root, validate_name
from bolt.core.node import Node
from bolt.core.plugs import Plug, PlugKind

if TYPE_CHECKING:
    from bolt.core.evaluation import Control, EvaluationResult
    from bolt.core.executors import Executor
    from bolt.core.registry import Registry

NodeRef = Union[Node, str]
PlugRef = Union[Plug, str]
TargetRef = Union[Node, Plug, str]

_busy_lock = threading.Lock()


class Connection:
    __slots__ = ("source", "target", "convert", "seen")

    def __init__(self, source: Plug, target: Plug, convert: Callable[[Any], Any] | None) -> None:
        self.source = source
        self.target = target
        self.convert = convert
        self.seen = -1

    def __repr__(self) -> str:
        return f"<Connection {self.source.path} -> {self.target.path}>"


class Graph:
    """A directed acyclic graph of nodes. Subgraphs are graphs owned by a node."""

    __slots__ = ("registry", "events", "name", "owner", "_context", "_nodes", "_variables", "_order", "_evaluating",
                 "_name_counters", "__weakref__")

    def __init__(self,
                 registry: Registry,
                 *,
                 name: str = "root",
                 events: EventBus | None = None,
                 owner: Node | None = None,
                 context: Any = None) -> None:
        self.registry = registry
        self.events = events if events is not None else EventBus()
        self.name = name
        self.owner = owner
        self._context = context
        self._nodes: dict[str, Node] = {}
        self._variables: dict[str, Any] = {}
        self._order: list[Node] | None = None
        self._evaluating = 0
        self._name_counters: dict[str, int] = {}

    @property
    def parent(self) -> Graph | None:
        return self.owner.graph if self.owner is not None else None

    @property
    def root(self) -> Graph:
        graph = self

        while graph.owner is not None and graph.owner.graph is not None:
            graph = graph.owner.graph

        return graph

    @property
    def path(self) -> str:
        return self.owner.path if self.owner is not None else ""

    @property
    def context(self) -> Any:
        """Object provided by the host application, shared with subgraphs and visible to nodes as ctx.context."""
        if self._context is not None:
            return self._context

        parent = self.parent

        return parent.context if parent is not None else None

    @context.setter
    def context(self, context: Any) -> None:
        self._context = context

    @property
    def is_evaluating(self) -> bool:
        return self.root._evaluating > 0

    @property
    def variables(self) -> Mapping[str, Any]:
        return MappingProxyType(self._variables)

    def set_variable(self, name: str, value: Any) -> None:
        validate_name(name, "variable name")
        self._variables[name] = value
        self.events.emit(events.VariableChanged, self, name)

    def remove_variable(self, name: str) -> None:
        if self._variables.pop(name, None) is not None:
            self.events.emit(events.VariableChanged, self, name)

    def __len__(self) -> int:
        return len(self._nodes)

    def __iter__(self) -> Iterator[Node]:
        return iter(self._nodes.values())

    def __contains__(self, item: object) -> bool:
        if isinstance(item, Node):
            return item.graph is self
        return item in self._nodes

    def nodes(self) -> list[Node]:
        return list(self._nodes.values())

    def node(self, name: str) -> Node:
        node = self._nodes.get(name)

        if node is None:
            raise NodeNotFoundError(f"graph '{self.path or self.name}' has no node named '{name}'")

        return node

    def find_node(self, name: str) -> Node | None:
        return self._nodes.get(name)

    def displayed_nodes(self) -> list[Node]:
        return [node for node in self._nodes.values() if node.displayed]

    def walk(self) -> Iterator[Node]:
        for node in self._nodes.values():
            yield node

            for child in node.child_graphs():
                yield from child.walk()

    def unique_name(self, base: str) -> str:
        if base not in self._nodes:
            return base

        root = name_root(base)
        counter = self._name_counters.get(root, 0)

        while True:
            counter += 1
            candidate = f"{root}_{counter}"

            if candidate not in self._nodes:
                self._name_counters[root] = counter
                return candidate

    def create_node(self, type_name: str, name: str | None = None, values: Mapping[str, Any] | None = None) -> Node:
        node = self.registry.create_node(type_name, name)
        self.add_node(node, unique=name is None)

        if values:
            for plug_name, value in values.items():
                node.set(plug_name, value)

        return node

    def add_node(self, node: Node, *, unique: bool = True) -> Node:
        self._check_editable()

        if node.graph is not None:
            raise GraphError(f"node {node.path} already belongs to a graph")

        if node.name in self._nodes:
            if not unique:
                raise GraphError(f"graph '{self.path or self.name}' already has a node named '{node.name}'")

            node._name = self.unique_name(node.name)

        node._attach(self)
        self._nodes[node.name] = node
        self._order = None
        node.touch()
        self.events.emit(events.NodeAdded, self, node)

        return node

    def remove_node(self, node: NodeRef, *, force: bool = False) -> None:
        self._check_editable()
        node = self._resolve_node(node)

        if not node.removable and not force:
            raise GraphError(f"node {node.path} cannot be removed")

        for plug in node.plugs():
            self._disconnect_all(plug)

        del self._nodes[node.name]

        self._order = None
        node._detach()
        self.events.emit(events.NodeRemoved, self, node)

    def rename_node(self, node: NodeRef, name: str) -> None:
        node = self._resolve_node(node)
        validate_name(name, "node name")

        if name == node.name:
            return

        if name in self._nodes:
            raise GraphError(f"graph '{self.path or self.name}' already has a node named '{name}'")

        old_name = node.name
        nodes = self._nodes
        self._nodes = {name if key == old_name else key: value for key, value in nodes.items()}
        node._name = name
        self.events.emit(events.NodeRenamed, self, node, old_name)

    def plug(self, reference: PlugRef) -> Plug:
        if isinstance(reference, Plug):
            if reference.node.graph is not self:
                raise GraphError(f"plug {reference.path} does not belong to this graph")

            return reference

        node_name, separator, plug_name = reference.partition(".")

        if not separator:
            raise GraphError(f"invalid plug reference {reference!r}, expected 'node.plug'")

        return self.node(node_name).plug(plug_name)

    def can_connect(self, source: Plug, target: Plug) -> bool:
        """Whether connect(source, target) would succeed, without changing anything."""
        if source.kind is not PlugKind.output or target.kind is not PlugKind.input:
            return False

        if source.node.graph is not self or target.node.graph is not self or source.node is target.node:
            return False

        if self.registry.converter(source.data_type, target.data_type) is False:
            return False

        return not self._reaches(target.node, source.node)

    def connect(self, source: PlugRef, target: PlugRef) -> Connection:
        self._check_editable()
        source = self.plug(source)
        target = self.plug(target)

        if source.kind is not PlugKind.output:
            raise InvalidConnectionError(f"{source.path} is not an output")

        if target.kind is not PlugKind.input:
            raise InvalidConnectionError(f"{target.path} is not an input")

        for existing in target.connections:
            if existing.source is source:
                return existing

        if source.node is target.node or self._reaches(target.node, source.node):
            raise InvalidConnectionError(f"connecting {source.path} to {target.path} would create a cycle")

        convert = self.registry.converter(source.data_type, target.data_type)

        if convert is False:
            raise InvalidConnectionError(f"cannot connect {source.path} ({source.spec.type_name}) "
                                         f"to {target.path} ({target.spec.type_name})")

        if not target.spec.multi and target.connections:
            self._remove_connection(target.connections[0])

        connection = Connection(source, target, convert)
        source.connections.append(connection)
        target.connections.append(connection)
        self._order = None
        target.node.touch()
        self.events.emit(events.Connected, self, connection)

        return connection

    def disconnect(self, source: PlugRef, target: PlugRef) -> bool:
        self._check_editable()
        source = self.plug(source)
        target = self.plug(target)

        for connection in target.connections:
            if connection.source is source:
                self._remove_connection(connection)
                return True

        return False

    def disconnect_plug(self, plug: PlugRef) -> None:
        self._check_editable()
        self._disconnect_all(self.plug(plug))

    def connections(self) -> list[Connection]:
        return [connection
                for node in self._nodes.values()
                for plug in node.input_plugs()
                for connection in plug.connections]

    def topological_order(self) -> list[Node]:
        if self._order is None:
            pending = {node: len(node.upstream_nodes()) for node in self._nodes.values()}
            ready = deque(node for node, count in pending.items() if count == 0)
            order: list[Node] = []

            while ready:
                node = ready.popleft()
                order.append(node)

                for downstream in node.downstream_nodes():
                    pending[downstream] -= 1

                    if pending[downstream] == 0:
                        ready.append(downstream)

            self._order = order

        return list(self._order)

    def evaluate(self,
                 targets: TargetRef | Iterable[TargetRef] | None = None,
                 *,
                 variables: Mapping[str, Any] | None = None,
                 executor: Executor | None = None,
                 control: Control | None = None,
                 force: bool = False,
                 strict: bool = False) -> EvaluationResult:
        from bolt.core.evaluation import Evaluation

        return Evaluation(self,variables=variables,
                          control=control,
                          force=force,
                          strict=strict).execute(targets,
                                                 executor)

    def pull(self,
             plug: PlugRef,
             *,
             variables: Mapping[str, Any] | None = None,
             executor: Executor | None = None,
             control: Control | None = None) -> Any:
        from bolt.core.errors import Cancelled, CookError

        plug = self.plug(plug)

        if plug.kind is not PlugKind.output:
            raise GraphError(f"can only pull outputs, {plug.path} is an {plug.kind.value}")

        result = self.evaluate(plug.node, variables=variables, executor=executor, control=control)

        if result.cancelled:
            raise Cancelled(f"evaluation of {plug.path} was cancelled")

        if not result.succeeded:
            node, error = next(iter(result.failed.items()))
            raise CookError(f"cannot pull {plug.path}: {node.path} failed: {error}")

        return plug.value

    def stale_nodes(self,
                    targets: TargetRef | Iterable[TargetRef] | None = None,
                    *,
                    variables: Mapping[str, Any] | None = None) -> list[Node]:
        from bolt.core.evaluation import Evaluation

        return Evaluation(self, variables=variables).stale_nodes(targets)

    def _check_editable(self) -> None:
        if self.root._evaluating:
            raise GraphBusyError("the graph structure cannot change while it is being evaluated")

    def _begin_evaluation(self) -> None:
        root = self.root

        with _busy_lock:
            root._evaluating += 1

    def _end_evaluation(self) -> None:
        root = self.root

        with _busy_lock:
            root._evaluating -= 1

    def _resolve_node(self, node: NodeRef) -> Node:
        if isinstance(node, Node):
            if node.graph is not self:
                raise NodeNotFoundError(f"node {node.path} does not belong to graph '{self.path or self.name}'")

            return node

        return self.node(node)

    def _reaches(self, start: Node, goal: Node) -> bool:
        visited = {start}
        stack = [start]

        while stack:
            node = stack.pop()

            for plug in node.output_plugs():
                for connection in plug.connections:
                    downstream = connection.target.node

                    if downstream is goal:
                        return True

                    if downstream not in visited:
                        visited.add(downstream)
                        stack.append(downstream)

        return False

    def _disconnect_all(self, plug: Plug) -> None:
        for connection in list(plug.connections):
            self._remove_connection(connection)

    def _remove_connection(self, connection: Connection) -> None:
        connection.source.connections.remove(connection)
        connection.target.connections.remove(connection)
        self._order = None
        connection.target.node.touch()
        self.events.emit(events.Disconnected, self, connection)

    def __repr__(self) -> str:
        return f"<Graph {self.path or self.name!r} nodes={len(self._nodes)}>"
