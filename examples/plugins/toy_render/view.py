from __future__ import annotations

import threading
from typing import Any

from PySide6.QtCore import QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QColorDialog, QLabel, QPushButton, QVBoxLayout, QWidget

import bolt
from bolt.ui import CurrentDocumentChanged, ImageCanvas, ParameterEditor, SelectionChanged, View

from .engine import RenderSession
from .nodes import RenderNode


class RenderView(View):
    """Shows the renderer of the selected toy.render node, or of the displayed one.

    The render thread calls the listener for every finished bucket; the canvas coalesces those into at most one
    repaint per frame, so the view stays live without ever blocking the renderer. The lock guarantees that once the
    view detached, the render thread no longer touches its Qt objects, which may then be destroyed."""

    view_type = "toy.render_view"
    label = "Render"
    description = "Live output of the toy renderer."

    def __init__(self, workspace: Any, parent: QWidget | None = None) -> None:
        super().__init__(workspace, parent)
        self.canvas = ImageCanvas()
        self.info = QLabel()
        self.info.setObjectName("muted")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas, 1)
        layout.addWidget(self.info)
        self.node: RenderNode | None = None
        self.session: RenderSession | None = None
        self._session_lock = threading.Lock()
        self.timer = QTimer(self)
        self.timer.setInterval(150)
        self.timer.timeout.connect(self._update_info)
        self.timer.start()
        self.subscribe(SelectionChanged, lambda event: self._follow())
        self.subscribe(CurrentDocumentChanged, lambda event: self._follow())
        self.subscribe(bolt.events.NodeAdded, lambda event: self._follow())
        self.subscribe(bolt.events.NodeRemoved, lambda event: self._follow())
        self.subscribe(bolt.events.NodeChanged, lambda event: self._follow())
        self.subscribe(bolt.events.NodeCooked, lambda event: self._follow())
        self._follow()

    def close_view(self) -> None:
        self._attach(None)
        self.timer.stop()
        super().close_view()

    def _follow(self) -> None:
        document = self.workspace.current
        node = None
        if document is not None:
            selected = [n for n in document.selection if isinstance(n, RenderNode)]
            displayed = [n for n in document.graph.displayed_nodes() if isinstance(n, RenderNode)]
            candidates = selected or displayed or [n for n in document.graph if isinstance(n, RenderNode)]
            node = candidates[0] if candidates else None
        if node is not self.node or (node is not None and node.session is not self.session):
            self._attach(node)

    def _attach(self, node: RenderNode | None) -> None:
        with self._session_lock:
            if self.session is not None:
                self.session.remove_listener(self._on_render)
            self.node = node
            self.session = node.session if node is not None else None
        if self.session is None:
            self.canvas.set_image(None)
            return
        self.session.add_listener(self._on_render)
        self._show_buffer()

    def _show_buffer(self) -> None:
        session = self.session
        if session is not None:
            self.canvas.set_buffer(session.buffer, session.width, session.height)

    def _on_render(self, kind: str) -> None:
        with self._session_lock:
            if self.session is None:
                return
            if kind == "resized":
                self.workspace.dispatcher.call_soon(self._show_buffer)
            else:
                self.canvas.request_update()

    def _update_info(self) -> None:
        session = self.session
        if session is None:
            self.info.setText("  No toy.render node in this graph")
            return
        stats = session.stats
        state = "rendering" if stats.rendering else f"done in {stats.frame_time * 1000:.0f} ms"
        region = stats.region
        area = f"{region[2] - region[0]}×{region[3] - region[1]} px" if region else "-"
        self.info.setText(f"  {self.node.name}: {session.width}×{session.height}  ·  {state}  ·  last update: "
                          f"{stats.last_update or '-'} ({area})  ·  {stats.updates} update(s)")


class ColorEditor(ParameterEditor):
    """A parameter widget for the color type, registered by this plugin's register_ui()."""

    def __init__(self, plug: bolt.Plug, parent: QWidget | None = None) -> None:
        super().__init__(plug, parent)
        self.button = QPushButton()
        self.button.clicked.connect(self._pick)
        self._layout.addWidget(self.button)
        self._layout.addStretch(1)
        self._value = (0.0, 0.0, 0.0)

    def set_value(self, value: Any) -> None:
        if isinstance(value, (tuple, list)) and len(value) == 3:
            self._value = tuple(value)
        color = QColor.fromRgbF(*self._value)
        self.button.setText(color.name())
        self.button.setStyleSheet(f"background: {color.name()}; color: {'#000' if color.lightnessF() > 0.5 else '#fff'};")

    def _pick(self) -> None:
        color = QColorDialog.getColor(QColor.fromRgbF(*self._value), self, self.plug.spec.label)
        if color.isValid():
            self._emit(color.name())
