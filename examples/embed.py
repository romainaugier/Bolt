"""Embedding Bolt in a host application, e.g. a renderer: register native types and nodes, then pull a viewer per frame."""

from __future__ import annotations

import bolt


class Image:
    def __init__(self, width: int, height: int, value: float) -> None:
        self.width = width
        self.height = height
        self.value = value

    def __repr__(self) -> str:
        return f"Image({self.width}x{self.height}, value={self.value:.3f})"


class Constant(bolt.Node):
    type_name = "comp.constant"
    parameters = (bolt.Parameter("width", "int", 1920), bolt.Parameter("height", "int", 1080),
                  bolt.Parameter("value", "float", 0.5))
    outputs = (bolt.Output("image", "image"),)

    def cook(self, ctx: bolt.CookContext) -> None:
        ctx.set("image", Image(ctx.get("width"), ctx.get("height"), ctx.get("value")))


class Gain(bolt.Node):
    type_name = "comp.gain"
    inputs = (bolt.Input("image", "image", required=True),)
    parameters = (bolt.Parameter("gain", "float", 1.0),)
    outputs = (bolt.Output("image_out", "image"),)
    passthrough = {"image_out": "image"}

    def cook(self, ctx: bolt.CookContext) -> None:
        image = ctx.get("image")
        ctx.set("image_out", Image(image.width, image.height, image.value * ctx.get("gain")))


def main() -> None:
    registry = bolt.Registry()
    registry.register_type(bolt.DataType("image", Image, ui={"color": "#4aa3df", "view": "image_viewer"}))
    registry.register_node(Constant)
    registry.register_node(Gain)

    graph = bolt.Graph(registry, name="comp")
    graph.create_node("comp.constant", "plate")
    graph.create_node("comp.gain", "flicker", values={"gain": "`1 + 0.1 * sin(FRAME)`"})
    graph.connect("plate.image", "flicker.image")

    cooked = []
    graph.events.subscribe(bolt.events.NodeCooked, lambda event: cooked.append(event.node.name))

    for frame in (1, 2, 2, 3):
        cooked.clear()
        image = graph.pull("flicker.image_out", variables={"FRAME": frame})
        print(f"frame {frame}: {image} cooked={cooked}")


if __name__ == "__main__":
    main()
