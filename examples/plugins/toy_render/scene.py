from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import bolt
from bolt.core.datatypes import DictType

Color = tuple[float, float, float]


@dataclass(frozen=True, slots=True)
class Sphere:
    """Immutable, so scenes can share unchanged spheres between versions (copy-on-write)."""

    name: str
    x: float
    y: float
    z: float
    radius: float
    color: Color

    def bounds(self, width: int, height: int) -> tuple[int, int, int, int]:
        scale = min(width, height) / 2
        left = int((self.x - self.radius) * scale + width / 2) - 1
        right = int((self.x + self.radius) * scale + width / 2) + 2
        top = int((-self.y - self.radius) * scale + height / 2) - 1
        bottom = int((-self.y + self.radius) * scale + height / 2) + 2

        return max(left, 0), max(top, 0), min(right, width), min(bottom, height)


def parse_color(value: Any) -> Color:
    if isinstance(value, str):
        text = value.lstrip("#")

        if len(text) != 6:
            raise bolt.InvalidValueError(f"invalid color {value!r}, expected #rrggbb")

        return tuple(int(text[index:index + 2], 16) / 255 for index in (0, 2, 4))

    if isinstance(value, (list, tuple)) and len(value) == 3:
        return tuple(float(component) for component in value)

    raise bolt.InvalidValueError(f"invalid color {value!r}")


class ColorType(bolt.DataType):
    __slots__ = ()

    def coerce(self, value: Any) -> Any:
        return None if value is None else parse_color(value)

    def serialize(self, value: Any) -> Any:
        return None if value is None else list(value)


class SceneType(DictType):
    """A dict of shapes by name; inherits the identity based diff, merge and apply of dict."""

    __slots__ = ()


color_type = ColorType("color", tuple, default=(0.8, 0.8, 0.8), editable=True,
                       ui={"widget": "color", "color": "#e06c75"})
shape_type = bolt.DataType("shape", Sphere, ui={"color": "#61afef"})
scene_type = SceneType("scene", dict, default_factory=dict, ui={"color": "#c678dd"})
