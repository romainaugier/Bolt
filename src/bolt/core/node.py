from __future__ import annotations

import enum
import itertools
import uuid
from collections.abc import Iterable, Iterator, Mapping
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, ClassVar

from bolt.core import events
from bolt.core.errors import GraphError, PlugNotFoundError
from bolt.core.names import sanitize_name, validate_name, validate_type_name
from bolt.core.plugs import Input, Output, Parameter, Plug, PlugKind, PlugSpec

if TYPE_CHECKING:
    from bolt.core.evaluation import CookContext, Evaluation
    from bolt.core.graph import Connection, Graph

_stamps = itertools.count(1)


def next_stamp() -> int:
    return next(_stamps)


class NodeState(enum.Enum):
    uncooked = "uncooked"
    cooking = "cooking"
    cooked = "cooked"
    failed = "failed"
    blocked = "blocked"


class Node:
    """Base class of every node type. Declare plugs with the inputs/parameters/outputs tuples and implement cook()."""

    type_name: ClassVar[str] = ""
    version: ClassVar[int] = 1
    category: ClassVar[str] = ""
    description: ClassVar[str] = ""
    ui: ClassVar[Mapping[str, Any]] = MappingProxyType({})
    inputs: ClassVar[tuple[Input, ...]] = ()
    parameters: ClassVar[tuple[Parameter, ...]] = ()
    outputs: ClassVar[tuple[Output, ...]] = ()
    context_dependencies: ClassVar[frozenset[str]] = frozenset()
    always_cook: ClassVar[bool] = False
    passthrough: ClassVar[Mapping[str, str] | None] = None
    removable: ClassVar[bool] = True
    user_plugs: ClassVar[bool] = False
    plug_specs: ClassVar[tuple[PlugSpec, ...]] = ()

    __slots__ = ("id", "metadata", "state", "error", "cook_time",
                 "_name", "_graph", "_plugs", "_disabled", "_displayed", "_modified_at", "_cooked_at", "_snapshot",
                 "__weakref__")

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        for declared, expected in ((cls.inputs, Input), (cls.parameters, Parameter), (cls.outputs, Output)):
            for spec in declared:
                if not isinstance(spec, expected):
                    raise TypeError(f"{cls.__name__}: {spec!r} must be declared as {expected.__name__}")

        specs = (*cls.inputs, *cls.parameters, *cls.outputs)
        seen: set[str] = set()

        for spec in specs:
            if spec.name in seen:
                raise TypeError(f"{cls.__name__}: duplicate plug name '{spec.name}'")

            seen.add(spec.name)

        cls.plug_specs = specs
        cls.context_dependencies = frozenset(cls.context_dependencies)

        if cls.type_name:
            validate_type_name(cls.type_name)

    def __init__(self, name: str | None = None) -> None:
        self.id = uuid.uuid4().hex
        self.metadata: dict[str, Any] = {}
        self.state = NodeState.uncooked
        self.error: str | None = None
        self.cook_time: float | None = None
        self._name = validate_name(name, "node name") if name is not None else self.default_name()
        self._graph: Graph | None = None
        self._plugs = {spec.name: Plug(spec, self) for spec in self.plug_specs}
        self._disabled = False
        self._displayed = False
        self._modified_at = next_stamp()
        self._cooked_at = 0
        self._snapshot: dict[str, Any] = {}

    @classmethod
    def default_name(cls) -> str:
        return sanitize_name(cls.type_name.rpartition(".")[2] or cls.__name__)

    @classmethod
    def migrate(cls, data: dict[str, Any], from_version: int) -> dict[str, Any]:
        """Upgrade serialized node data written by an older version of this node type."""
        return data

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, name: str) -> None:
        if self._graph is not None:
            self._graph.rename_node(self, name)
        else:
            self._name = validate_name(name, "node name")

    @property
    def graph(self) -> Graph | None:
        return self._graph

    @property
    def path(self) -> str:
        prefix = self._graph.path if self._graph is not None else ""
        return f"{prefix}/{self._name}"

    @property
    def disabled(self) -> bool:
        return self._disabled

    @disabled.setter
    def disabled(self, disabled: bool) -> None:
        disabled = bool(disabled)

        if disabled == self._disabled:
            return

        self._disabled = disabled
        self.touch()

        if self._graph is not None:
            self._graph.events.emit(events.NodeChanged, self._graph, self, "disabled")

    @property
    def displayed(self) -> bool:
        return self._displayed

    @displayed.setter
    def displayed(self, displayed: bool) -> None:
        displayed = bool(displayed)

        if displayed == self._displayed:
            return

        self._displayed = displayed

        if self._graph is not None:
            self._graph.events.emit(events.NodeChanged, self._graph, self, "displayed")

    def plug(self, name: str) -> Plug:
        plug = self._plugs.get(name)

        if plug is None:
            raise PlugNotFoundError(f"node {self.path} has no plug '{name}'")

        return plug

    __getitem__ = plug

    def has_plug(self, name: str) -> bool:
        return name in self._plugs

    def plugs(self, kind: PlugKind | None = None) -> Iterator[Plug]:
        if kind is None:
            return iter(self._plugs.values())

        return (plug for plug in self._plugs.values() if plug.kind is kind)

    def input_plugs(self) -> Iterator[Plug]:
        return self.plugs(PlugKind.input)

    def parameter_plugs(self) -> Iterator[Plug]:
        return self.plugs(PlugKind.parameter)

    def output_plugs(self) -> Iterator[Plug]:
        return self.plugs(PlugKind.output)

    def declared_plugs(self, kind: PlugKind) -> Iterator[Plug]:
        """Plugs declared as kind, whether or not they were promoted on this node."""
        return (plug for plug in self._plugs.values() if plug.spec.kind is kind)

    def dynamic_plugs(self) -> Iterator[Plug]:
        return (plug for plug in self._plugs.values() if plug.dynamic)

    def get(self, name: str) -> Any:
        plug = self.plug(name)
        return plug.value if plug.kind is PlugKind.output else plug.raw

    def set(self, name: str, value: Any) -> None:
        self.plug(name).set(value)

    def add_plug(self, spec: PlugSpec) -> Plug:
        if spec.name in self._plugs:
            raise GraphError(f"node {self.path} already has a plug named '{spec.name}'")

        graph = self._graph
        plug = Plug(spec, self, dynamic=True)

        if graph is not None:
            graph._check_editable()
            plug.bind(graph.registry.data_type(spec.data_type))

        self._plugs[spec.name] = plug
        self.touch()

        if graph is not None:
            graph.events.emit(events.PlugAdded, graph, plug)

        return plug

    def remove_plug(self, name: str) -> None:
        plug = self.plug(name)

        if not plug.dynamic:
            raise GraphError(f"plug {plug.path} is declared by the node type and cannot be removed")

        graph = self._graph

        if graph is not None:
            graph._check_editable()
            graph.disconnect_plug(plug)

        del self._plugs[name]

        self.touch()

        if graph is not None:
            graph.events.emit(events.PlugRemoved, graph, self, name)

    def set_plug_kind(self, name: str, kind: PlugKind) -> Plug:
        """Promote an input to a parameter or a parameter to an input, on this node only. The cook reads it the same
        way with ctx.get(). Only plugs of editable data types can become parameters, and only once disconnected."""
        plug = self.plug(name)

        if plug.kind is kind:
            return plug

        error = plug.kind_error(kind)

        if error is not None:
            raise GraphError(error)

        if plug.connections:
            raise GraphError(f"disconnect {plug.path} before making it a {kind.value}")

        graph = self._graph

        if graph is not None:
            graph._check_editable()

        plug._kind = kind
        plug.version += 1
        self.touch()

        if graph is not None:
            graph.events.emit(events.PlugKindChanged, graph, plug)

        return plug

    def add_user_plug(self, spec: PlugSpec) -> Plug:
        """Add a plug on behalf of a user, for node types declaring user_plugs. Subgraphs mirror it inside."""
        return self.add_plug(spec)

    def remove_user_plug(self, name: str) -> None:
        self.remove_plug(name)

    def touch(self) -> None:
        self._modified_at = next_stamp()

    def upstream_nodes(self) -> list[Node]:
        return list(dict.fromkeys(connection.source.node
                                  for plug in self.input_plugs()
                                  for connection in plug.connections))

    def downstream_nodes(self) -> list[Node]:
        return list(dict.fromkeys(connection.target.node
                                  for plug in self.output_plugs()
                                  for connection in plug.connections))

    def child_graphs(self) -> tuple[Graph, ...]:
        return ()

    def cook(self, ctx: CookContext) -> None:
        raise NotImplementedError(f"{type(self).__name__} does not implement cook()")

    def active_connections(self, evaluation: Evaluation) -> Iterable[Connection] | None:
        """Inbound connections this cook will read. None means all of them; override to evaluate lazily."""
        return None

    def has_internal_changes(self, evaluation: Evaluation, since: int) -> bool:
        return False

    def on_attached(self) -> None:
        pass

    def on_detached(self) -> None:
        pass

    def save_extra(self) -> dict[str, Any] | None:
        return None

    def load_extra(self, data: Mapping[str, Any]) -> None:
        pass

    def _attach(self, graph: Graph) -> None:
        resolved = [(plug, graph.registry.data_type(plug.spec.data_type)) for plug in self._plugs.values()]

        for plug, data_type in resolved:
            plug.bind(data_type)

        self._graph = graph
        self.on_attached()

    def _detach(self) -> None:
        self.on_detached()
        self._graph = None

    def _value_changed(self, plug: Plug) -> None:
        self.touch()
        graph = self._graph

        if graph is not None:
            graph.events.emit(events.ValueChanged, graph, plug)

    def _mark_cooked(self) -> None:
        self.state = NodeState.cooked
        self.error = None
        self._cooked_at = next_stamp()

    def _passthrough(self, ctx: CookContext) -> None:
        mapping = self.passthrough

        if mapping is None:
            first_input = next(self.declared_plugs(PlugKind.input), None)
            first_output = next(self.output_plugs(), None)
            mapping = {first_output.name: first_input.name} if first_input and first_output else {}

        for plug in self.output_plugs():
            source = mapping.get(plug.name)
            ctx.set(plug.name, ctx.get(source) if source is not None else plug._default())

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self.path} ({self.state.value})>"
