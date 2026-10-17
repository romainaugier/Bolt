from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, ClassVar, TypeVar

from PySide6.QtWidgets import QWidget

from bolt.core.events import Event, Subscription

if TYPE_CHECKING:
    from bolt.ui.workspace import Workspace

EventT = TypeVar("EventT", bound=Event)


class View(QWidget):
    """A panel that can live in any pane. Subclass it, set view_type and label, and register it."""

    view_type: ClassVar[str] = ""
    label: ClassVar[str] = ""
    description: ClassVar[str] = ""

    def __init__(self, workspace: Workspace, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.workspace = workspace
        self._subscriptions: list[Subscription] = []

    def subscribe(self, event_type: type[EventT], callback: Callable[[EventT], None]) -> None:
        """Subscribe to the workspace events for the lifetime of the view."""
        self._subscriptions.append(self.workspace.events.subscribe(event_type, callback))

    def save_state(self) -> dict[str, Any]:
        return {}

    def restore_state(self, state: dict[str, Any]) -> None:
        pass

    def close_view(self) -> None:
        for subscription in self._subscriptions:
            subscription.close()

        self._subscriptions = []


class ViewRegistry:
    def __init__(self) -> None:
        self._views: dict[str, type[View]] = {}

    def register(self, view_class: type[View]) -> type[View]:
        if not view_class.view_type:
            raise ValueError(f"{view_class.__name__} has no view_type")

        self._views[view_class.view_type] = view_class

        return view_class

    def get(self, view_type: str) -> type[View] | None:
        return self._views.get(view_type)

    def views(self) -> list[type[View]]:
        return sorted(self._views.values(), key=lambda view_class: view_class.label or view_class.view_type)
