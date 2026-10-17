"""Colors and a few metrics of the editor, as a Theme that can be changed while the application runs.

Read colors as module attributes (theme.text, theme.node_header...): they always come from the current theme, so
paint code picks up a new theme on its next repaint. Widgets styled once (icons...) reconnect to notifier().changed."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import QObject, QPointF, QRectF, QSettings, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontDatabase, QImage, QPainter, QPalette, QPen
from PySide6.QtWidgets import QApplication, QProxyStyle, QStyle, QStyleFactory, QStyleOption, QWidget


@dataclass(frozen=True, slots=True)
class ColorRole:
    key: str
    label: str
    group: str


@dataclass(frozen=True, slots=True)
class MetricRole:
    key: str
    label: str
    minimum: float
    maximum: float
    step: float


color_roles = (
    ColorRole("window", "Window", "Interface"),
    ColorRole("panel", "Panels", "Interface"),
    ColorRole("raised", "Headers and toolbars", "Interface"),
    ColorRole("base", "Lists and text areas", "Interface"),
    ColorRole("field", "Fields", "Interface"),
    ColorRole("field_text", "Field text", "Interface"),
    ColorRole("border", "Separators", "Interface"),
    ColorRole("text", "Text", "Interface"),
    ColorRole("text_strong", "Emphasized text", "Interface"),
    ColorRole("muted", "Secondary text", "Interface"),
    ColorRole("accent", "Accent", "Interface"),
    ColorRole("selection", "Selection", "Interface"),
    ColorRole("selection_text", "Selected text", "Interface"),
    ColorRole("error", "Error", "Interface"),
    ColorRole("warning", "Warning", "Interface"),
    ColorRole("success", "Success", "Interface"),
    ColorRole("display", "Display flag", "Interface"),
    ColorRole("canvas", "Background", "Node editor"),
    ColorRole("grid_minor", "Grid", "Node editor"),
    ColorRole("grid_major", "Grid every 5 cells", "Node editor"),
    ColorRole("node_header", "Node header", "Node editor"),
    ColorRole("node_body", "Node body", "Node editor"),
    ColorRole("node_text", "Node title", "Node editor"),
    ColorRole("node_shadow", "Node shadow", "Node editor"),
    ColorRole("node_selected", "Selection outline", "Node editor"),
    ColorRole("node_veil", "Disabled veil", "Node editor"),
    ColorRole("node_subgraph", "Subgraph header", "Node editor"),
    ColorRole("node_loop", "Loop header", "Node editor"),
    ColorRole("node_branch", "Branch header", "Node editor"),
    ColorRole("type_any", "any", "Data types"),
    ColorRole("type_bool", "bool", "Data types"),
    ColorRole("type_int", "int", "Data types"),
    ColorRole("type_float", "float", "Data types"),
    ColorRole("type_string", "string", "Data types"),
    ColorRole("type_path", "path", "Data types"),
    ColorRole("type_code", "code", "Data types"),
    ColorRole("type_list", "list", "Data types"),
    ColorRole("type_dict", "dict", "Data types"),
)

metric_roles = (
    MetricRole("node_radius", "Node corner radius", 0, 16, 1),
    MetricRole("shadow_offset", "Node shadow offset", 0, 12, 1),
    MetricRole("connection_width", "Connection width", 0.5, 6, 0.25),
)

_color_keys = frozenset(role.key for role in color_roles)
_metric_keys = frozenset(role.key for role in metric_roles)


class Theme:
    __slots__ = ("name", "colors", "metrics")

    def __init__(self, name: str, colors: Mapping[str, Any], metrics: Mapping[str, float]) -> None:
        self.name = name
        self.colors = {key: QColor(value) for key, value in colors.items()}
        self.metrics = {key: float(value) for key, value in metrics.items()}

    def color(self, key: str) -> QColor:
        return QColor(self.colors[key])

    def copy(self, name: str | None = None) -> Theme:
        return Theme(name or self.name, self.colors, self.metrics)

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name,
                "colors": {key: color_name(color) for key, color in self.colors.items()},
                "metrics": dict(self.metrics)}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], base: Theme | None = None) -> Theme:
        """Build a theme from saved data; roles it does not define keep the base theme's values."""
        theme = (base or presets[default_preset]).copy(data.get("name", "Custom"))

        for key, value in data.get("colors", {}).items():
            if key in _color_keys and QColor.isValidColorName(str(value)):
                theme.colors[key] = QColor(str(value))

        for key, value in data.get("metrics", {}).items():
            if key in _metric_keys and isinstance(value, (int, float)):
                theme.metrics[key] = float(value)

        return theme

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Theme) and self.to_dict() == other.to_dict()


def color_name(color: QColor) -> str:
    return color.name(QColor.HexArgb) if color.alpha() < 255 else color.name()


def _with_alpha(color: str, alpha: int) -> QColor:
    result = QColor(color)
    result.setAlpha(alpha)

    return result


_shared_colors = {
    "error": "#ff5370", "warning": "#ffcb6b", "success": "#c3e88d", "display": "#82aaff",
    "canvas": "#292d3e", "grid_minor": _with_alpha("#464b5d", 48), "grid_major": _with_alpha("#464b5d", 127),
    "node_text": "#ffffff", "node_shadow": _with_alpha("#000000", 60), "node_selected": "#ffcb6b",
    "node_veil": _with_alpha("#000000", 100), "node_subgraph": "#7eb862", "node_loop": "#cd684a",
    "node_branch": "#6686c9",
    "type_any": "#f07178", "type_bool": "#eeffff", "type_int": "#82aaff", "type_float": "#89ddff",
    "type_string": "#c3e88d", "type_path": "#80cbc4", "type_code": "#717cb4", "type_list": "#f78c6c",
    "type_dict": "#c792ea",
}

_default_metrics = {"node_radius": 10.0, "shadow_offset": 5.0, "connection_width": 2.0}

presets = {
    "Deep ocean": Theme("Deep ocean", {
        **_shared_colors,
        "window": "#090b10", "panel": "#0f111a", "raised": "#1a1c25", "base": "#0f111a", "field": "#464b5d",
        "field_text": _with_alpha("#eaebff", 180), "border": "#4b526d", "text": "#8f93a2", "text_strong": "#eeffff",
        "muted": "#4b526d", "accent": "#84ffff", "selection": _with_alpha("#717cb4", 128), "selection_text": "#ffffff",
        "node_header": "#1f2233", "node_body": "#1a1c25",
    }, _default_metrics),
    "Palenight": Theme("Palenight", {
        **_shared_colors,
        "window": "#08080a", "panel": "#0d0e19", "raised": "#191924", "base": "#0d0e19", "field": "#454a5c",
        "field_text": _with_alpha("#eaebff", 180), "border": "#4a526b", "text": "#8f90a0", "text_strong": "#ffffff",
        "muted": "#4a526b", "accent": "#68f0de", "selection": "#404566", "selection_text": "#ffffff",
        "node_header": "#1e1f33", "node_body": "#191924", "error": "#ea424a",
    }, _default_metrics),
}
default_preset = "Deep ocean"
settings_key = "theme"

_current = presets[default_preset].copy()


class ThemeNotifier(QObject):
    changed = Signal()


_notifier: ThemeNotifier | None = None


def notifier() -> ThemeNotifier:
    global _notifier

    if _notifier is None:
        _notifier = ThemeNotifier(QApplication.instance())

    return _notifier


def current() -> Theme:
    return _current


def __getattr__(name: str) -> Any:
    if name in _color_keys:
        return QColor(_current.colors[name])

    if name in _metric_keys:
        return _current.metrics[name]

    raise AttributeError(f"module 'bolt.ui.theme' has no attribute '{name}'")


_settings: QSettings | None = None


def set_theme(theme: Theme, application: QApplication | None = None) -> None:
    """Make a theme current, restyle the application, save it if use_settings() was called, and tell the widgets
    styled once to update."""
    global _current

    _current = theme.copy()

    application = application or QApplication.instance()

    if application is not None:
        apply(application)

    if _settings is not None:
        save(_settings)

    notifier().changed.emit()


def use_settings(settings: QSettings | None) -> None:
    """Make the theme saved in settings current and save every later change there (None stops saving)."""
    global _settings

    _settings = None

    if settings is not None:
        set_theme(load(settings))

    _settings = settings


def load(settings: QSettings) -> Theme:
    text = settings.value(settings_key)

    if not text:
        return presets[default_preset].copy()

    try:
        return Theme.from_dict(json.loads(text))
    except (TypeError, ValueError):
        return presets[default_preset].copy()


def save(settings: QSettings, theme: Theme | None = None) -> None:
    settings.setValue(settings_key, json.dumps((theme or _current).to_dict()))


def apply(application: QApplication) -> None:
    global _style

    if _style is None:
        _style = BoltStyle()
        application.setStyle(_style)

    palette = QPalette()

    for role, key in ((QPalette.Window, "panel"), (QPalette.WindowText, "text"), (QPalette.Base, "base"),
                      (QPalette.AlternateBase, "raised"), (QPalette.Text, "text"), (QPalette.Button, "raised"),
                      (QPalette.ButtonText, "text"), (QPalette.Highlight, "selection"),
                      (QPalette.HighlightedText, "selection_text"), (QPalette.ToolTipBase, "raised"),
                      (QPalette.ToolTipText, "text_strong"), (QPalette.PlaceholderText, "muted"),
                      (QPalette.BrightText, "text_strong"), (QPalette.Link, "accent")):
        palette.setColor(role, _current.colors[key])

    palette.setColor(QPalette.Disabled, QPalette.Text, _current.colors["muted"])
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, _current.colors["muted"])
    palette.setColor(QPalette.Disabled, QPalette.WindowText, _current.colors["muted"])

    application.setPalette(palette)
    application.setStyleSheet(stylesheet(_current))


_chevrons = {QStyle.PE_IndicatorArrowDown: ((-1, -0.5), (0, 0.5), (1, -0.5)),
             QStyle.PE_IndicatorSpinDown: ((-1, -0.5), (0, 0.5), (1, -0.5)),
             QStyle.PE_IndicatorSpinMinus: ((-1, -0.5), (0, 0.5), (1, -0.5)),
             QStyle.PE_IndicatorArrowUp: ((-1, 0.5), (0, -0.5), (1, 0.5)),
             QStyle.PE_IndicatorSpinUp: ((-1, 0.5), (0, -0.5), (1, 0.5)),
             QStyle.PE_IndicatorSpinPlus: ((-1, 0.5), (0, -0.5), (1, 0.5)),
             QStyle.PE_IndicatorArrowRight: ((-0.5, -1), (0.5, 0), (-0.5, 1)),
             QStyle.PE_IndicatorArrowLeft: ((0.5, -1), (-0.5, 0), (0.5, 1))}


_directions = {"down": QStyle.PE_IndicatorArrowDown, "up": QStyle.PE_IndicatorArrowUp,
               "left": QStyle.PE_IndicatorArrowLeft, "right": QStyle.PE_IndicatorArrowRight}


def draw_chevron(painter: QPainter, rect: QRectF, points: Sequence[tuple[float, float]], color: QColor,
                 size: float = 0.22) -> None:
    half = min(rect.width(), rect.height()) * size

    center = rect.center()

    painter.save()
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(QPen(color, max(1.3, half * 0.45), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    painter.drawPolyline([center + QPointF(x * half, y * half) for x, y in points])
    painter.restore()


class BoltStyle(QProxyStyle):
    """Fusion with flat chevrons in the theme's colors instead of its beveled arrows, and no mnemonic underlines
    (Alt shortcuts still work)."""

    def __init__(self) -> None:
        super().__init__(QStyleFactory.create("Fusion"))

    def styleHint(self, hint: QStyle.StyleHint, option: QStyleOption | None = None, widget: QWidget | None = None,
                  data: Any = None) -> int:
        if hint == QStyle.SH_UnderlineShortcut:
            return 0

        return super().styleHint(hint, option, widget, data)

    def drawPrimitive(self, element: QStyle.PrimitiveElement, option: QStyleOption, painter: QPainter,
                      widget: QWidget | None = None) -> None:
        points = _chevrons.get(element)

        if points is not None:
            enabled = bool(option.state & QStyle.State_Enabled)
            hovered = bool(option.state & QStyle.State_MouseOver)
            color = _current.colors["text_strong" if hovered else "text"] if enabled else _current.colors["muted"]
            draw_chevron(painter, QRectF(option.rect), points, color)
            return

        if element == QStyle.PE_IndicatorBranch:
            if option.state & QStyle.State_Children:
                opened = bool(option.state & QStyle.State_Open)
                draw_chevron(painter, QRectF(option.rect), _chevrons[QStyle.PE_IndicatorArrowDown if opened
                                                                     else QStyle.PE_IndicatorArrowRight],
                             _current.colors["muted"])
            return

        super().drawPrimitive(element, option, painter, widget)


_style: BoltStyle | None = None
_image_directory: tempfile.TemporaryDirectory | None = None


def chevron_image(direction: str, color: QColor) -> str:
    """Path of a chevron image for stylesheets, whose sub-controls (combo and spin box arrows) only accept files."""
    global _image_directory

    if _image_directory is None:
        _image_directory = tempfile.TemporaryDirectory(prefix="bolt-theme-")

    path = os.path.join(_image_directory.name, f"{direction}_{color.name(QColor.HexArgb)[1:]}.png")

    if not os.path.exists(path):
        image = QImage(32, 32, QImage.Format_ARGB32_Premultiplied)
        image.fill(Qt.transparent)
        painter = QPainter(image)

        draw_chevron(painter, QRectF(0, 0, 32, 32), _chevrons[_directions[direction]], color, 0.36)

        painter.end()
        image.save(path)

    return path.replace(os.sep, "/")


def _css(color: QColor) -> str:
    return f"rgba({color.red()}, {color.green()}, {color.blue()}, {color.alpha()})"


def stylesheet(theme: Theme) -> str:
    c = {key: _css(color) for key, color in theme.colors.items()}
    hover = _with_alpha(theme.colors["border"].name(), 127)
    soft = _with_alpha(theme.colors["border"].name(), 63)
    field_hover = theme.colors["field"].lighter(112)

    def arrow(direction: str, role: str) -> str:
        color = QColor(theme.colors["text"])

        if role == "muted":
            color.setAlpha(90)
        return chevron_image(direction, color)

    return f"""
QWidget {{ font-size: 12px; color: {c["text"]}; }}
QMainWindow, QMenuBar, QToolBar, QStatusBar {{ background: {c["window"]}; }}
QToolBar {{ border: none; spacing: 4px; padding: 2px 6px; }}
QStatusBar {{ color: {c["muted"]}; }}
QToolTip {{ color: {c["text_strong"]}; background: {c["raised"]}; border: 1px solid {c["border"]}; padding: 4px; }}
QSplitter::handle {{ background: {c["window"]}; }}
QSplitter::handle:hover {{ background: {c["border"]}; }}
QSplitter::handle:horizontal {{ width: 4px; }}
QSplitter::handle:vertical {{ height: 4px; }}
QFrame#pane {{ background: {c["panel"]}; border: none; border-radius: 6px; }}
QWidget#pane_header {{ background: {c["raised"]}; border-top-left-radius: 6px; border-top-right-radius: 6px; }}
QTabBar::tab {{ background: transparent; color: {c["muted"]}; padding: 6px 10px; border: none; }}
QTabBar::tab:selected {{ color: {c["text_strong"]}; border-bottom: 2px solid {c["accent"]}; }}
QTabBar::tab:hover {{ color: {c["text"]}; }}
QMenuBar::item {{ background: transparent; padding: 4px 8px; }}
QMenuBar::item:selected, QMenu::item:selected {{ color: {c["selection_text"]}; background: {c["selection"]}; }}
QMenu {{ background: {c["panel"]}; border: 1px solid {c["raised"]}; border-radius: 6px; padding: 4px; }}
QMenu::item {{ color: {c["text"]}; background: transparent; padding: 5px 18px; border-radius: 4px; }}
QMenu::separator {{ height: 1px; background: {c["raised"]}; margin: 4px 6px; }}
QToolButton::menu-indicator {{ image: none; width: 0; }}
QToolButton {{ border: none; padding: 3px; border-radius: 4px; background: transparent; }}
QToolButton:hover {{ background: {_css(hover)}; }}
QToolButton:checked {{ background: {c["selection"]}; color: {c["selection_text"]}; }}
QPushButton {{ color: {c["text"]}; background: {_css(soft)}; border: none; border-radius: 4px; padding: 4px 10px; }}
QPushButton:hover:!pressed {{ background: {_css(hover)}; }}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    color: {c["field_text"]}; background: {c["field"]}; border: none; border-radius: 3px; padding: 3px 5px;
    selection-color: {c["selection_text"]}; selection-background-color: {c["selection"]}; }}
QLineEdit[expression="true"] {{ color: {c["warning"]}; }}
QLineEdit#heading {{ font-size: 14px; color: {c["text_strong"]}; background: transparent; padding-left: 0; }}
QComboBox {{ padding-right: 20px; }}
QComboBox:hover, QAbstractSpinBox:hover {{ background: {_css(field_hover)}; }}
QComboBox:on {{ background: {_css(field_hover)}; }}
QComboBox::drop-down {{ subcontrol-origin: padding; subcontrol-position: center right; width: 20px; border: none;
    background: transparent; }}
QComboBox::down-arrow {{ image: url({arrow("down", "text")}); width: 10px; height: 10px; }}
QComboBox::down-arrow:disabled {{ image: url({arrow("down", "muted")}); }}
QAbstractSpinBox {{ padding-right: 18px; }}
QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {{ subcontrol-origin: border; width: 18px; border: none;
    background: transparent; }}
QAbstractSpinBox::up-button {{ subcontrol-position: top right; border-top-right-radius: 3px; }}
QAbstractSpinBox::down-button {{ subcontrol-position: bottom right; border-bottom-right-radius: 3px; }}
QAbstractSpinBox::up-button:hover, QAbstractSpinBox::down-button:hover {{ background: {_css(hover)}; }}
QAbstractSpinBox::up-button:pressed, QAbstractSpinBox::down-button:pressed {{ background: {c["selection"]}; }}
QAbstractSpinBox::up-arrow {{ image: url({arrow("up", "text")}); width: 9px; height: 9px; }}
QAbstractSpinBox::down-arrow {{ image: url({arrow("down", "text")}); width: 9px; height: 9px; }}
QAbstractSpinBox::up-arrow:disabled, QAbstractSpinBox::up-arrow:off {{ image: url({arrow("up", "muted")}); }}
QAbstractSpinBox::down-arrow:disabled, QAbstractSpinBox::down-arrow:off {{ image: url({arrow("down", "muted")}); }}
QComboBox QAbstractItemView {{ background: {c["panel"]}; color: {c["text"]}; border: 1px solid {c["raised"]};
    selection-background-color: {c["selection"]}; selection-color: {c["selection_text"]}; }}
QPlainTextEdit, QTextEdit {{ color: {c["text"]}; background: {c["base"]}; border: none; border-radius: 3px;
    selection-color: {c["selection_text"]}; selection-background-color: {c["selection"]}; }}
QTreeWidget, QTreeView, QListWidget, QListView, QTableWidget, QTableView {{
    color: {c["text"]}; background: {c["base"]}; alternate-background-color: {c["raised"]}; border: none;
    selection-color: {c["selection_text"]}; selection-background-color: {c["selection"]}; }}
QHeaderView::section {{ background: {c["raised"]}; color: {c["muted"]}; border: none; padding: 4px; }}
QCheckBox {{ spacing: 6px; }}
QCheckBox::indicator {{ width: 12px; height: 12px; border-radius: 3px; }}
QCheckBox::indicator:unchecked {{ background: {c["error"]}; }}
QCheckBox::indicator:checked {{ background: {c["success"]}; }}
QProgressBar {{ background: {c["field"]}; border: none; border-radius: 3px; color: {c["text_strong"]};
    text-align: center; }}
QProgressBar::chunk {{ background: {c["accent"]}; border-radius: 3px; }}
QScrollBar:vertical {{ background: {c["window"]}; width: 10px; border: none; margin: 0; }}
QScrollBar:horizontal {{ background: {c["window"]}; height: 10px; border: none; margin: 0; }}
QScrollBar::handle:vertical {{ background: {c["field"]}; min-height: 24px; border-radius: 5px; }}
QScrollBar::handle:horizontal {{ background: {c["field"]}; min-width: 24px; border-radius: 5px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; border: none; background: none; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}
QScrollArea {{ background: transparent; border: none; }}
QLabel#error {{ color: {c["error"]}; background: {c["raised"]}; border-radius: 4px; padding: 6px; }}
QLabel#heading {{ font-size: 14px; color: {c["text_strong"]}; }}
QLabel#muted {{ color: {c["muted"]}; }}
QLabel#logo {{ padding: 2px 4px 2px 10px; background: transparent; }}
"""


def monospace() -> QFont:
    return QFontDatabase.systemFont(QFontDatabase.FixedFont)


def color_from(value: Any, fallback_key: str, saturation: float = 0.45, lightness: float = 0.6) -> QColor:
    """A color given as '#rrggbb', an (r, g, b) sequence or a stable color derived from fallback_key."""
    if isinstance(value, str) and QColor.isValidColorName(value):
        return QColor(value)

    if isinstance(value, Sequence) and not isinstance(value, str) and len(value) >= 3:
        return QColor(int(value[0]), int(value[1]), int(value[2]))

    hue = int(hashlib.md5(fallback_key.encode()).hexdigest()[:4], 16) / 0xFFFF

    return QColor.fromHslF(hue, saturation, lightness)


def ui_color(ui: Mapping[str, Any], fallback_key: str, **kwargs: float) -> QColor:
    return color_from(ui.get("color"), fallback_key, **kwargs)


def type_color(name: str, ui: Mapping[str, Any]) -> QColor:
    """Theme color of a built-in data type, else the type's own ui color, else a stable color from its name."""
    key = f"type_{name}"

    if key in _current.colors:
        return QColor(_current.colors[key])

    return ui_color(ui, name, saturation=0.6, lightness=0.7)


def node_header_color(ui: Mapping[str, Any]) -> QColor:
    """A node type's header: its ui color, a themed role from its ui style (subgraph, loop, branch), or the default."""
    if "color" in ui:
        return ui_color(ui, "")

    key = f"node_{ui.get('style', 'header')}"

    return QColor(_current.colors.get(key, _current.colors["node_header"]))
