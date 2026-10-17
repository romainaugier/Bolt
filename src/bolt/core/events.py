from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from bolt.core.evaluation import EvaluationResult
    from bolt.core.graph import Connection, Graph
    from bolt.core.node import Node
    from bolt.core.plugs import Plug

logger = logging.getLogger("bolt.events")

EventT = TypeVar("EventT", bound="Event")
Listener = Callable[[Any], None]


@dataclass(frozen=True, slots=True, eq=False)
class Event:
    """Base class of every event. Subclass it (as a frozen dataclass) to define your own events."""


@dataclass(frozen=True, slots=True, eq=False)
class GraphEvent(Event):
    graph: Graph


@dataclass(frozen=True, slots=True, eq=False)
class NodeAdded(GraphEvent):
    node: Node


@dataclass(frozen=True, slots=True, eq=False)
class NodeRemoved(GraphEvent):
    node: Node


@dataclass(frozen=True, slots=True, eq=False)
class NodeRenamed(GraphEvent):
    node: Node
    old_name: str


@dataclass(frozen=True, slots=True, eq=False)
class NodeChanged(GraphEvent):
    node: Node
    attribute: str


@dataclass(frozen=True, slots=True, eq=False)
class PlugAdded(GraphEvent):
    plug: Plug


@dataclass(frozen=True, slots=True, eq=False)
class PlugRemoved(GraphEvent):
    node: Node
    name: str


@dataclass(frozen=True, slots=True, eq=False)
class PlugKindChanged(GraphEvent):
    plug: Plug


@dataclass(frozen=True, slots=True, eq=False)
class ValueChanged(GraphEvent):
    plug: Plug


@dataclass(frozen=True, slots=True, eq=False)
class Connected(GraphEvent):
    connection: Connection


@dataclass(frozen=True, slots=True, eq=False)
class Disconnected(GraphEvent):
    connection: Connection


@dataclass(frozen=True, slots=True, eq=False)
class VariableChanged(GraphEvent):
    name: str


@dataclass(frozen=True, slots=True, eq=False)
class EvaluationStarted(GraphEvent):
    node_count: int


@dataclass(frozen=True, slots=True, eq=False)
class EvaluationProgress(GraphEvent):
    done: int
    total: int


@dataclass(frozen=True, slots=True, eq=False)
class EvaluationFinished(GraphEvent):
    result: EvaluationResult


@dataclass(frozen=True, slots=True, eq=False)
class NodeCookStarted(GraphEvent):
    node: Node


@dataclass(frozen=True, slots=True, eq=False)
class NodeCooked(GraphEvent):
    node: Node
    duration: float


@dataclass(frozen=True, slots=True, eq=False)
class NodeCookFailed(GraphEvent):
    node: Node
    error: str


@dataclass(frozen=True, slots=True, eq=False)
class NodeBlocked(GraphEvent):
    node: Node


@dataclass(frozen=True, slots=True, eq=False)
class NodeLog(GraphEvent):
    node: Node
    level: int
    message: str


@dataclass(frozen=True, slots=True, eq=False)
class NodeProgress(GraphEvent):
    node: Node
    fraction: float


class Subscription:
    __slots__ = ("_bus", "event_type", "callback")

    def __init__(self, bus: EventBus, event_type: type[Event], callback: Listener) -> None:
        self._bus = bus
        self.event_type = event_type
        self.callback = callback

    def close(self) -> None:
        self._bus.unsubscribe(self.event_type, self.callback)

    def __enter__(self) -> Subscription:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


class EventBus:
    """Synchronous publish/subscribe hub. Listeners of a class also receive events of its subclasses."""

    __slots__ = ("_listeners", "_resolved", "_lock")

    def __init__(self) -> None:
        self._listeners: dict[type[Event], list[Listener]] = {}
        self._resolved: dict[type[Event], tuple[Listener, ...]] = {}
        self._lock = threading.Lock()

    def subscribe(self, event_type: type[EventT], callback: Callable[[EventT], None]) -> Subscription:
        with self._lock:
            self._listeners.setdefault(event_type, []).append(callback)
            self._resolved.clear()

        return Subscription(self, event_type, callback)

    def unsubscribe(self, event_type: type[Event], callback: Listener) -> None:
        with self._lock:
            listeners = self._listeners.get(event_type)

            if listeners is None or callback not in listeners:
                return

            listeners.remove(callback)

            if not listeners:
                del self._listeners[event_type]

            self._resolved.clear()

    def listeners(self, event_type: type[Event]) -> tuple[Listener, ...]:
        resolved = self._resolved.get(event_type)

        if resolved is None:
            with self._lock:
                resolved = tuple(callback
                                 for klass in event_type.__mro__
                                 for callback in self._listeners.get(klass, ()))
                self._resolved[event_type] = resolved

        return resolved

    def has_listeners(self, event_type: type[Event]) -> bool:
        return bool(self._listeners) and bool(self.listeners(event_type))

    def emit(self, event_type: type[Event], *args: Any, **kwargs: Any) -> None:
        if not self._listeners:
            return

        listeners = self.listeners(event_type)

        if listeners:
            self._dispatch(event_type(*args, **kwargs), listeners)

    def dispatch(self, event: Event) -> None:
        if self._listeners:
            self._dispatch(event, self.listeners(type(event)))

    @staticmethod
    def _dispatch(event: Event, listeners: tuple[Listener, ...]) -> None:
        for callback in listeners:
            try:
                callback(event)
            except Exception:
                logger.exception("event listener %r failed on %s", callback, type(event).__name__)
