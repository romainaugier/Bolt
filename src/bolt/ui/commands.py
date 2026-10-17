from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from typing import TYPE_CHECKING, Any

from PySide6.QtGui import QUndoCommand

from bolt.core import events
from bolt.core.graph import Graph
from bolt.core.node import Node
from bolt.core.plugs import Plug, PlugKind, PlugSpec
from bolt.core.serialization import node_from_dict, node_to_dict

if TYPE_CHECKING:
    from bolt.ui.workspace import Document

GraphRef = tuple[str, ...]
ConnectionRef = tuple[str, str, str, str]

_merge_ids = {"set_value": 1, "move": 2}


def graph_ref(graph: Graph) -> GraphRef:
    names: list[str] = []

    while graph.owner is not None:
        names.append(graph.owner.name)
        graph = graph.owner.graph

    return tuple(reversed(names))


def resolve_graph(root: Graph, ref: GraphRef) -> Graph:
    graph = root

    for name in ref:
        graph = graph.node(name).child_graphs()[0]

    return graph


def internal_connections(nodes: Iterable[Node]) -> list[ConnectionRef]:
    """Connections between the given nodes, in input order, as (source node, source plug, target node, target plug)."""
    nodes = list(nodes)
    members = set(nodes)

    return [(connection.source.node.name, connection.source.name, node.name, plug.name)
            for node in nodes
            for plug in node.input_plugs()
            for connection in plug.connections
            if connection.source.node in members]


class DocumentCommand(QUndoCommand):
    structural = True

    def __init__(self, document: Document, text: str, graph: Graph | None = None) -> None:
        super().__init__(text)
        self.document = document
        self.graph_ref = graph_ref(graph) if graph is not None else ()

    @property
    def graph(self) -> Graph:
        return resolve_graph(self.document.graph, self.graph_ref)

    def redo(self) -> None:
        self._run(self.apply)

    def undo(self) -> None:
        self._run(self.revert)

    def apply(self) -> None:
        raise NotImplementedError

    def revert(self) -> None:
        raise NotImplementedError

    def _run(self, function: Callable[[], None]) -> None:
        if self.structural:
            self.document.live.edit(function)
        else:
            function()


class InsertNodes(DocumentCommand):
    """Add nodes from serialized data plus the connections between them; also used to paste and to undo deletions."""

    def __init__(self,
                 document: Document,
                 graph: Graph,
                 nodes: Sequence[Mapping[str, Any]],
                 connections: Sequence[ConnectionRef] = (),
                 text: str = "Add nodes",
                 rename: bool = True) -> None:
        super().__init__(document, text, graph)

        datas = [dict(data) for data in nodes]

        if rename:
            taken = {node.name for node in graph}
            renamed: dict[str, str] = {}

            for data in datas:
                name = data["name"]

                if name in taken:
                    root = name.rstrip("0123456789").rstrip("_") or name
                    index = 1

                    while f"{root}_{index}" in taken:
                        index += 1
                    name = f"{root}_{index}"

                renamed[data["name"]] = name
                taken.add(name)
                data["name"] = name
                data.pop("id", None)

            connections = [(renamed.get(a, a), b, renamed.get(c, c), d) for a, b, c, d in connections]

        self.datas = datas
        self.connections = list(connections)

    @property
    def names(self) -> list[str]:
        return [data["name"] for data in self.datas]

    def apply(self) -> None:
        graph = self.graph

        for data in self.datas:
            node_from_dict(data, graph)

        for source_node, source_plug, target_node, target_plug in self.connections:
            graph.connect(f"{source_node}.{source_plug}", f"{target_node}.{target_plug}")

    def revert(self) -> None:
        graph = self.graph

        for name in self.names:
            graph.remove_node(name)


def create_node_command(document: Document,
                        graph: Graph,
                        type_name: str,
                        position: tuple[float, float] | None = None,
                        values: Mapping[str, Any] | None = None,
                        name: str | None = None) -> InsertNodes:
    node_class = graph.registry.node_class(type_name)

    data: dict[str, Any] = {"name": graph.unique_name(name or node_class.default_name()), "type": type_name,
                            "version": node_class.version}

    if position is not None:
        data["metadata"] = {"position": [float(position[0]), float(position[1])]}

    if values:
        data["values"] = dict(values)

    return InsertNodes(document, graph, [data], text=f"Create {type_name}", rename=False)


class RemoveNodes(DocumentCommand):
    def __init__(self, document: Document, graph: Graph, nodes: Iterable[Node]) -> None:
        nodes = [node for node in nodes if node.removable]

        super().__init__(document, f"Delete {len(nodes)} node(s)", graph)

        self.datas = [node_to_dict(node) for node in nodes]
        self.connections = self._all_connections(nodes)

    @staticmethod
    def _all_connections(nodes: Sequence[Node]) -> list[tuple[str, str, list[tuple[str, str]]]]:
        targets: dict[tuple[str, str], list[tuple[str, str]]] = {}
        names = {node.name for node in nodes}

        for node in nodes:
            for plug in node.plugs():
                for connection in plug.connections:
                    target = connection.target
                    key = (target.node.name, target.name)

                    if key not in targets:
                        targets[key] = [(c.source.node.name, c.source.name) for c in target.connections]

        return [(node, plug, sources) for (node, plug), sources in targets.items()
                if node in names or any(source in names for source, _ in sources)]

    def apply(self) -> None:
        graph = self.graph

        for data in self.datas:
            graph.remove_node(data["name"])

    def revert(self) -> None:
        graph = self.graph

        for data in self.datas:
            node_from_dict(data, graph)

        for target_node, target_plug, sources in self.connections:
            target = graph.node(target_node).plug(target_plug)
            graph.disconnect_plug(target)

            for source_node, source_plug in sources:
                graph.connect(f"{source_node}.{source_plug}", target)


class SetConnections(DocumentCommand):
    """Replace the ordered list of sources of an input. Connecting, disconnecting and reordering all use it."""

    def __init__(self,
                 document: Document,
                 target: Plug,
                 sources: Sequence[tuple[str, str]],
                 text: str = "Connect") -> None:
        super().__init__(document, text, target.node.graph)

        self.target = (target.node.name, target.name)
        self.before = [(c.source.node.name, c.source.name) for c in target.connections]
        self.after = list(sources)

    def apply(self) -> None:
        self._set(self.after)

    def revert(self) -> None:
        self._set(self.before)

    def _set(self, sources: Sequence[tuple[str, str]]) -> None:
        graph = self.graph
        target = graph.node(self.target[0]).plug(self.target[1])
        graph.disconnect_plug(target)

        for node, plug in sources:
            graph.connect(f"{node}.{plug}", target)


def connect_command(document: Document, source: Plug, target: Plug) -> SetConnections:
    current = [(c.source.node.name, c.source.name) for c in target.connections]
    added = (source.node.name, source.name)
    sources = [*current, added] if target.spec.multi else [added]

    return SetConnections(document, target, sources, f"Connect {source.path} to {target.path}")


def disconnect_command(document: Document, source: Plug, target: Plug) -> SetConnections:
    removed = (source.node.name, source.name)
    sources = [ref for ref in ((c.source.node.name, c.source.name) for c in target.connections) if ref != removed]

    return SetConnections(document, target, sources, f"Disconnect {source.path} from {target.path}")


class SetPlugKind(DocumentCommand):
    """Make an input a parameter (disconnecting it) or a parameter an input; undo restores the connections."""

    def __init__(self, document: Document, plug: Plug, kind: PlugKind) -> None:
        verb = "Make" if kind is PlugKind.parameter else "Promote"

        super().__init__(document, f"{verb} {plug.path} {'a parameter' if kind is PlugKind.parameter else 'an input'}",
                         plug.node.graph)

        self.plug_ref = (plug.node.name, plug.name)
        self.before = plug.kind
        self.after = kind
        self.sources = [(c.source.node.name, c.source.name) for c in plug.connections]

    def apply(self) -> None:
        node = self.graph.node(self.plug_ref[0])

        self.graph.disconnect_plug(node.plug(self.plug_ref[1]))

        node.set_plug_kind(self.plug_ref[1], self.after)

    def revert(self) -> None:
        graph = self.graph
        node = graph.node(self.plug_ref[0])
        plug = node.set_plug_kind(self.plug_ref[1], self.before)

        for source_node, source_plug in self.sources:
            graph.connect(f"{source_node}.{source_plug}", plug)


class SetValue(DocumentCommand):
    structural = False

    def __init__(self, document: Document, plug: Plug, value: Any) -> None:
        super().__init__(document, f"Set {plug.path}", plug.node.graph)

        self.plug_ref = (plug.node.name, plug.name)
        self.before = plug.raw
        self.after = value

    def id(self) -> int:
        return _merge_ids["set_value"]

    def mergeWith(self, other: QUndoCommand) -> bool:
        if not isinstance(other, SetValue) or other.plug_ref != self.plug_ref or other.graph_ref != self.graph_ref:
            return False

        if isinstance(self.after, str) or type(other.after) is not type(self.after):
            return False

        self.after = other.after

        return True

    def apply(self) -> None:
        self._plug().set(self.after)

    def revert(self) -> None:
        self._plug().set(self.before)

    def _plug(self) -> Plug:
        return self.graph.node(self.plug_ref[0]).plug(self.plug_ref[1])


class RenameNode(DocumentCommand):
    def __init__(self, document: Document, node: Node, name: str) -> None:
        super().__init__(document, f"Rename {node.name} to {name}", node.graph)

        self.before = node.name
        self.after = name

    def apply(self) -> None:
        self.graph.rename_node(self.before, self.after)

    def revert(self) -> None:
        self.graph.rename_node(self.after, self.before)


class SetFlag(DocumentCommand):
    structural = False

    def __init__(self, document: Document, node: Node, flag: str, value: bool) -> None:
        super().__init__(document, f"{'Set' if value else 'Clear'} {flag} on {node.name}", node.graph)

        if flag not in ("disabled", "displayed"):
            raise ValueError(f"unknown flag {flag!r}")

        self.node_name = node.name
        self.flag = flag
        self.before = getattr(node, flag)
        self.after = value

    def apply(self) -> None:
        setattr(self.graph.node(self.node_name), self.flag, self.after)

    def revert(self) -> None:
        setattr(self.graph.node(self.node_name), self.flag, self.before)


class MoveNodes(DocumentCommand):
    structural = False

    def __init__(self, document: Document, graph: Graph,
                 moves: Mapping[str, tuple[tuple[float, float], tuple[float, float]]], text: str = "") -> None:
        super().__init__(document, text or f"Move {len(moves)} node(s)", graph)

        self.moves = dict(moves)

    def apply(self) -> None:
        self._place(1)

    def revert(self) -> None:
        self._place(0)

    def _place(self, index: int) -> None:
        graph = self.graph

        for name, positions in self.moves.items():
            node = graph.find_node(name)

            if node is None:
                continue

            node.metadata["position"] = list(positions[index])
            graph.events.emit(events.NodeChanged, graph, node, "position")


class AddUserPlug(DocumentCommand):
    def __init__(self, document: Document, node: Node, spec: PlugSpec) -> None:
        super().__init__(document, f"Add {spec.kind.value} {spec.name} to {node.name}", node.graph)

        self.node_name = node.name
        self.spec = spec.to_dict()

    def apply(self) -> None:
        self.graph.node(self.node_name).add_user_plug(PlugSpec.from_dict(self.spec))

    def revert(self) -> None:
        self.graph.node(self.node_name).remove_user_plug(self.spec["name"])


class RemoveUserPlug(DocumentCommand):
    def __init__(self, document: Document, node: Node, name: str) -> None:
        super().__init__(document, f"Remove {name} from {node.name}", node.graph)

        plug = node.plug(name)

        self.node_name = node.name
        self.spec = plug.spec.to_dict()
        self.raw = None if plug.spec.kind.value == "output" else plug.raw
        self.connections = [(c.source.node.name, c.source.name, c.target.node.name, c.target.name)
                            for c in plug.connections]

    def apply(self) -> None:
        self.graph.node(self.node_name).remove_user_plug(self.spec["name"])

    def revert(self) -> None:
        graph = self.graph
        node = graph.node(self.node_name)
        plug = node.add_user_plug(PlugSpec.from_dict(self.spec))

        if self.raw is not None:
            plug.set(self.raw)

        for source_node, source_plug, target_node, target_plug in self.connections:
            graph.connect(f"{source_node}.{source_plug}", f"{target_node}.{target_plug}")


class SetVariable(DocumentCommand):
    structural = False

    def __init__(self, document: Document, graph: Graph, name: str, value: Any, remove: bool = False) -> None:
        super().__init__(document, f"{'Remove' if remove else 'Set'} variable {name}", graph)

        self.name = name
        self.had_before = name in graph.variables
        self.before = graph.variables.get(name)
        self.after = value
        self.remove = remove

    def apply(self) -> None:
        if self.remove:
            self.graph.remove_variable(self.name)
        else:
            self.graph.set_variable(self.name, self.after)

    def revert(self) -> None:
        if self.had_before:
            self.graph.set_variable(self.name, self.before)
        else:
            self.graph.remove_variable(self.name)
