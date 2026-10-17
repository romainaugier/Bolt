from __future__ import annotations

import functools
from types import CodeType

from bolt.core.errors import CookError
from bolt.core.evaluation import CookContext
from bolt.core.node import Node
from bolt.core.plugs import Parameter, PlugKind


@functools.lru_cache(maxsize=256)
def _compile(code: str, filename: str) -> CodeType:
    return compile(code, filename, "exec")


class Script(Node):
    """Runs Python code. Add inputs and outputs with add_plug: inputs and parameters are visible as variables,
    outputs are read back from the variables of the same name, and 'ctx' gives access to the cook context."""

    type_name = "python.script"
    ui = {"icon": "code"}
    category = "Python"
    user_plugs = True
    parameters = (Parameter("code", "code", ui={"language": "python"}),)

    def cook(self, ctx: CookContext) -> None:
        try:
            code = _compile(ctx.get("code"), f"<{self.path}>")
        except SyntaxError as error:
            raise CookError(f"syntax error line {error.lineno}: {error.msg}") from None

        namespace = {plug.name: ctx.get(plug.name)
                     for plug in self.plugs()
                     if plug.kind is not PlugKind.output and plug.name != "code"}

        namespace["ctx"] = ctx

        exec(code, namespace)

        for plug in self.output_plugs():
            ctx.set(plug.name, namespace[plug.name] if plug.name in namespace else plug._default())
