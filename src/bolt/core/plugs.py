from __future__ import annotations

import enum
from collections import deque
from collections.abc import Mapping
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, ClassVar

from bolt.core.errors import InvalidValueError
from bolt.core.names import validate_name
from bolt.core.datatypes import DataType

if TYPE_CHECKING:
    from bolt.core.graph import Connection
    from bolt.core.node import Node

_empty_mapping: Mapping[str, Any] = MappingProxyType({})

history_limit = 32
unset: Any = type("Unset", (), {"__repr__": lambda self: "<unset>"})()


class PlugKind(enum.Enum):
    input = "input"
    output = "output"
    parameter = "parameter"


class PlugSpec:
    """Declaration of a plug. Use the Input, Output and Parameter subclasses."""

    __slots__ = ("name", "data_type", "default", "label", "multi", "required", "ui", "description")

    kind: ClassVar[PlugKind]

    def __init__(self,
                 name: str,
                 data_type: str | DataType = "any",
                 default: Any = None,
                 *,
                 label: str | None = None,
                 multi: bool = False,
                 required: bool = False,
                 ui: Mapping[str, Any] | None = None,
                 description: str = "") -> None:
        self.name = validate_name(name, "plug name")
        self.data_type = data_type
        self.default = default
        self.label = label if label is not None else name.replace("_", " ").capitalize()
        self.multi = multi
        self.required = required
        self.ui = MappingProxyType(dict(ui)) if ui else _empty_mapping
        self.description = description

    @property
    def type_name(self) -> str:
        return self.data_type.name if isinstance(self.data_type, DataType) else self.data_type

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"name": self.name, "kind": self.kind.value, "type": self.type_name}

        if self.default is not None:
            data["default"] = self.default

        if self.label != self.name.replace("_", " ").capitalize():
            data["label"] = self.label

        if self.multi:
            data["multi"] = True

        if self.required:
            data["required"] = True

        if self.ui:
            data["ui"] = dict(self.ui)

        if self.description:
            data["description"] = self.description

        return data

    @staticmethod
    def from_dict(data: Mapping[str, Any]) -> PlugSpec:
        spec_class = _spec_classes[PlugKind(data["kind"])]

        return spec_class(data["name"],
                          data.get("type", "any"),
                          data.get("default"),
                          label=data.get("label"),
                          multi=data.get("multi", False),
                          required=data.get("required", False),
                          ui=data.get("ui"),
                          description=data.get("description", ""))

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.name!r}, {self.type_name!r})"


class Input(PlugSpec):
    __slots__ = ()
    kind = PlugKind.input


class Output(PlugSpec):
    __slots__ = ()
    kind = PlugKind.output


class Parameter(PlugSpec):
    __slots__ = ()
    kind = PlugKind.parameter


_spec_classes = {PlugKind.input: Input, PlugKind.output: Output, PlugKind.parameter: Parameter}


class Plug:
    """A live plug on a node instance. Inputs and parameters hold a raw value, outputs hold the cooked value."""

    __slots__ = ("spec", "node", "dynamic", "data_type", "connections", "value", "version", "seen", "history",
                 "_raw", "_expression", "_kind")

    def __init__(self, spec: PlugSpec, node: Node, dynamic: bool = False) -> None:
        self.spec = spec
        self.node = node
        self.dynamic = dynamic
        self.data_type: DataType | None = None
        self.connections: list[Connection] = []
        self.value: Any = None
        self.version = 0
        self.seen = -1
        self.history: deque[tuple[int, Any]] | None = None
        self._raw: Any = spec.default
        self._expression = False
        self._kind = spec.kind

    @property
    def name(self) -> str:
        return self.spec.name

    @property
    def kind(self) -> PlugKind:
        """The plug's kind on this node: the declared one, unless Node.set_plug_kind() swapped input and parameter."""
        return self._kind

    @property
    def promoted(self) -> bool:
        return self._kind is not self.spec.kind

    def kind_error(self, kind: PlugKind) -> str | None:
        """Why this plug cannot become kind, or None when it can."""
        if kind is self._kind:
            return None

        if self._kind is PlugKind.output:
            return f"{self.path} is an output, it cannot become an {kind.value}"

        if kind is PlugKind.output:
            return f"{self.path} cannot become an output"

        if kind is PlugKind.parameter:
            if self.spec.multi:
                return f"{self.path} accepts several connections and cannot become a parameter"

            if self.data_type is None or not self.data_type.editable:
                return f"{self.spec.type_name} values cannot be edited, so {self.path} cannot become a parameter"

        return None

    @property
    def path(self) -> str:
        return f"{self.node.path}.{self.spec.name}"

    @property
    def raw(self) -> Any:
        return self._raw

    @property
    def is_expression(self) -> bool:
        return self._expression

    @property
    def is_connected(self) -> bool:
        return bool(self.connections)

    @property
    def tracked(self) -> bool:
        return self.history is not None

    def track(self) -> None:
        if self.history is None:
            self.history = deque(maxlen=history_limit)

    def publish(self, value: Any, delta: Any = unset) -> Any:
        """Write an output value. Returns the delta recorded for change tracking, None when it counts as replaced."""
        previous = self.value

        if value is previous and delta is unset:
            return None

        self.version += 1

        if self.history is not None:
            if delta is unset:
                delta = None if previous is None or value is None else self.data_type.diff(previous, value)

            self.history.append((self.version, delta))
        elif delta is unset:
            delta = None

        self.value = value

        return delta

    def set(self, value: Any) -> None:
        if self._kind is PlugKind.output:
            raise InvalidValueError(f"cannot set output {self.path}, outputs are written by the node's cook")

        self._store(value)
        self.version += 1
        self.node._value_changed(self)

    def reset(self) -> None:
        self.set(self._default())

    def bind(self, data_type: DataType) -> None:
        self.data_type = data_type
        raw = self._raw if self._raw is not None else data_type.default()

        if self.spec.kind is PlugKind.output:
            self.value = data_type.coerce(raw)
        else:
            self._store(raw)

    def _default(self) -> Any:
        if self.spec.default is not None:
            return self.spec.default

        return self.data_type.default() if self.data_type is not None else None

    def _store(self, raw: Any) -> None:
        data_type = self.data_type

        if data_type is None:
            self._raw = raw
            self._expression = False
        elif data_type.needs_expansion(raw):
            self._raw = raw
            self._expression = True
        else:
            self._raw = data_type.coerce(raw)
            self._expression = False

    def __repr__(self) -> str:
        return f"<Plug {self.path} ({self._kind.value}, {self.spec.type_name})>"
