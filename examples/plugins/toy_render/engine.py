from __future__ import annotations

import math
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

from bolt import MappingDelta

from .scene import Color, Sphere

Region = tuple[int, int, int, int]
Listener = Callable[[str], None]

light = (-0.45, 0.55, 0.7)
_light_length = math.sqrt(sum(component * component for component in light))
light = tuple(component / _light_length for component in light)
block_sizes = (16, 8, 4, 2, 1)
bucket = 32


@dataclass
class Stats:
    updates: int = 0
    last_update: str = ""
    passes: int = 0
    pixels: int = 0
    region: Region | None = None
    rendering: bool = False
    frame_time: float = 0.0
    history: list[str] = field(default_factory=list)


class RenderSession:
    """A background renderer: it owns its scene, gets full scenes or deltas, and refines the image progressively.

    Listeners are called from the render thread with "progress", "resized" or "idle"; they must not block."""

    def __init__(self, width: int = 320, height: int = 240, background: Color = (0.08, 0.09, 0.1)) -> None:
        self.width = width
        self.height = height
        self.background = background
        self.buffer = bytearray(width * height * 4)
        self.stats = Stats()
        self._scene: dict[str, Sphere] = {}
        self._listeners: list[Listener] = []
        self._listeners_lock = threading.Lock()
        self._condition = threading.Condition()
        self._dirty: Region | None = None
        self._generation = 0
        self._closing = False
        self._fill(self.buffer, background)
        self._thread = threading.Thread(target=self._run, name="toy-render", daemon=True)
        self._thread.start()

    def add_listener(self, listener: Listener) -> None:
        with self._listeners_lock:
            self._listeners = [*self._listeners, listener]

    def remove_listener(self, listener: Listener) -> None:
        with self._listeners_lock:
            self._listeners = [item for item in self._listeners if item != listener]

    def load(self, scene: Mapping[str, Sphere]) -> None:
        with self._condition:
            self._scene = dict(scene)
            self._record("full scene")
            self._invalidate((0, 0, self.width, self.height))

    def apply(self, delta: MappingDelta) -> None:
        with self._condition:
            region = None
            for name in (*delta.removed, *delta.modified):
                if name in self._scene:
                    region = _union(region, self._scene[name].bounds(self.width, self.height))
            scene = dict(self._scene)
            for name in delta.removed:
                scene.pop(name, None)
            scene.update(delta.added)
            scene.update(delta.modified)
            for shape in (*delta.added.values(), *delta.modified.values()):
                region = _union(region, shape.bounds(self.width, self.height))
            self._scene = scene
            self._record(f"delta: +{len(delta.added)} -{len(delta.removed)} ~{len(delta.modified)}")
            if region is not None:
                self._invalidate(region)

    def configure(self, width: int, height: int, background: Color) -> None:
        with self._condition:
            if (width, height) == (self.width, self.height) and background == self.background:
                return
            resized = (width, height) != (self.width, self.height)
            self.width = width
            self.height = height
            self.background = background
            if resized:
                self.buffer = bytearray(width * height * 4)
                self._fill(self.buffer, background)
            self._invalidate((0, 0, width, height))
        if resized:
            self._notify("resized")

    def close(self) -> None:
        with self._condition:
            self._closing = True
            self._generation += 1
            self._condition.notify_all()
        self._thread.join(timeout=2)

    def _record(self, text: str) -> None:
        self.stats.updates += 1
        self.stats.last_update = text
        self.stats.history = (self.stats.history + [text])[-8:]

    def _invalidate(self, region: Region) -> None:
        self._dirty = _union(self._dirty, region)
        self._generation += 1
        self._condition.notify_all()

    def _run(self) -> None:
        while True:
            with self._condition:
                self._condition.wait_for(lambda: self._closing or self._dirty is not None)
                if self._closing:
                    return
                region = self._dirty
                self._dirty = None
                generation = self._generation
                scene = self._scene
                buffer = self.buffer
                width, height, background = self.width, self.height, self.background
            self.stats.rendering = True
            self.stats.region = region
            start = time.perf_counter()
            if self._render(scene, buffer, width, height, background, region, generation):
                self.stats.frame_time = time.perf_counter() - start
                self.stats.rendering = False
                self._notify("idle")

    def _render(self, scene: Mapping[str, Sphere], buffer: bytearray, width: int, height: int, background: Color,
                region: Region, generation: int) -> bool:
        spheres = sorted(scene.values(), key=lambda sphere: -sphere.z)
        left, top, right, bottom = region
        for block in block_sizes:
            self.stats.passes += 1
            for bucket_top in range(top, bottom, bucket):
                for bucket_left in range(left, right, bucket):
                    if self._generation != generation:
                        return False
                    area = (bucket_left, bucket_top, min(bucket_left + bucket, right), min(bucket_top + bucket, bottom))
                    self._render_bucket(spheres, buffer, width, height, background, area, block)
                    self._notify("progress")
        return True

    def _render_bucket(self, spheres: list[Sphere], buffer: bytearray, width: int, height: int, background: Color,
                       area: Region, block: int) -> None:
        left, top, right, bottom = area
        scale = min(width, height) / 2
        candidates = [sphere for sphere in spheres if _overlaps(sphere.bounds(width, height), area)]
        linear_background = tuple(component * component for component in background)
        for y in range(top, bottom, block):
            v = -((y + block / 2) - height / 2) / scale
            for x in range(left, right, block):
                u = ((x + block / 2) - width / 2) / scale
                color = linear_background
                nearest = -math.inf
                for sphere in candidates:
                    dx = u - sphere.x
                    dy = v - sphere.y
                    inside = sphere.radius * sphere.radius - dx * dx - dy * dy
                    if inside <= 0:
                        continue
                    dz = math.sqrt(inside)
                    depth = sphere.z + dz
                    if depth <= nearest:
                        continue
                    nearest = depth
                    normal = (dx / sphere.radius, dy / sphere.radius, dz / sphere.radius)
                    lambert = max(0.0, normal[0] * light[0] + normal[1] * light[1] + normal[2] * light[2])
                    shade = 0.12 + 0.88 * lambert
                    red, green, blue = sphere.color
                    color = (red * red * shade, green * green * shade, blue * blue * shade)
                pixel = bytes((_byte(color[0]), _byte(color[1]), _byte(color[2]), 255))
                row = pixel * (min(x + block, right) - x)
                for line in range(y, min(y + block, bottom)):
                    offset = (line * width + x) * 4
                    buffer[offset:offset + len(row)] = row
                self.stats.pixels += 1

    @staticmethod
    def _fill(buffer: bytearray, color: Color) -> None:
        pixel = bytes((_byte(color[0] ** 2), _byte(color[1] ** 2), _byte(color[2] ** 2), 255))
        buffer[:] = pixel * (len(buffer) // 4)

    def _notify(self, kind: str) -> None:
        for listener in self._listeners:
            listener(kind)


def _byte(value: float) -> int:
    return max(0, min(255, int(math.sqrt(max(value, 0.0)) * 255)))


def _union(first: Region | None, second: Region) -> Region:
    if first is None:
        return second
    return min(first[0], second[0]), min(first[1], second[1]), max(first[2], second[2]), max(first[3], second[3])


def _overlaps(first: Region, second: Region) -> bool:
    return first[0] < second[2] and second[0] < first[2] and first[1] < second[3] and second[1] < first[3]
