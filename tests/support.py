from __future__ import annotations

from bolt.core.node import Node
from bolt.core.plugs import Input, Output, Parameter


class Counter:
    def __init__(self) -> None:
        self.names: list[str] = []

    def clear(self) -> None:
        self.names.clear()


cooks = Counter()


class AddNode(Node):
    type_name = "test.add"
    inputs = (Input("a", "float", 0.0), Input("b", "float", 0.0))
    parameters = (Parameter("scale", "float", 1.0),)
    outputs = (Output("result", "float"),)

    def cook(self, ctx) -> None:
        cooks.names.append(self.name)
        ctx.set("result", (ctx.get("a") + ctx.get("b")) * ctx.get("scale"))


class TextNode(Node):
    type_name = "test.text"
    parameters = (Parameter("text", "string"),)
    outputs = (Output("result", "string"),)

    def cook(self, ctx) -> None:
        cooks.names.append(self.name)
        ctx.set("result", ctx.get("text"))


class ConcatNode(Node):
    type_name = "test.concat"
    inputs = (Input("parts", "string", multi=True),)
    outputs = (Output("result", "string"),)

    def cook(self, ctx) -> None:
        cooks.names.append(self.name)
        ctx.set("result", "".join(ctx.get("parts")))


class FailNode(Node):
    type_name = "test.fail"
    inputs = (Input("input", "any"),)
    outputs = (Output("result", "any"),)

    def cook(self, ctx) -> None:
        cooks.names.append(self.name)
        raise RuntimeError("boom")


test_nodes = (AddNode, TextNode, ConcatNode, FailNode)
