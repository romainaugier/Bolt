from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from types import MappingProxyType
from typing import Any

from bolt.core import changes
from bolt.core.errors import InvalidValueError

Expand = Callable[[str], Any]

_true_strings = frozenset(("1", "true", "yes", "on"))
_false_strings = frozenset(("0", "false", "no", "off", ""))
_empty_mapping: Mapping[str, Any] = MappingProxyType({})


def has_markers(text: str) -> bool:
    return "$(" in text or "`" in text


class DataType:
    """Describes a kind of value flowing through plugs. Subclass it to add your own types.

    editable means users can type its values in an editor and files can save them: plugs of editable types can be
    switched between input and parameter on a node (Node.set_plug_kind). Custom types are not editable by default."""

    __slots__ = ("name", "python_type", "default_value", "default_factory", "string_like", "expandable", "editable",
                 "ui", "description")

    def __init__(self,
                 name: str,
                 python_type: type | tuple[type, ...] = object,
                 *,
                 default: Any = None,
                 default_factory: Callable[[], Any] | None = None,
                 string_like: bool = False,
                 expandable: bool | None = None,
                 editable: bool = False,
                 ui: Mapping[str, Any] | None = None,
                 description: str = "") -> None:
        self.name = name
        self.python_type = python_type
        self.default_value = default
        self.default_factory = default_factory
        self.string_like = string_like
        self.expandable = string_like if expandable is None else expandable
        self.editable = editable
        self.ui = MappingProxyType(dict(ui)) if ui else _empty_mapping
        self.description = description

    def default(self) -> Any:
        if self.default_factory is not None:
            return self.default_factory()

        return self.default_value

    def coerce(self, value: Any) -> Any:
        if value is None or self.python_type is object or isinstance(value, self.python_type):
            return value

        constructor = self.python_type[0] if isinstance(self.python_type, tuple) else self.python_type

        try:
            return constructor(value)
        except (TypeError, ValueError) as error:
            raise InvalidValueError(f"cannot convert {value!r} to {self.name}") from error

    def needs_expansion(self, raw: Any) -> bool:
        if not isinstance(raw, str):
            return False

        if self.string_like and not self.expandable:
            return False

        return has_markers(raw)

    def resolve(self, raw: Any, expand: Expand) -> Any:
        if isinstance(raw, str):
            raw = expand(raw)

        return self.coerce(raw)

    def serialize(self, value: Any) -> Any:
        return value

    def deserialize(self, data: Any) -> Any:
        return data

    def diff(self, old: Any, new: Any) -> Any:
        """Delta between two values, or None when the new value should be treated as a replacement."""
        return None

    def merge(self, first: Any, second: Any) -> Any:
        """Delta equivalent to applying first then second, or None when they cannot be combined."""
        return None

    def apply(self, value: Any, delta: Any) -> Any:
        """Value obtained by applying a delta, used by strict evaluations to verify deltas."""
        return NotImplemented

    def fingerprint(self, value: Any) -> Any:
        """Cheap identity of a value's content, used by strict evaluations to detect mutated inputs."""
        return None

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self.name!r}>"


class BoolType(DataType):
    __slots__ = ()

    def coerce(self, value: Any) -> Any:
        if value is None or isinstance(value, bool):
            return value

        if isinstance(value, str):
            lowered = value.strip().lower()

            if lowered in _true_strings:
                return True

            if lowered in _false_strings:
                return False

            raise InvalidValueError(f"cannot convert {value!r} to bool")

        return bool(value)


class IntType(DataType):
    __slots__ = ()

    def coerce(self, value: Any) -> Any:
        if value is None:
            return None

        if isinstance(value, bool):
            return int(value)

        if isinstance(value, int):
            return value

        try:
            if isinstance(value, str):
                text = value.strip()

                try:
                    return int(text)
                except ValueError:
                    value = float(text)

            if isinstance(value, float):
                if value.is_integer():
                    return int(value)

                raise InvalidValueError(f"cannot convert {value!r} to int without losing precision")

            return int(value)

        except (TypeError, ValueError) as error:
            if isinstance(error, InvalidValueError):
                raise

            raise InvalidValueError(f"cannot convert {value!r} to int") from error


class PathType(DataType):
    __slots__ = ()

    def coerce(self, value: Any) -> Any:
        if value is None or isinstance(value, str):
            return value

        if isinstance(value, os.PathLike):
            return os.fspath(value)

        raise InvalidValueError(f"cannot convert {value!r} to {self.name}")


class ListType(DataType):
    __slots__ = ()

    def coerce(self, value: Any) -> Any:
        if value is None or isinstance(value, list):
            return value

        if isinstance(value, (str, bytes, Mapping)):
            raise InvalidValueError(f"cannot convert {value!r} to list")

        try:
            return list(value)
        except TypeError as error:
            raise InvalidValueError(f"cannot convert {value!r} to list") from error

    def needs_expansion(self, raw: Any) -> bool:
        if isinstance(raw, str):
            return has_markers(raw)

        if isinstance(raw, list):
            return any(isinstance(item, str) and has_markers(item) for item in raw)

        return False

    def resolve(self, raw: Any, expand: Expand) -> Any:
        if isinstance(raw, str):
            return self.coerce(expand(raw))

        return [expand(item) if isinstance(item, str) and has_markers(item) else item for item in raw]

    def diff(self, old: Any, new: Any) -> Any:
        return changes.diff_sequence(old, new)

    def merge(self, first: Any, second: Any) -> Any:
        return changes.merge_sequence(first, second)

    def apply(self, value: Any, delta: Any) -> Any:
        return changes.apply_sequence(value, delta)

    def fingerprint(self, value: Any) -> Any:
        return None if value is None else tuple(map(id, value))


class DictType(DataType):
    __slots__ = ()

    def coerce(self, value: Any) -> Any:
        if value is None or isinstance(value, dict):
            return value

        if isinstance(value, Mapping):
            return dict(value)

        raise InvalidValueError(f"cannot convert {value!r} to dict")

    def needs_expansion(self, raw: Any) -> bool:
        if isinstance(raw, str):
            return has_markers(raw)

        if isinstance(raw, dict):
            return any(isinstance(item, str) and has_markers(item) for item in raw.values())

        return False

    def resolve(self, raw: Any, expand: Expand) -> Any:
        if isinstance(raw, str):
            return self.coerce(expand(raw))

        return {key: expand(item) if isinstance(item, str) and has_markers(item) else item for key, item in raw.items()}

    def diff(self, old: Any, new: Any) -> Any:
        return changes.diff_mapping(old, new)

    def merge(self, first: Any, second: Any) -> Any:
        return changes.merge_mapping(first, second)

    def apply(self, value: Any, delta: Any) -> Any:
        return changes.apply_mapping(value, delta)

    def fingerprint(self, value: Any) -> Any:
        return None if value is None else tuple((key, id(item)) for key, item in value.items())


any_type = DataType("any", editable=True, description="Any value")
bool_type = BoolType("bool", bool, default=False, editable=True)
int_type = IntType("int", int, default=0, editable=True)
float_type = DataType("float", float, default=0.0, editable=True)
string_type = DataType("string", str, default="", string_like=True, editable=True)
path_type = PathType("path", str, default="", string_like=True, editable=True, ui={"widget": "path"})
code_type = DataType("code", str, default="", string_like=True, expandable=False, editable=True, ui={"widget": "code"})
list_type = ListType("list", list, default_factory=list, editable=True)
dict_type = DictType("dict", dict, default_factory=dict, editable=True)

builtin_types = (any_type, bool_type, int_type, float_type, string_type, path_type, code_type, list_type, dict_type)

builtin_conversions = (
    ("bool", "int", int),
    ("bool", "float", float),
    ("int", "float", float),
    ("bool", "string", str),
    ("int", "string", str),
    ("float", "string", str),
    ("path", "string", None),
    ("string", "path", None),
)
