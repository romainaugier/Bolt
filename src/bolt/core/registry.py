from __future__ import annotations

import importlib
import importlib.metadata
import importlib.util
import logging
import os
import sys
from collections.abc import Callable, Iterable
from pathlib import Path
from types import ModuleType
from typing import Any, Literal, TypeVar

from bolt.core.errors import PluginError, RegistryError, UnknownNodeTypeError, UnknownTypeError
from bolt.core.node import Node
from bolt.core.datatypes import DataType, builtin_conversions, builtin_types

logger = logging.getLogger("bolt.registry")

NodeClass = TypeVar("NodeClass", bound=type[Node])
Converter = Callable[[Any], Any]

default_entry_point_group = "bolt.plugins"
default_plugin_path_variable = "BOLT_PLUGIN_PATH"


class Registry:
    """Holds the data types, conversions and node types available to a set of graphs. Owned by the host application."""

    __slots__ = ("_types", "_nodes", "_conversions", "_plugins", "_sources")

    def __init__(self, *, core: bool = True) -> None:
        self._types: dict[str, DataType] = {}
        self._nodes: dict[str, type[Node]] = {}
        self._conversions: dict[tuple[str, str], Converter | None] = {}
        self._plugins: dict[str, ModuleType] = {}
        self._sources: dict[str, str] = {}

        if core:
            for data_type in builtin_types:
                self.register_type(data_type)

            for source, target, function in builtin_conversions:
                self.register_conversion(source, target, function)

            from bolt.core import subgraph

            self.register_module(subgraph)

    def register_type(self, data_type: DataType, *, replace: bool = False) -> DataType:
        if not replace and data_type.name in self._types and self._types[data_type.name] is not data_type:
            raise RegistryError(f"data type '{data_type.name}' is already registered")

        self._types[data_type.name] = data_type

        return data_type

    def data_type(self, reference: str | DataType) -> DataType:
        if isinstance(reference, DataType):
            return self._types.get(reference.name, reference)

        data_type = self._types.get(reference)

        if data_type is None:
            raise UnknownTypeError(f"unknown data type '{reference}'")

        return data_type

    def data_types(self) -> list[DataType]:
        return list(self._types.values())

    def register_conversion(self, source: str, target: str, function: Converter | None) -> None:
        self._conversions[(source, target)] = function

    def converter(self, source: DataType | None, target: DataType | None) -> Converter | None | Literal[False]:
        """None when values pass through unchanged, a callable when they need converting, False when incompatible."""
        if source is None or target is None or source is target or target.name == "any" or source.name == "any":
            return None

        if source.name == target.name:
            return None

        key = (source.name, target.name)

        if key in self._conversions:
            return self._conversions[key]

        return False

    def register_node(self, node_class: NodeClass, *, replace: bool = False) -> NodeClass:
        if not (isinstance(node_class, type) and issubclass(node_class, Node)):
            raise RegistryError(f"{node_class!r} is not a Node subclass")

        type_name = node_class.type_name

        if not type_name:
            raise RegistryError(f"{node_class.__name__} has no type_name")

        existing = self._nodes.get(type_name)

        if existing is not None and existing is not node_class and not replace:
            raise RegistryError(f"node type '{type_name}' is already registered by {existing.__module__}.{existing.__name__}")

        self._nodes[type_name] = node_class

        return node_class

    def unregister_node(self, type_name: str) -> None:
        self._nodes.pop(type_name, None)

    def node_class(self, type_name: str) -> type[Node]:
        node_class = self._nodes.get(type_name)

        if node_class is None:
            raise UnknownNodeTypeError(f"unknown node type '{type_name}'")

        return node_class

    def has_node_type(self, type_name: str) -> bool:
        return type_name in self._nodes

    def node_classes(self) -> list[type[Node]]:
        return list(self._nodes.values())

    def create_node(self, type_name: str, name: str | None = None) -> Node:
        return self.node_class(type_name)(name)

    def register_module(self, module: ModuleType) -> None:
        """Register every Node subclass with a type_name and every DataType defined at the top level of a module."""
        for value in vars(module).values():
            if isinstance(value, DataType):
                self.register_type(value)

        for value in vars(module).values():
            if isinstance(value, type) and issubclass(value, Node) and value.type_name and value.__module__ == module.__name__:
                self.register_node(value)

    @property
    def plugins(self) -> list[str]:
        return list(self._plugins)

    def plugin_modules(self) -> list[ModuleType]:
        return list(self._plugins.values())

    def plugin_sources(self) -> list[str]:
        """Module names or paths that reload the same plugins with load_plugin, e.g. in a child process."""
        return list(self._sources.values())

    def load_plugin(self, plugin: str | os.PathLike[str] | ModuleType) -> ModuleType:
        """Load a plugin given as a module, an importable module name, a .py file or a package directory."""
        if isinstance(plugin, ModuleType):
            module = plugin
            source = _module_source(module)
        elif isinstance(plugin, os.PathLike) or os.path.exists(plugin):
            module = self._import_path(Path(plugin))
            source = str(Path(plugin).resolve())
        else:
            source = plugin

            try:
                module = importlib.import_module(plugin)
            except Exception as error:
                raise PluginError(f"cannot import plugin '{plugin}': {error}") from error

        if module.__name__ in self._plugins:
            return module

        try:
            register = getattr(module, "register", None)

            if callable(register):
                register(self)
            else:
                self.register_module(module)
        except Exception as error:
            raise PluginError(f"plugin '{module.__name__}' failed to register: {error}") from error

        self._plugins[module.__name__] = module
        self._sources[module.__name__] = source

        logger.debug("loaded plugin %s", module.__name__)

        return module

    def load_plugins_from_directory(self, directory: str | os.PathLike[str]) -> list[PluginError]:
        directory = Path(directory)

        if directory.is_file():
            return self._load_all([directory])

        if not directory.is_dir():
            return [PluginError(f"plugin directory '{directory}' does not exist")]

        entries = sorted(entry for entry in directory.iterdir()
                         if not entry.name.startswith(("_", "."))
                         and ((entry.is_file() and entry.suffix == ".py")
                              or (entry.is_dir() and (entry / "__init__.py").is_file())))

        return self._load_all(entries)

    def load_entry_points(self, group: str = default_entry_point_group) -> list[PluginError]:
        errors: list[PluginError] = []

        for entry_point in importlib.metadata.entry_points(group=group):
            try:
                self.load_plugin(entry_point.load())
            except Exception as error:
                errors.append(error if isinstance(error, PluginError)
                              else PluginError(f"entry point '{entry_point.name}' failed: {error}"))

        return errors

    def discover_plugins(self,
                         paths: Iterable[str | os.PathLike[str]] = (),
                         *,
                         environment_variable: str | None = default_plugin_path_variable,
                         entry_point_group: str | None = default_entry_point_group) -> list[PluginError]:
        """Load plugins from entry points, from the directories listed in an environment variable and from paths.
        Failures are logged and returned instead of raised so one broken plugin does not take the application down."""
        errors: list[PluginError] = []

        if entry_point_group:
            errors.extend(self.load_entry_points(entry_point_group))

        directories: list[str | os.PathLike[str]] = []

        if environment_variable:
            directories.extend(path for path in os.environ.get(environment_variable, "").split(os.pathsep) if path)

        directories.extend(paths)

        for directory in directories:
            errors.extend(self.load_plugins_from_directory(directory))

        for error in errors:
            logger.error("%s", error)

        return errors

    def _load_all(self, paths: Iterable[Path]) -> list[PluginError]:
        errors: list[PluginError] = []

        for path in paths:
            try:
                self.load_plugin(path)
            except PluginError as error:
                errors.append(error)

        return errors

    @staticmethod
    def _import_path(path: Path) -> ModuleType:
        path = path.resolve()

        if path.is_dir():
            location = path / "__init__.py"
            search_locations = [str(path)]
        else:
            location = path
            search_locations = None

        module_name = f"bolt_plugin_{path.stem if path.is_file() else path.name}"

        existing = sys.modules.get(module_name)

        if existing is not None and getattr(existing, "__file__", None) == str(location):
            return existing

        spec = importlib.util.spec_from_file_location(module_name, location, submodule_search_locations=search_locations)

        if spec is None or spec.loader is None:
            raise PluginError(f"cannot load plugin from '{path}'")

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module

        try:
            spec.loader.exec_module(module)
        except Exception as error:
            del sys.modules[module_name]
            raise PluginError(f"plugin '{path}' failed to import: {error}") from error

        return module


def _module_source(module: ModuleType) -> str:
    if not module.__name__.startswith("bolt_plugin_") or not getattr(module, "__file__", None):
        return module.__name__

    path = Path(module.__file__)

    return str(path.parent if path.name == "__init__.py" else path)
