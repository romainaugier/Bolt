from __future__ import annotations

import logging
import time
from collections.abc import Iterable

from bolt.core.errors import CookError
from bolt.core.evaluation import CookContext, Evaluation
from bolt.core.graph import Connection
from bolt.core.node import Node
from bolt.core.plugs import Input, Output, Parameter

_levels = {"debug": logging.DEBUG, "info": logging.INFO, "warning": logging.WARNING, "error": logging.ERROR}


class Switch(Node):
    type_name = "flow.switch"
    category = "Flow"
    ui = {"style": "branch", "icon": "alt_route"}
    description = "Forwards the input selected by 'index'. Only the selected branch is evaluated."
    inputs = (Input("inputs", "any", multi=True),)
    parameters = (Parameter("index", "int", 0),)
    outputs = (Output("result", "any"),)

    def active_connections(self, evaluation: Evaluation) -> Iterable[Connection]:
        connections = self.plug("inputs").connections
        index = evaluation.parameter(self, "index")

        if 0 <= index < len(connections):
            return connections[index:index + 1]

        return ()

    def cook(self, ctx: CookContext) -> None:
        index = ctx.get("index")
        count = ctx.connection_count("inputs")

        if not 0 <= index < count:
            raise CookError(f"index {index} is out of range, {count} inputs are connected")

        ctx.set("result", ctx.get_item("inputs", index))


class Merge(Node):
    type_name = "flow.merge"
    category = "Flow"
    description = "Gathers every connected input into a list, in connection order."
    inputs = (Input("inputs", "any", multi=True),)
    parameters = (Parameter("flatten", "bool", False),)
    outputs = (Output("result", "list"),)

    def cook(self, ctx: CookContext) -> None:
        values = ctx.get("inputs")

        if ctx.get("flatten"):
            values = [item for value in values for item in (value if isinstance(value, (list, tuple)) else (value,))]

        ctx.set("result", values)


class Passthrough(Node):
    type_name = "flow.passthrough"
    category = "Flow"
    inputs = (Input("input", "any"),)
    outputs = (Output("result", "any"),)

    def cook(self, ctx: CookContext) -> None:
        ctx.set("result", ctx.get("input"))


class Log(Node):
    type_name = "flow.log"
    ui = {"icon": "sticky_note_2"}
    category = "Flow"
    description = "Logs a message, then forwards its input."
    inputs = (Input("input", "any"),)
    parameters = (Parameter("message", "string", "{value}"),
                  Parameter("level", "string", "info", ui={"choices": list(_levels)}))
    outputs = (Output("result", "any"),)

    def cook(self, ctx: CookContext) -> None:
        value = ctx.get("input")
        level = _levels.get(ctx.get("level").lower())

        if level is None:
            raise CookError(f"unknown level '{ctx.get('level')}', expected one of {', '.join(_levels)}")

        ctx.log(level, ctx.get("message").replace("{value}", str(value)))
        ctx.set("result", value)


class Fail(Node):
    type_name = "flow.fail"
    ui = {"icon": "report"}
    category = "Flow"
    description = "Fails the evaluation with a message when 'condition' is true, otherwise forwards its input."
    inputs = (Input("input", "any"),)
    parameters = (Parameter("condition", "bool", True), Parameter("message", "string", "failed"))
    outputs = (Output("result", "any"),)

    def cook(self, ctx: CookContext) -> None:
        if ctx.get("condition"):
            raise CookError(ctx.get("message"))

        ctx.set("result", ctx.get("input"))


class Sleep(Node):
    type_name = "flow.sleep"
    ui = {"icon": "hourglass_empty"}
    category = "Flow"
    inputs = (Input("input", "any"),)
    parameters = (Parameter("seconds", "float", 1.0),)
    outputs = (Output("result", "any"),)

    def cook(self, ctx: CookContext) -> None:
        deadline = time.monotonic() + ctx.get("seconds")

        while True:
            remaining = deadline - time.monotonic()

            if remaining <= 0:
                break

            ctx.checkpoint()
            time.sleep(min(remaining, 0.05))

        ctx.set("result", ctx.get("input"))
