from __future__ import annotations

from bolt.core.errors import CookError
from bolt.core.evaluation import CookContext
from bolt.core.node import Node
from bolt.core.plugs import Input, Output


class _BinaryNode(Node):
    category = "Math"
    inputs = (Input("a", "float"), Input("b", "float"))
    outputs = (Output("result", "float"),)


class Add(_BinaryNode):
    type_name = "math.add"

    def cook(self, ctx: CookContext) -> None:
        ctx.set("result", ctx.get("a") + ctx.get("b"))


class Subtract(_BinaryNode):
    type_name = "math.subtract"

    def cook(self, ctx: CookContext) -> None:
        ctx.set("result", ctx.get("a") - ctx.get("b"))


class Multiply(_BinaryNode):
    type_name = "math.multiply"

    def cook(self, ctx: CookContext) -> None:
        ctx.set("result", ctx.get("a") * ctx.get("b"))


class Divide(_BinaryNode):
    type_name = "math.divide"

    def cook(self, ctx: CookContext) -> None:
        divisor = ctx.get("b")

        if divisor == 0:
            raise CookError("division by zero")

        ctx.set("result", ctx.get("a") / divisor)


class Sum(Node):
    type_name = "math.sum"
    category = "Math"
    inputs = (Input("values", "float", multi=True),)
    outputs = (Output("result", "float"),)

    def cook(self, ctx: CookContext) -> None:
        ctx.set("result", float(sum(ctx.get("values"))))
