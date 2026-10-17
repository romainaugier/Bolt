from __future__ import annotations

import json
import logging
import os
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from bolt.core.errors import BoltError, CookError, SerializationError
from bolt.core.events import EventBus
from bolt.core.graph import Graph
from bolt.core.node import Node
from bolt.core.plugs import Plug, PlugKind, PlugSpec

if TYPE_CHECKING:
    from bolt.core.evaluation import CookContext
    from bolt.core.registry import Registry

logger = logging.getLogger("bolt.serialization")

format_name = "bolt.graph"
format_version = 1


class MissingNode(Node):
    """Stands in for a node whose type is not registered, so loading and saving the graph keeps its data intact."""

    category = "Graph"

    def __init__(self, data: Mapping[str, Any]) -> None:
        super().__init__(data["name"])
        self.data = dict(data)
        self.missing_type: str = data["type"]

        for spec_data in data.get("plugs", ()):
            self.add_plug(PlugSpec.from_dict({**spec_data, "type": "any"}))

    def ensure_plug(self, name: str, kind: PlugKind) -> Plug:
        if self.has_plug(name):
            return self.plug(name)

        spec_class = {PlugKind.input: _input_spec, PlugKind.output: _output_spec}[kind]

        return self.add_plug(spec_class(name))

    def cook(self, ctx: CookContext) -> None:
        raise CookError(f"node type '{self.missing_type}' is not available, is its plugin loaded?")


def _input_spec(name: str) -> PlugSpec:
    from bolt.core.plugs import Input

    return Input(name, "any", multi=True)


def _output_spec(name: str) -> PlugSpec:
    from bolt.core.plugs import Output

    return Output(name, "any")


def _serialize_value(plug: Plug) -> Any:
    if plug.is_expression or plug.data_type is None:
        return plug.raw

    return plug.data_type.serialize(plug.raw)


def _deserialize_value(plug: Plug, value: Any) -> Any:
    if isinstance(value, str) and plug.data_type.needs_expansion(value):
        return value

    return plug.data_type.deserialize(value)


def node_to_dict(node: Node) -> dict[str, Any]:
    if isinstance(node, MissingNode):
        data = dict(node.data)
        data["name"] = node.name
        data["id"] = node.id
        data["disabled"] = node.disabled
        data["displayed"] = node.displayed
        data["metadata"] = node.metadata
        return data

    data: dict[str, Any] = {"id": node.id, "name": node.name, "type": node.type_name, "version": node.version}

    if node.disabled:
        data["disabled"] = True

    if node.displayed:
        data["displayed"] = True

    if node.metadata:
        data["metadata"] = node.metadata

    dynamic = [plug.spec.to_dict() for plug in node.dynamic_plugs()]

    if dynamic:
        data["plugs"] = dynamic

    values = {plug.name: _serialize_value(plug) for plug in node.plugs() if plug.kind is not PlugKind.output}

    if values:
        data["values"] = values

    kinds = {plug.name: plug.kind.value for plug in node.plugs() if plug.promoted}

    if kinds:
        data["kinds"] = kinds

    extra = node.save_extra()

    if extra:
        data["extra"] = extra

    return data


def graph_to_dict(graph: Graph) -> dict[str, Any]:
    data: dict[str, Any] = {"name": graph.name}

    if graph.variables:
        data["variables"] = dict(graph.variables)

    data["nodes"] = [node_to_dict(node) for node in graph]
    data["connections"] = [[connection.source.node.name, connection.source.name,
                            connection.target.node.name, connection.target.name]
                           for connection in graph.connections()]

    return data


def _restore_flags(node: Node, data: Mapping[str, Any]) -> None:
    node.disabled = data.get("disabled", False)
    node.displayed = data.get("displayed", False)
    node.metadata = dict(data.get("metadata", {}))


def node_from_dict(data: Mapping[str, Any], graph: Graph) -> Node:
    registry = graph.registry
    type_name = data["type"]

    if not registry.has_node_type(type_name):
        logger.warning("node type '%s' is not registered, keeping %s as a missing node", type_name, data["name"])
        node: Node = MissingNode(data)
        node.id = data.get("id", node.id)
        _restore_flags(node, data)
        graph.add_node(node, unique=False)

        return node

    node_class = registry.node_class(type_name)
    version = data.get("version", 1)

    if version < node_class.version:
        data = node_class.migrate(dict(data), version)
    elif version > node_class.version:
        logger.warning("%s was saved with version %d of '%s' but version %d is installed",
                       data["name"], version, type_name, node_class.version)

    node = node_class(data["name"])
    node.id = data.get("id", node.id)

    for spec_data in data.get("plugs", ()):
        node.add_plug(PlugSpec.from_dict(spec_data))

    _restore_flags(node, data)

    graph.add_node(node, unique=False)

    for name, value in data.get("values", {}).items():
        if not node.has_plug(name):
            logger.warning("%s has no plug '%s' anymore, its saved value is dropped", node.path, name)
            continue

        plug = node.plug(name)

        if plug.kind is PlugKind.output:
            continue

        try:
            plug.set(_deserialize_value(plug, value))
        except BoltError as error:
            logger.warning("%s: cannot restore saved value %r: %s", plug.path, value, error)

    for name, kind in data.get("kinds", {}).items():
        try:
            node.set_plug_kind(name, PlugKind(kind))
        except (BoltError, ValueError) as error:
            logger.warning("%s: cannot make plug '%s' an %s: %s", node.path, name, kind, error)

    extra = data.get("extra")

    if extra:
        node.load_extra(extra)

    return node


def graph_from_dict(data: Mapping[str, Any],
                    registry: Registry,
                    *,
                    owner: Node | None = None,
                    events: EventBus | None = None,
                    context: Any = None) -> Graph:
    graph = Graph(registry, name=data.get("name", "root"), events=events, owner=owner, context=context)

    for name, value in data.get("variables", {}).items():
        graph.set_variable(name, value)

    for node_data in data.get("nodes", ()):
        try:
            node_from_dict(node_data, graph)
        except BoltError as error:
            raise SerializationError(f"cannot load node {node_data.get('name')!r}: {error}") from error

    for source_node, source_plug, target_node, target_plug in data.get("connections", ()):
        try:
            source = _connection_plug(graph, source_node, source_plug, PlugKind.output)
            target = _connection_plug(graph, target_node, target_plug, PlugKind.input)
            graph.connect(source, target)
        except BoltError as error:
            logger.warning("cannot restore connection %s.%s -> %s.%s: %s",
                           source_node, source_plug, target_node, target_plug, error)

    return graph


def _connection_plug(graph: Graph, node_name: str, plug_name: str, kind: PlugKind) -> Plug:
    node = graph.node(node_name)

    if isinstance(node, MissingNode):
        return node.ensure_plug(plug_name, kind)

    return node.plug(plug_name)


def dumps(graph: Graph, *, indent: int | None = 2) -> str:
    return json.dumps({"format": format_name, "version": format_version, "graph": graph_to_dict(graph)}, indent=indent)


def loads(text: str, registry: Registry, *, events: EventBus | None = None, context: Any = None) -> Graph:
    try:
        document = json.loads(text)
    except json.JSONDecodeError as error:
        raise SerializationError(f"invalid graph file: {error}") from error

    if not isinstance(document, dict) or document.get("format") != format_name:
        raise SerializationError("not a bolt graph file")

    version = document.get("version", 0)

    if version > format_version:
        raise SerializationError(f"graph file format version {version} is newer than the supported version {format_version}")

    return graph_from_dict(document["graph"], registry, events=events, context=context)


def save_graph(graph: Graph, path: str | os.PathLike[str]) -> None:
    path = os.fspath(path)
    directory = os.path.dirname(path)

    if directory:
        os.makedirs(directory, exist_ok=True)

    temporary = f"{path}.tmp"

    with open(temporary, "w", encoding="utf-8") as file:
        file.write(dumps(graph))
        file.write("\n")

    os.replace(temporary, path)


def load_graph(path: str | os.PathLike[str],
               registry: Registry,
               *,
               events: EventBus | None = None,
               context: Any = None) -> Graph:
    with open(path, encoding="utf-8") as file:
        return loads(file.read(), registry, events=events, context=context)
