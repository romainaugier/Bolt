from __future__ import annotations

import dataclasses

import bolt

from .engine import RenderSession
from .scene import Sphere


class SphereNode(bolt.Node):
    type_name = "toy.sphere"
    ui = {"icon": "circle"}
    category = "Toy render"
    description = "A sphere named after the node."
    parameters = (bolt.Parameter("x", "float", 0.0, ui={"step": 0.05}),
                  bolt.Parameter("y", "float", 0.0, ui={"step": 0.05}),
                  bolt.Parameter("z", "float", 0.0, ui={"step": 0.05}),
                  bolt.Parameter("radius", "float", 0.3, ui={"step": 0.05, "min": 0.01}),
                  bolt.Parameter("color", "color", "#d9a441"))
    outputs = (bolt.Output("shape", "shape"),)

    def cook(self, ctx: bolt.CookContext) -> None:
        ctx.set("shape", Sphere(self.name, ctx.get("x"), ctx.get("y"), ctx.get("z"), ctx.get("radius"),
                                ctx.get("color")))


class GroupNode(bolt.Node):
    type_name = "toy.group"
    ui = {"icon": "layers"}
    category = "Toy render"
    description = "Gathers shapes into a scene. Unchanged shapes keep their identity, so the scene diffs cheaply."
    inputs = (bolt.Input("shapes", "shape", multi=True),)
    outputs = (bolt.Output("scene", "scene"),)

    def cook(self, ctx: bolt.CookContext) -> None:
        ctx.set("scene", {shape.name: shape for shape in ctx.get("shapes") if shape is not None})


class OffsetNode(bolt.Node):
    type_name = "toy.offset"
    ui = {"icon": "open_with"}
    category = "Toy render"
    description = "Moves one shape of the scene, copying only that shape: the rest is shared with the input."
    inputs = (bolt.Input("scene", "scene", required=True),)
    parameters = (bolt.Parameter("shape", "string"),
                  bolt.Parameter("dx", "float", 0.0, ui={"step": 0.05}),
                  bolt.Parameter("dy", "float", 0.0, ui={"step": 0.05}))
    outputs = (bolt.Output("scene_out", "scene"),)
    passthrough = {"scene_out": "scene"}

    def __init__(self, name: str | None = None) -> None:
        super().__init__(name)
        self._moved: tuple[Sphere, float, float, Sphere] | None = None

    def cook(self, ctx: bolt.CookContext) -> None:
        scene = ctx.get("scene")
        name = ctx.get("shape")
        shape = scene.get(name)
        if shape is None:
            ctx.set("scene_out", scene)
            return
        dx, dy = ctx.get("dx"), ctx.get("dy")
        cached = self._moved
        if cached is not None and cached[0] is shape and cached[1:3] == (dx, dy):
            moved = cached[3]
        else:
            moved = dataclasses.replace(shape, x=shape.x + dx, y=shape.y + dy)
            self._moved = (shape, dx, dy, moved)
        ctx.set("scene_out", bolt.copy_with(scene, {name: moved}))


class RenderNode(bolt.Node):
    """The "last node": it turns graph changes into updates of a renderer it owns, then the view shows the pixels."""

    type_name = "toy.render"
    ui = {"icon": "photo_camera"}
    category = "Toy render"
    description = "Sends the scene to a background progressive renderer: deltas when possible, full scenes otherwise."
    inputs = (bolt.Input("scene", "scene", required=True),)
    parameters = (bolt.Parameter("width", "int", 320, ui={"min": 16, "max": 4096}),
                  bolt.Parameter("height", "int", 240, ui={"min": 16, "max": 4096}),
                  bolt.Parameter("background", "color", "#15171a"))

    def __init__(self, name: str | None = None) -> None:
        super().__init__(name)
        self.session: RenderSession | None = None

    def on_attached(self) -> None:
        self.session = RenderSession()

    def on_detached(self) -> None:
        if self.session is not None:
            self.session.close()
            self.session = None

    def cook(self, ctx: bolt.CookContext) -> None:
        session = self.session
        session.configure(ctx.get("width"), ctx.get("height"), ctx.get("background"))
        change = ctx.change("scene")
        if change.kind is bolt.ChangeKind.delta:
            if not change.delta.empty:
                session.apply(change.delta)
                ctx.info(session.stats.last_update)
        elif change.kind is bolt.ChangeKind.replaced:
            session.load(change.value)
            ctx.info(f"full scene: {len(change.value)} shape(s)")
