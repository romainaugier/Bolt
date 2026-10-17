"""The icon library of the original Bolt: a folder of images looked up by file name, painted in theme colors.

The shipped icons are Google's Material Symbols (Rounded, weight 400, Apache 2.0), named as in Material: "play_arrow",
"check_circle-fill"... library.icon("save", theme.text), library.pixmap("tune", 18, theme.node_text) and
bind_icon(button, "close") read them, and any folder added with add_directory() (plugins call ui.register_icons()).
SVG icons stay sharp at every size; PNG, GIF and JPEG images work too."""

from __future__ import annotations

import functools
import os
from collections.abc import Iterable

from PySide6.QtCore import QObject, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QIcon, QMovie, QPainter, QPen, QPixmap
from PySide6.QtSvg import QSvgRenderer

from bolt.ui import theme

builtin_directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "icons")
icon_sizes = (16, 20, 24, 32, 48, 64)


class IconLibrary:
    """Images found in icon folders, by file name without extension. Folders added later override earlier ones."""

    extensions = frozenset((".svg", ".png", ".gif", ".jpg", ".jpeg", ".ico"))

    def __init__(self, directories: Iterable[str] = ()) -> None:
        self.directories: list[str] = []
        self._files: dict[str, str] = {}
        self._pixmaps: dict[tuple[str, int, str], QPixmap] = {}
        self._icons: dict[tuple[str, str], QIcon] = {}

        for directory in directories:
            self.add_directory(directory)

    def add_directory(self, directory: str) -> list[str]:
        names = []

        for entry in sorted(os.listdir(directory)):
            name, extension = os.path.splitext(entry)

            if extension.lower() in self.extensions:
                self._files[name] = os.path.join(directory, entry)
                names.append(name)

        self.directories.append(directory)
        self._clear_caches()

        return names

    def add_file(self, path: str, name: str | None = None) -> str:
        name = name or os.path.splitext(os.path.basename(path))[0]

        self._files[name] = path
        self._clear_caches()

        return name

    def names(self) -> list[str]:
        return sorted(self._files)

    def __contains__(self, name: str) -> bool:
        return name in self._files

    def path(self, name: str) -> str | None:
        """The file of an icon name, or name itself when it is the path of an existing image."""
        path = self._files.get(name)

        if path is None and os.path.splitext(name)[1].lower() in self.extensions and os.path.isfile(name):
            path = name

        return path

    def pixmap(self, name: str, extent: int = 0, color: QColor | None = None) -> QPixmap:
        """The image fitted in extent x extent (0 keeps its own size), its opaque pixels painted in color if given.
        An unknown name gives a null pixmap."""
        key = (name, extent, _color_key(color))
        pixmap = self._pixmaps.get(key)

        if pixmap is None:
            pixmap = self._load(name, extent, color)
            self._pixmaps[key] = pixmap

        return pixmap

    def icon(self, name: str, color: QColor | None = None) -> QIcon:
        """The image as an icon, rendered at the usual icon sizes (from the vector source for SVG files). An unknown
        name gives a null icon."""
        key = (name, _color_key(color))
        result = self._icons.get(key)

        if result is None:
            result = QIcon()
            path = self.path(name)

            if path is not None and path.lower().endswith(".svg"):
                for extent in icon_sizes:
                    result.addPixmap(self.pixmap(name, extent, color))
            elif path is not None:
                result.addPixmap(self.pixmap(name, 0, color))

            self._icons[key] = result

        return result

    def movie(self, name: str, parent: QObject | None = None) -> QMovie:
        """A new animation (each user gets its own, to start and stop it independently)."""
        movie = QMovie(self.path(name) or "", parent=parent)
        movie.setCacheMode(QMovie.CacheAll)

        return movie

    def _clear_caches(self) -> None:
        self._pixmaps.clear()
        self._icons.clear()

    def _load(self, name: str, extent: int, color: QColor | None) -> QPixmap:
        path = self.path(name)

        if path is None:
            return QPixmap()

        if path.lower().endswith(".svg"):
            renderer = QSvgRenderer(path)

            if not renderer.isValid():
                return QPixmap()

            size = renderer.defaultSize().scaled(QSize(extent, extent), Qt.KeepAspectRatio) if extent else renderer.defaultSize()

            pixmap = QPixmap(size)
            pixmap.fill(Qt.transparent)

            painter = QPainter(pixmap)
            renderer.render(painter, QRectF(0, 0, size.width(), size.height()))
            painter.end()
        else:
            pixmap = QPixmap(path)

            if pixmap.isNull() and path.lower().endswith(".gif"):
                movie = QMovie(path)
                movie.jumpToFrame(0)
                pixmap = movie.currentPixmap()

            if pixmap.isNull():
                return pixmap

            if extent:
                pixmap = pixmap.scaled(QSize(extent, extent), Qt.KeepAspectRatio, Qt.SmoothTransformation)

        if color is not None:
            pixmap = tinted(pixmap, color)

        return pixmap


def _color_key(color: QColor | None) -> str:
    return color.name(QColor.HexArgb) if color is not None else ""


def tinted(pixmap: QPixmap, color: QColor) -> QPixmap:
    """The pixmap's shape filled with color, keeping its antialiased edges."""
    result = QPixmap(pixmap.size())
    result.setDevicePixelRatio(pixmap.devicePixelRatio())
    result.fill(Qt.transparent)
    painter = QPainter(result)
    painter.drawPixmap(0, 0, pixmap)
    painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
    painter.fillRect(result.rect(), color)
    painter.end()

    return result


library = IconLibrary([builtin_directory])


spinner_frame_count = 24


@functools.lru_cache(maxsize=64)
def spinner_frame(extent: int, color: str, frame: int) -> QPixmap:
    """One frame of a Material circular progress indicator: a three-quarter arc turning clockwise."""
    pixmap = QPixmap(extent, extent)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    width = extent * 0.12
    painter.setPen(QPen(QColor(color), width, Qt.SolidLine, Qt.RoundCap))
    margin = width / 2 + extent * 0.08
    start = 90 - frame * 360 / spinner_frame_count
    painter.drawArc(QRectF(margin, margin, extent - 2 * margin, extent - 2 * margin), int(start * 16), -270 * 16)
    painter.end()

    return pixmap


class Spinner(QObject):
    """Drives a cooking indicator: emits advanced on every frame while started."""

    advanced = Signal()

    def __init__(self, parent: QObject | None = None, interval: int = 40) -> None:
        super().__init__(parent)
        self.frame = 0
        self._timer = QTimer(self)
        self._timer.setInterval(interval)
        self._timer.timeout.connect(self._advance)

    @property
    def running(self) -> bool:
        return self._timer.isActive()

    def start(self) -> None:
        if not self._timer.isActive():
            self._timer.start()

    def stop(self) -> None:
        self._timer.stop()

    def pixmap(self, extent: int, color: QColor) -> QPixmap:
        return spinner_frame(extent, color.name(QColor.HexArgb), self.frame)

    def _advance(self) -> None:
        self.frame = (self.frame + 1) % spinner_frame_count
        self.advanced.emit()


class _IconBinding(QObject):
    def __init__(self, target: QObject, name: str, role: str | None) -> None:
        super().__init__(target)

        self.name = name
        self.role = role

        theme.notifier().changed.connect(self.refresh)

        self.refresh()

    def refresh(self) -> None:
        self.parent().setIcon(library.icon(self.name, getattr(theme, self.role) if self.role else None))


def bind_icon(target: QObject, name: str, role: str | None = "text") -> None:
    """Give a widget or action an icon from the library painted in a theme color role ("text", "muted", "accent"...),
    repainted whenever the theme changes. role=None keeps the image's own colors."""
    _IconBinding(target, name, role)


def icon(name: str, color: QColor | None = None) -> QIcon:
    return library.icon(name, color)
