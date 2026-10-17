from __future__ import annotations

import enum
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

_empty_mapping: Mapping[Any, Any] = MappingProxyType({})


class ChangeKind(enum.Enum):
    unchanged = "unchanged"
    delta = "delta"
    replaced = "replaced"


@dataclass(frozen=True, slots=True, eq=False)
class Change:
    """How a value changed since the node reading it last cooked successfully."""

    kind: ChangeKind
    value: Any
    delta: Any = None

    @property
    def changed(self) -> bool:
        return self.kind is not ChangeKind.unchanged


@dataclass(frozen=True, slots=True)
class MappingDelta:
    added: Mapping[Any, Any] = field(default_factory=lambda: _empty_mapping)
    removed: frozenset[Any] = frozenset()
    modified: Mapping[Any, Any] = field(default_factory=lambda: _empty_mapping)

    @property
    def empty(self) -> bool:
        return not (self.added or self.removed or self.modified)


@dataclass(frozen=True, slots=True)
class SequenceDelta:
    modified: Mapping[int, Any] = field(default_factory=lambda: _empty_mapping)

    @property
    def empty(self) -> bool:
        return not self.modified


def diff_mapping(old: Mapping[Any, Any], new: Mapping[Any, Any]) -> MappingDelta:
    added = {key: value for key, value in new.items() if key not in old}
    removed = frozenset(key for key in old if key not in new)
    modified = {key: value for key, value in new.items() if key in old and old[key] is not value}
    return MappingDelta(added, removed, modified)


def merge_mapping(first: MappingDelta, second: MappingDelta) -> MappingDelta:
    added = dict(first.added)
    removed = set(first.removed)
    modified = dict(first.modified)

    for key in second.removed:
        if key in added:
            del added[key]
        else:
            modified.pop(key, None)
            removed.add(key)

    for key, value in second.added.items():
        if key in removed:
            removed.discard(key)
            modified[key] = value
        else:
            added[key] = value

    for key, value in second.modified.items():
        if key in added:
            added[key] = value
        else:
            modified[key] = value

    return MappingDelta(added, frozenset(removed), modified)


def apply_mapping(value: Mapping[Any, Any], delta: MappingDelta) -> dict[Any, Any]:
    result = dict(value)

    for key in delta.removed:
        result.pop(key, None)

    result.update(delta.added)
    result.update(delta.modified)

    return result


def diff_sequence(old: Sequence[Any], new: Sequence[Any]) -> SequenceDelta | None:
    if len(old) != len(new):
        return None

    return SequenceDelta({index: item for index, (previous, item) in enumerate(zip(old, new)) if previous is not item})


def merge_sequence(first: SequenceDelta, second: SequenceDelta) -> SequenceDelta:
    return SequenceDelta({**first.modified, **second.modified})


def apply_sequence(value: Sequence[Any], delta: SequenceDelta) -> list[Any]:
    result = list(value)

    for index, item in delta.modified.items():
        result[index] = item

    return result


def copy_with(container: Any, updates: Mapping[Any, Any] | None = None, removed: Any = ()) -> Any:
    """Copy-on-write helper: a new dict or list sharing every untouched item with the original."""
    if isinstance(container, Mapping):
        result = dict(container)
        for key in removed:
            result.pop(key, None)
        if updates:
            result.update(updates)
        return result

    result = list(container)

    if updates:
        for index, item in updates.items():
            result[index] = item

    for index in sorted(removed, reverse=True):
        del result[index]

    return result
