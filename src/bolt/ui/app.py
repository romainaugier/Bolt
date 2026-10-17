from __future__ import annotations

import argparse
import importlib.metadata
import logging
import sys
from collections.abc import Iterable, Sequence
from typing import Any

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from bolt.core.errors import BoltError
from bolt.core.live import EditPolicy, LiveMode
from bolt.core.registry import Registry
from bolt.ui import icons, theme
from bolt.ui.collector import GarbageCollector
from bolt.ui.parameters import EditorFactory, ParameterWidgets
from bolt.ui.views import View, ViewRegistry, builtin_views
from bolt.ui.window import MainWindow
from bolt.ui.workspace import Workspace

logger = logging.getLogger("bolt.ui")

ui_entry_point_group = "bolt.ui_plugins"

default_layout: dict[str, Any] = {
    "type": "split", "orientation": "horizontal", "sizes": [980, 420], "children": [
        {"type": "split", "orientation": "vertical", "sizes": [620, 220], "children": [
            {"type": "pane", "views": [{"view": "node_editor"}]},
            {"type": "pane", "views": [{"view": "log"}, {"view": "jobs"}]},
        ]},
        {"type": "split", "orientation": "vertical", "sizes": [520, 320], "children": [
            {"type": "pane", "views": [{"view": "parameters"}]},
            {"type": "pane", "views": [{"view": "node_library"}, {"view": "variables"}]},
        ]},
    ]}


class UiRegistry:
    """What UI plugins extend: a plugin module defining register_ui(ui) receives one of these."""

    def __init__(self) -> None:
        self.views = ViewRegistry()
        self.parameter_widgets = ParameterWidgets()

    def register_view(self, view_class: type[View]) -> type[View]:
        return self.views.register(view_class)

    def register_parameter_widget(self, key: str, factory: EditorFactory) -> None:
        self.parameter_widgets.register(key, factory)

    def register_icons(self, directory: str) -> list[str]:
        """Add a folder of icons (png, svg, gif...) to the icon library; its names override the built-in ones."""
        return icons.library.add_directory(directory)


class Application:
    """The editor, configured by the host: its registry, context, extra views, default layout and live settings."""

    def __init__(self,
                 registry: Registry | None = None,
                 *,
                 name: str = "Bolt",
                 organization: str = "Bolt",
                 context: Any = None,
                 stdlib: bool = True,
                 plugins: Iterable[Any] = (),
                 plugin_paths: Iterable[str] = (),
                 discover: bool = True,
                 views: Iterable[type[View]] = (),
                 layout: dict[str, Any] | None = None,
                 restore_layout: bool = True,
                 live_mode: LiveMode = LiveMode.auto,
                 live_policy: EditPolicy = EditPolicy.restart) -> None:
        self.registry = registry if registry is not None else Registry()
        self.name = name
        self.organization = organization
        self.context = context
        self.default_layout = layout or default_layout
        self.restore_layout = restore_layout
        self.live_mode = live_mode
        self.live_policy = live_policy

        if stdlib and "bolt.stdlib" not in self.registry.plugins:
            self.registry.load_plugin("bolt.stdlib")

        for plugin in plugins:
            self.registry.load_plugin(plugin)

        if discover or plugin_paths:
            self.registry.discover_plugins(plugin_paths, entry_point_group="bolt.plugins" if discover else None,
                                           environment_variable="BOLT_PLUGIN_PATH" if discover else None)
        self.ui = UiRegistry()

        for view_class in (*builtin_views, *views):
            self.ui.register_view(view_class)

        self._load_ui_plugins(discover)
        self.workspace: Workspace | None = None
        self.window: MainWindow | None = None

    def build(self, files: Sequence[str] = ()) -> MainWindow:
        """Create the workspace and main window without entering the event loop (for tests and embedding)."""
        qt_application = QApplication.instance() or QApplication(sys.argv[:1])

        theme.use_settings(QSettings(self.organization, self.name))

        qt_application.setWindowIcon(icons.library.icon("bolt"))

        if qt_application.findChild(GarbageCollector) is None:
            collector = GarbageCollector(qt_application)
            collector.start()
            qt_application.aboutToQuit.connect(collector.stop)

        logging.getLogger("bolt").setLevel(logging.INFO)

        self.workspace = Workspace(self.registry, context=self.context, live_mode=self.live_mode,
                                   live_policy=self.live_policy)
        self.workspace.parameter_widgets = self.ui.parameter_widgets
        self.window = MainWindow(self, self.workspace, self.ui)

        for path in files:
            self.window.open_document(path)

        if not self.workspace.documents:
            self.workspace.new_document()

        return self.window

    def run(self, files: Sequence[str] = ()) -> int:
        window = self.build(files)
        window.show()

        return QApplication.instance().exec()

    def _load_ui_plugins(self, discover: bool) -> None:
        modules = list(self.registry.plugin_modules())

        if discover:
            for entry_point in importlib.metadata.entry_points(group=ui_entry_point_group):
                try:
                    modules.append(entry_point.load())
                except Exception:
                    logger.exception("cannot load the UI plugin '%s'", entry_point.name)

        for module in modules:
            register_ui = getattr(module, "register_ui", None)

            if callable(register_ui):
                try:
                    register_ui(self.ui)
                except Exception:
                    logger.exception("UI plugin %s failed to register", getattr(module, "__name__", module))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="bolt-editor", description="Bolt node graph editor")
    parser.add_argument("files", nargs="*", help="graph files to open")
    parser.add_argument("--plugin", dest="plugins", action="append", default=[], metavar="MODULE_OR_PATH")
    parser.add_argument("-p", "--plugins-path", dest="plugin_paths", action="append", default=[], metavar="PATH")
    parser.add_argument("--no-stdlib", action="store_true")

    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(asctime)s %(message)s", datefmt="%H:%M:%S")

    try:
        application = Application(stdlib=not args.no_stdlib, plugins=args.plugins, plugin_paths=args.plugin_paths)
    except BoltError as error:
        logger.error("%s", error)

        return 1

    return application.run(args.files)
