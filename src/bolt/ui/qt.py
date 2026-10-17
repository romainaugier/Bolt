from __future__ import annotations

import logging
import threading
from collections.abc import Callable, Iterable
from typing import Any

from PySide6.QtCore import QObject, QThread, QTimer, Signal
from PySide6.QtWidgets import QWidget

from bolt.core.events import Event, EventBus, Subscription

logger = logging.getLogger("bolt.ui")


class Dispatcher(QObject):
    """Runs callables on the thread that created it (the GUI thread), whatever thread asks."""

    _invoke = Signal(object)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._invoke.connect(self._run)

    def call_soon(self, function: Callable[[], Any]) -> None:
        self._invoke.emit(function)

    def in_gui_thread(self) -> bool:
        return QThread.currentThread() is self.thread()

    @staticmethod
    def _run(function: Callable[[], Any]) -> None:
        try:
            function()
        except Exception:
            logger.exception("dispatched call failed")


class EventRelay(QObject):
    """Forwards events from a bus fed by any thread to another bus, always on the GUI thread.

    Events of the coalesced types are merged per (type, node or job) and delivered at most every interval, so
    progress events from busy workers cannot flood the interface."""

    _relay = Signal(object)
    _schedule = Signal()

    def __init__(self,
                 source: EventBus,
                 target: EventBus,
                 event_types: Iterable[type[Event]] = (Event,),
                 coalesce: Iterable[type[Event]] = (),
                 interval_ms: int = 33,
                 parent: QObject | None = None) -> None:
        super().__init__(parent)

        self.target = target
        self._coalesce = tuple(coalesce)
        self._pending: dict[tuple[type, Any], Event] = {}
        self._pending_lock = threading.Lock()
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(interval_ms)
        self._timer.timeout.connect(self.flush)
        self._relay.connect(self._deliver)
        self._schedule.connect(self._start_timer)
        self._subscriptions: list[Subscription] = [source.subscribe(event_type, self._receive)
                                                   for event_type in event_types]

    def close(self) -> None:
        for subscription in self._subscriptions:
            subscription.close()

        self._subscriptions = []
        self._timer.stop()

    def flush(self) -> None:
        with self._pending_lock:
            pending = list(self._pending.values())
            self._pending.clear()

        for event in pending:
            self.target.dispatch(event)

    def _receive(self, event: Event) -> None:
        if self._coalesce and isinstance(event, self._coalesce):
            key = (type(event), getattr(event, "node", None) or getattr(event, "job", None))

            with self._pending_lock:
                first = not self._pending

                self._pending[key] = event
            if first:
                self._schedule.emit()

            return

        if QThread.currentThread() is self.thread():
            self._deliver(event)
        else:
            self._relay.emit(event)

    def _deliver(self, event: Event) -> None:
        if self._pending:
            self.flush()

        self.target.dispatch(event)

    def _start_timer(self) -> None:
        if not self._timer.isActive():
            self._timer.start()


class RepaintScheduler(QObject):
    """Thread-safe, rate-limited widget.update(): call request() from any thread, e.g. a render thread."""

    _requested = Signal()

    def __init__(self, widget: QWidget, max_fps: int = 60) -> None:
        super().__init__(widget)

        self._widget = widget
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(max(1, 1000 // max_fps))
        self._timer.timeout.connect(widget.update)
        self._requested.connect(self._schedule)

    def request(self) -> None:
        self._requested.emit()

    def _schedule(self) -> None:
        if not self._timer.isActive():
            self._timer.start()
