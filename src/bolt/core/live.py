from __future__ import annotations

import enum
import logging
import threading
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from bolt.core import events
from bolt.core.evaluation import Control, EvaluationResult
from bolt.core.events import GraphEvent

if TYPE_CHECKING:
    from bolt.core.executors import Executor
    from bolt.core.graph import Graph

logger = logging.getLogger("bolt.live")

edit_events = (events.NodeAdded, events.NodeRemoved, events.NodeChanged, events.PlugAdded, events.PlugRemoved,
               events.PlugKindChanged, events.ValueChanged, events.Connected, events.Disconnected,
               events.VariableChanged)


cooking_attributes = frozenset(("disabled", "displayed"))


class LiveMode(enum.Enum):
    auto = "auto"
    manual = "manual"


class EditPolicy(enum.Enum):
    restart = "restart"
    finish = "finish"


@dataclass(frozen=True, slots=True, eq=False)
class LiveStateChanged(GraphEvent):
    mode: LiveMode
    policy: EditPolicy
    busy: bool


class LiveCooker:
    """Cooks the displayed nodes of a graph on a background thread.

    In auto mode every edit schedules a cook, in manual mode only cook() does. When an edit arrives during a cook, the
    restart policy cancels it and cooks again while the finish policy lets it end first. Structural edits cannot happen
    during a cook, so make them through edit(): they run immediately when idle and are queued otherwise."""

    def __init__(self,
                 graph: Graph,
                 *,
                 mode: LiveMode = LiveMode.auto,
                 policy: EditPolicy = EditPolicy.restart,
                 debounce: float = 0.05,
                 executor: Executor | None = None,
                 variables: Mapping[str, Any] | None = None,
                 strict: bool = False,
                 call_soon: Callable[[Callable[[], None]], None] | None = None) -> None:
        self.graph = graph
        self.debounce = debounce
        self.executor = executor
        self.strict = strict
        self.last_result: EvaluationResult | None = None
        self._mode = mode
        self._policy = policy
        self._variables: dict[str, Any] = dict(variables) if variables else {}
        self._call_soon = call_soon
        self._condition = threading.Condition(threading.RLock())
        self._pending = mode is LiveMode.auto
        self._running = False
        self._closing = False
        self._control: Control | None = None
        self._queued_edits: list[Callable[[], Any]] = []
        self._override_targets: list[Any] | None = None
        self._edits_in_flight = 0
        self._subscriptions = [graph.events.subscribe(event_type, self._on_edit) for event_type in edit_events]
        self._thread = threading.Thread(target=self._run, name="bolt-live", daemon=True)
        self._thread.start()

    @property
    def mode(self) -> LiveMode:
        return self._mode

    @mode.setter
    def mode(self, mode: LiveMode) -> None:
        with self._condition:
            self._mode = mode

            if mode is LiveMode.auto:
                self._request()

        self._emit_state()

    @property
    def policy(self) -> EditPolicy:
        return self._policy

    @policy.setter
    def policy(self, policy: EditPolicy) -> None:
        self._policy = policy
        self._emit_state()

    @property
    def busy(self) -> bool:
        return self._running

    @property
    def variables(self) -> Mapping[str, Any]:
        return dict(self._variables)

    def set_variables(self, variables: Mapping[str, Any]) -> None:
        with self._condition:
            self._variables = dict(variables)
            self._on_change()

    def cook(self, targets: list[Any] | None = None) -> None:
        """Cook now: the displayed nodes, or the given targets once."""
        with self._condition:
            self._override_targets = targets

            if self._running:
                if self._policy is EditPolicy.restart and self._control is not None:
                    self._control.cancel()

            self._request()

    def stop(self) -> None:
        with self._condition:
            self._pending = False

            if self._control is not None:
                self._control.cancel()

    def edit(self, function: Callable[[], Any]) -> bool:
        """Run a graph edit now when idle, or queue it until the current cook ends. Returns True when it ran now."""
        with self._condition:
            if not self._running and not self._edits_in_flight:
                function()
                return True

            self._queued_edits.append(function)

            if self._running and self._policy is EditPolicy.restart and self._control is not None:
                self._control.cancel()

            if self._mode is LiveMode.auto or self._policy is EditPolicy.restart:
                self._pending = True

            return False

    def wait(self, timeout: float | None = None) -> bool:
        """Block until no cook is running or scheduled. Returns False on timeout."""
        with self._condition:
            return self._condition.wait_for(
                lambda: not (self._pending or self._running or self._edits_in_flight or self._queued_edits),
                timeout)

    def close(self) -> None:
        for subscription in self._subscriptions:
            subscription.close()

        with self._condition:
            self._closing = True

            if self._control is not None:
                self._control.cancel()

            self._condition.notify_all()

        self._thread.join(timeout=5)

    def _on_edit(self, event: GraphEvent) -> None:
        if isinstance(event, events.NodeChanged) and event.attribute not in cooking_attributes:
            return

        with self._condition:
            self._on_change()

    def _on_change(self) -> None:
        if self._running:
            if self._policy is EditPolicy.restart:
                if self._control is not None:
                    self._control.cancel()

                self._request()

            elif self._mode is LiveMode.auto:
                self._request()

        elif self._mode is LiveMode.auto:
            self._request()

    def _request(self) -> None:
        self._pending = True
        self._condition.notify_all()

    def _targets(self) -> list[Any] | None:
        if self._override_targets is not None:
            targets, self._override_targets = self._override_targets, None
            return targets

        displayed = self.graph.displayed_nodes()

        if displayed:
            return displayed

        return None if self._mode is LiveMode.manual else []

    def _run(self) -> None:
        while True:
            with self._condition:
                self._condition.wait_for(lambda: self._closing or (self._pending and not self._edits_in_flight))

                if self._closing:
                    return

            with self._condition:
                if self._condition.wait_for(lambda: self._closing, self.debounce):
                    return

                if self._edits_in_flight or not self._pending:
                    continue

                self._pending = False
                targets = self._targets()

                if targets == []:
                    self._condition.notify_all()
                    continue

                self._running = True
                self._control = Control()
                control = self._control
                variables = dict(self._variables)

            self._emit_state()

            try:
                self.last_result = self.graph.evaluate(targets, variables=variables, executor=self.executor,
                                                       control=control, strict=self.strict)
            except Exception:
                logger.exception("live cook failed")

            with self._condition:
                self._running = False
                self._control = None
                edits = self._queued_edits
                self._queued_edits = []
                if edits:
                    self._edits_in_flight += 1

                self._condition.notify_all()

            self._emit_state()

            if edits:
                if self._call_soon is None:
                    self._apply_edits(edits)
                else:
                    self._call_soon(lambda edits=edits: self._apply_edits(edits))

    def _apply_edits(self, edits: list[Callable[[], Any]]) -> None:
        with self._condition:
            try:
                while edits:
                    for function in edits:
                        try:
                            function()
                        except Exception:
                            logger.exception("queued graph edit failed")

                    edits = self._queued_edits
                    self._queued_edits = []
            finally:
                self._edits_in_flight -= 1
                self._condition.notify_all()

    def _emit_state(self) -> None:
        self.graph.events.emit(LiveStateChanged, self.graph, self._mode, self._policy, self._running)
