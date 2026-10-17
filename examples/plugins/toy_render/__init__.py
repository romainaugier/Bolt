"""Toy progressive renderer: the reference for plugging an engine into Bolt.

- scene.py   data types (color, shape, scene) whose values are immutable and shared between versions
- nodes.py   nodes building the scene, and the render node: the "last node" that feeds the engine with deltas
- engine.py  the engine, a background thread unaware of Bolt beyond the delta it receives
- view.py    the editor view showing the engine's pixels, and a color parameter widget

register() is all the core needs; register_ui() is only called by the editor, so Qt is never imported headless.
"""

from . import nodes, scene


def register(registry):
    registry.register_module(scene)
    registry.register_module(nodes)


def register_ui(ui):
    from .view import ColorEditor, RenderView

    ui.register_view(RenderView)
    ui.register_parameter_widget("color", ColorEditor)
