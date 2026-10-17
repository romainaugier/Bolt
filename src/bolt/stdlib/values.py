from __future__ import annotations

from bolt.core.evaluation import CookContext
from bolt.core.node import Node
from bolt.core.plugs import Output, Parameter


class _ValueNode(Node):
    category = "Values"

    def cook(self, ctx: CookContext) -> None:
        ctx.set("result", ctx.get("value"))


class IntValue(_ValueNode):
    type_name = "values.int"
    parameters = (Parameter("value", "int"),)
    outputs = (Output("result", "int"),)


class FloatValue(_ValueNode):
    type_name = "values.float"
    parameters = (Parameter("value", "float"),)
    outputs = (Output("result", "float"),)


class BoolValue(_ValueNode):
    type_name = "values.bool"
    parameters = (Parameter("value", "bool"),)
    outputs = (Output("result", "bool"),)


class StringValue(_ValueNode):
    type_name = "values.string"
    parameters = (Parameter("value", "string"),)
    outputs = (Output("result", "string"),)


class PathValue(_ValueNode):
    type_name = "values.path"
    parameters = (Parameter("value", "path"),)
    outputs = (Output("result", "path"),)


class ListValue(_ValueNode):
    type_name = "values.list"
    parameters = (Parameter("value", "list"),)
    outputs = (Output("result", "list"),)


class DictValue(_ValueNode):
    type_name = "values.dict"
    parameters = (Parameter("value", "dict"),)
    outputs = (Output("result", "dict"),)
