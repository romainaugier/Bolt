"""Example plugin: a custom data type and two nodes, loaded with `bolt -p examples/plugins ...`."""

from __future__ import annotations

from dataclasses import dataclass

import bolt


@dataclass(frozen=True)
class Shot:
    sequence: str
    name: str
    first_frame: int
    last_frame: int


class ShotType(bolt.DataType):
    __slots__ = ()

    def coerce(self, value):
        if value is None or isinstance(value, Shot):
            return value
        if isinstance(value, dict):
            return Shot(**value)
        raise bolt.InvalidValueError(f"cannot convert {value!r} to shot")

    def serialize(self, value):
        return None if value is None else {"sequence": value.sequence, "name": value.name,
                                           "first_frame": value.first_frame, "last_frame": value.last_frame}


shot_type = ShotType("shot", Shot, ui={"color": "#e8a33d"})


class MakeShot(bolt.Node):
    type_name = "shots.make"
    category = "Shots"
    parameters = (bolt.Parameter("sequence", "string", "sq010"),
                  bolt.Parameter("name", "string", "sh010"),
                  bolt.Parameter("first_frame", "int", 1001),
                  bolt.Parameter("last_frame", "int", 1100))
    outputs = (bolt.Output("shot", "shot"),)

    def cook(self, ctx: bolt.CookContext) -> None:
        ctx.set("shot", Shot(ctx.get("sequence"), ctx.get("name"), ctx.get("first_frame"), ctx.get("last_frame")))


class ShotPath(bolt.Node):
    type_name = "shots.path"
    category = "Shots"
    inputs = (bolt.Input("shot", "shot", required=True),)
    parameters = (bolt.Parameter("template", "string", "$(PROJECT_ROOT)/{sequence}/{name}/{name}.####.exr"),)
    outputs = (bolt.Output("path", "path"), bolt.Output("frames", "list"))

    def cook(self, ctx: bolt.CookContext) -> None:
        shot = ctx.get("shot")
        ctx.set("path", ctx.get("template").format(sequence=shot.sequence, name=shot.name))
        ctx.set("frames", list(range(shot.first_frame, shot.last_frame + 1)))
