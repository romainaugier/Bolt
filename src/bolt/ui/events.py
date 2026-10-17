from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from bolt.core.events import Event

if TYPE_CHECKING:
    from bolt.core.graph import Graph
    from bolt.core.node import Node
    from bolt.ui.workspace import Document


@dataclass(frozen=True, slots=True, eq=False)
class DocumentEvent(Event):
    document: Document


@dataclass(frozen=True, slots=True, eq=False)
class DocumentOpened(DocumentEvent):
    pass


@dataclass(frozen=True, slots=True, eq=False)
class DocumentClosed(DocumentEvent):
    pass


@dataclass(frozen=True, slots=True, eq=False)
class DocumentStateChanged(DocumentEvent):
    pass


@dataclass(frozen=True, slots=True, eq=False)
class CurrentDocumentChanged(Event):
    document: Document | None


@dataclass(frozen=True, slots=True, eq=False)
class CurrentGraphChanged(DocumentEvent):
    graph: Graph


@dataclass(frozen=True, slots=True, eq=False)
class SelectionChanged(DocumentEvent):
    nodes: tuple[Node, ...]


@dataclass(frozen=True, slots=True, eq=False)
class NodeCreationRequested(Event):
    type_name: str
    position: Any = None
