from __future__ import annotations

import gc

from PySide6.QtCore import QObject, QTimer


class GarbageCollector(QObject):
    """Runs Python's cyclic garbage collector on the GUI thread only.

    The collector normally runs on whichever thread happens to allocate, such as a cooking or rendering thread. When it
    frees Qt objects there, PySide defers their deletion to the GUI thread, where it runs at an arbitrary point,
    possibly while Qt is still using them, and crashes. This disables automatic collection and collects from a timer
    on the GUI thread instead, with the same generation thresholds."""

    def __init__(self, parent: QObject | None = None, interval_ms: int = 500) -> None:
        super().__init__(parent)
        self._threshold = gc.get_threshold()
        self._was_enabled = gc.isenabled()
        self._timer = QTimer(self)
        self._timer.setInterval(interval_ms)
        self._timer.timeout.connect(self.check)

    @property
    def active(self) -> bool:
        return self._timer.isActive()

    def start(self) -> None:
        if self.active:
            return

        self._was_enabled = gc.isenabled()

        gc.disable()

        self._timer.start()

    def stop(self) -> None:
        if not self.active:
            return

        self._timer.stop()

        if self._was_enabled:
            gc.enable()

    def check(self) -> None:
        counts = gc.get_count()

        if counts[0] <= self._threshold[0]:
            return

        generation = 0

        if counts[1] > self._threshold[1]:
            generation = 1

            if counts[2] > self._threshold[2]:
                generation = 2

        gc.collect(generation)
