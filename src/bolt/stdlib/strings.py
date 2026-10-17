from __future__ import annotations

from bolt.core.errors import CookError
from bolt.core.evaluation import CookContext
from bolt.core.node import Node
from bolt.core.plugs import Input, Output, Parameter


class Format(Node):
    type_name = "string.format"
    ui = {"icon": "text_fields"}
    category = "String"
    description = "Formats a template with str.format, using the 'values' dict as keyword arguments."
    inputs = (Input("values", "dict"),)
    parameters = (Parameter("template", "string"),)
    outputs = (Output("result", "string"),)

    def cook(self, ctx: CookContext) -> None:
        try:
            ctx.set("result", ctx.get("template").format(**ctx.get("values")))
        except (KeyError, IndexError, ValueError) as error:
            raise CookError(f"cannot format template: {error!r}") from error


class Join(Node):
    type_name = "string.join"
    ui = {"icon": "text_fields"}
    category = "String"
    inputs = (Input("items", "list"),)
    parameters = (Parameter("separator", "string", " "),)
    outputs = (Output("result", "string"),)

    def cook(self, ctx: CookContext) -> None:
        ctx.set("result", ctx.get("separator").join(str(item) for item in ctx.get("items")))


class Replace(Node):
    type_name = "string.replace"
    ui = {"icon": "text_fields"}
    category = "String"
    inputs = (Input("text", "string"),)
    parameters = (Parameter("old", "string"), Parameter("new", "string"))
    outputs = (Output("result", "string"),)

    def cook(self, ctx: CookContext) -> None:
        ctx.set("result", ctx.get("text").replace(ctx.get("old"), ctx.get("new")))
