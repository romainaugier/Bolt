from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QMenu, QSplitter, QStackedWidget, QTabBar, QToolButton,
                               QVBoxLayout, QWidget)

from bolt.ui.icons import bind_icon
from bolt.ui.views.base import View, ViewRegistry

if TYPE_CHECKING:
    from bolt.ui.workspace import Workspace

logger = logging.getLogger("bolt.ui")

orientations = {"horizontal": Qt.Horizontal, "vertical": Qt.Vertical}


def _tool_button(icon_name: str, tooltip: str) -> QToolButton:
    button = QToolButton()
    bind_icon(button, icon_name)
    button.setIconSize(QSize(14, 14))
    button.setToolTip(tooltip)
    button.setAutoRaise(True)

    return button


def closing_button(tooltip: str) -> QToolButton:
    button = QToolButton()
    bind_icon(button, "close", "muted")
    button.setIconSize(QSize(10, 10))
    button.setToolTip(tooltip)
    button.setAutoRaise(True)

    return button


class Pane(QFrame):
    """A tab group of views with buttons to add views, split the pane and close it."""

    def __init__(self, workbench: Workbench) -> None:
        super().__init__()

        self.setObjectName("pane")
        self.workbench = workbench
        self.tabs = QTabBar()
        self.tabs.setMovable(True)
        self.tabs.setDrawBase(False)
        self.tabs.setExpanding(False)
        self.tabs.currentChanged.connect(self._show)
        self.tabs.tabMoved.connect(self._moved)
        self.stack = QStackedWidget()

        add_button = _tool_button("add", "Add a view")
        add_button.setPopupMode(QToolButton.InstantPopup)
        add_button.setMenu(self._views_menu())
        split_button = _tool_button("vertical_split", "Split this pane")
        split_button.setPopupMode(QToolButton.InstantPopup)
        split_menu = QMenu(split_button)

        bind_icon(split_menu.addAction("Split left/right", lambda: self.split(Qt.Horizontal)), "vertical_split")
        bind_icon(split_menu.addAction("Split top/bottom", lambda: self.split(Qt.Vertical)), "horizontal_split")

        split_button.setMenu(split_menu)
        close_button = _tool_button("close", "Close this pane")
        close_button.clicked.connect(lambda: self.workbench.close_pane(self))

        header = QWidget()
        header.setObjectName("pane_header")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(4, 0, 4, 0)
        header_layout.setSpacing(2)
        header_layout.addWidget(self.tabs)
        header_layout.addStretch(1)

        for button in (add_button, split_button, close_button):
            header_layout.addWidget(button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(0)
        layout.addWidget(header)
        layout.addWidget(self.stack, 1)

    def views(self) -> list[View]:
        return [self.stack.widget(index) for index in range(self.stack.count())]

    def current_view(self) -> View | None:
        return self.stack.currentWidget()

    def add_view(self, view_type: str, state: dict[str, Any] | None = None) -> View | None:
        view_class = self.workbench.views.get(view_type)

        if view_class is None:
            logger.warning("unknown view type '%s'", view_type)
            return None

        view = view_class(self.workbench.workspace)

        if state:
            try:
                view.restore_state(state)
            except Exception:
                logger.exception("cannot restore the state of view '%s'", view_type)

        index = self.tabs.addTab(view_class.label or view_type)

        self.stack.insertWidget(index, view)

        close = closing_button(f"Close {view_class.label or view_type}")
        close.clicked.connect(lambda checked=False, view=view: self.close_view(self.stack.indexOf(view)))

        self.tabs.setTabButton(index, QTabBar.RightSide, close)
        self.tabs.setCurrentIndex(index)

        return view

    def close_view(self, index: int) -> None:
        view = self.stack.widget(index)

        if view is None:
            return

        view.close_view()

        self.stack.removeWidget(view)
        self.tabs.removeTab(index)

        view.deleteLater()

        if self.stack.count() == 0 and self.workbench.pane_count() > 1:
            self.workbench.close_pane(self)

    def split(self, orientation: Qt.Orientation) -> Pane:
        return self.workbench.split(self, orientation)

    def to_dict(self) -> dict[str, Any]:
        return {"type": "pane",
                "views": [{"view": view.view_type, "state": view.save_state()} for view in self.views()],
                "current": self.tabs.currentIndex()}

    def dispose(self) -> None:
        for view in self.views():
            view.close_view()

    def _views_menu(self) -> QMenu:
        menu = QMenu(self)

        for view_class in self.workbench.views.views():
            action = menu.addAction(view_class.label or view_class.view_type)
            action.setToolTip(view_class.description)
            action.triggered.connect(lambda checked=False, view_type=view_class.view_type: self.add_view(view_type))

        return menu

    def _show(self, index: int) -> None:
        if 0 <= index < self.stack.count():
            self.stack.setCurrentIndex(index)

    def _moved(self, source: int, target: int) -> None:
        widget = self.stack.widget(source)

        self.stack.removeWidget(widget)
        self.stack.insertWidget(target, widget)
        self.stack.setCurrentIndex(self.tabs.currentIndex())


class Workbench(QWidget):
    """The recursive split layout: every leaf is a Pane, every branch a QSplitter. Saved and restored as a dict."""

    def __init__(self, workspace: Workspace, views: ViewRegistry, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.workspace = workspace
        self.views = views
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(4, 4, 4, 4)
        self.root: QWidget = Pane(self)
        self._layout.addWidget(self.root)

    def panes(self) -> list[Pane]:
        return self._panes(self.root)

    def pane_count(self) -> int:
        return len(self.panes())

    def all_views(self) -> list[View]:
        return [view for pane in self.panes() for view in pane.views()]

    def split(self, pane: Pane, orientation: Qt.Orientation) -> Pane:
        new_pane = Pane(self)
        current = pane.current_view()

        if current is not None:
            new_pane.add_view(current.view_type)

        parent = pane.parentWidget()

        if isinstance(parent, QSplitter) and parent.orientation() == orientation:
            index = parent.indexOf(pane)
            sizes = parent.sizes()
            half = sizes[index] // 2
            parent.insertWidget(index + 1, new_pane)
            parent.setSizes(sizes[:index] + [sizes[index] - half, half] + sizes[index + 1:])

            return new_pane

        splitter = QSplitter(orientation)
        splitter.setChildrenCollapsible(False)

        self._replace(pane, splitter)

        splitter.addWidget(pane)
        splitter.addWidget(new_pane)

        pane.show()

        extent = pane.width() if orientation == Qt.Horizontal else pane.height()

        splitter.setSizes([max(extent // 2, 1), max(extent // 2, 1)])

        return new_pane

    def close_pane(self, pane: Pane) -> None:
        parent = pane.parentWidget()

        if not isinstance(parent, QSplitter):
            for index in reversed(range(len(pane.views()))):
                pane.close_view(index)

            return

        pane.dispose()
        pane.setParent(None)
        pane.deleteLater()

        if parent.count() == 1:
            survivor = parent.widget(0)
            survivor.setParent(self)

            self._replace(parent, survivor)

            parent.deleteLater()

    def to_dict(self) -> dict[str, Any]:
        return self._serialize(self.root)

    def restore(self, data: dict[str, Any]) -> None:
        old_root = self.root

        for pane in self.panes():
            pane.dispose()

        self._layout.removeWidget(old_root)

        old_root.setParent(None)
        old_root.deleteLater()

        self.root = self._build(data)
        self._layout.addWidget(self.root)

        if not self.panes():
            self.restore({"type": "pane", "views": []})

    def _replace(self, old: QWidget, new: QWidget) -> None:
        parent = old.parentWidget()

        if isinstance(parent, QSplitter):
            index = parent.indexOf(old)
            sizes = parent.sizes()
            parent.insertWidget(index, new)
            old.hide()
            old.setParent(self)
            parent.setSizes(sizes)
        else:
            self._layout.removeWidget(old)

            old.hide()

            self._layout.addWidget(new)
            self.root = new

        new.show()

    def _panes(self, widget: QWidget) -> list[Pane]:
        if isinstance(widget, Pane):
            return [widget]

        if isinstance(widget, QSplitter):
            return [pane for index in range(widget.count()) for pane in self._panes(widget.widget(index))]

        return []

    def _serialize(self, widget: QWidget) -> dict[str, Any]:
        if isinstance(widget, Pane):
            return widget.to_dict()

        orientation = "horizontal" if widget.orientation() == Qt.Horizontal else "vertical"

        return {"type": "split", "orientation": orientation, "sizes": widget.sizes(),
                "children": [self._serialize(widget.widget(index)) for index in range(widget.count())]}

    def _build(self, data: dict[str, Any]) -> QWidget:
        if data.get("type") == "split" and data.get("children"):
            splitter = QSplitter(orientations.get(data.get("orientation"), Qt.Horizontal))
            splitter.setChildrenCollapsible(False)

            for child in data["children"]:
                splitter.addWidget(self._build(child))

            sizes = data.get("sizes")

            if sizes and len(sizes) == splitter.count():
                splitter.setSizes([int(size) for size in sizes])

            return splitter

        pane = Pane(self)

        for entry in data.get("views", ()):
            pane.add_view(entry.get("view", ""), entry.get("state"))

        current = data.get("current", 0)

        if 0 <= current < pane.tabs.count():
            pane.tabs.setCurrentIndex(current)

        return pane
