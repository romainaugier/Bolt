from __future__ import annotations

import os
from collections.abc import Iterable
from typing import Any

from PySide6.QtCore import QObject
from PySide6.QtGui import QUndoCommand, QUndoGroup, QUndoStack

from bolt.core import events as core_events
from bolt.core.events import EventBus
from bolt.core.graph import Graph
from bolt.core.jobs import Job, JobChanged, JobManager
from bolt.core.live import EditPolicy, LiveCooker, LiveMode
from bolt.core.node import Node
from bolt.core.registry import Registry
from bolt.core.serialization import load_graph, save_graph
from bolt.ui.events import (CurrentDocumentChanged, CurrentGraphChanged, DocumentClosed, DocumentOpened,
                            DocumentStateChanged, SelectionChanged)
from bolt.ui.parameters import ParameterWidgets
from bolt.ui.qt import Dispatcher, EventRelay

coalesced_graph_events = (core_events.EvaluationProgress, core_events.NodeProgress)


class Document:
    """One open graph: its file, undo history, live cooker and the subgraph currently shown."""

    def __init__(self, workspace: Workspace, graph: Graph, path: str | None = None) -> None:
        self.workspace = workspace
        self.graph = graph
        self.path = path
        self.current_graph = graph
        self.selection: tuple[Node, ...] = ()
        self.undo_stack = QUndoStack(workspace)
        self.undo_stack.cleanChanged.connect(self._state_changed)

        workspace.undo_group.addStack(self.undo_stack)

        self.live = LiveCooker(graph,
                               mode=workspace.live_mode,
                               policy=workspace.live_policy,
                               call_soon=workspace.dispatcher.call_soon)

        self.relay = EventRelay(graph.events, workspace.events, coalesce=coalesced_graph_events, parent=workspace)

    @property
    def name(self) -> str:
        if self.path:
            return os.path.splitext(os.path.basename(self.path))[0]

        return self.graph.name

    @property
    def modified(self) -> bool:
        return not self.undo_stack.isClean()

    def owns(self, graph: Graph | None) -> bool:
        return graph is not None and graph.root is self.graph

    def push(self, command: QUndoCommand) -> None:
        self.undo_stack.push(command)

    def save(self, path: str | None = None) -> None:
        path = path or self.path

        if not path:
            raise ValueError("the document has no file path yet")

        if not self.live.wait(30):
            raise RuntimeError("the graph is still cooking")

        save_graph(self.graph, path)

        self.path = path
        self.undo_stack.setClean()
        self._state_changed()

    def close(self) -> None:
        self.live.close()
        self.relay.close()
        self.workspace.undo_group.removeStack(self.undo_stack)

    def _state_changed(self, *args: Any) -> None:
        self.workspace.events.dispatch(DocumentStateChanged(self))


class Workspace(QObject):
    """Everything the views share: the registry, open documents, the current selection, jobs and the event bus.

    Every event views care about arrives on `events`, on the GUI thread: graph events of all open documents
    (filter them with document.owns(event.graph)), job events and the workspace's own events."""

    def __init__(self,
                 registry: Registry,
                 *,
                 context: Any = None,
                 jobs: JobManager | None = None,
                 live_mode: LiveMode = LiveMode.auto,
                 live_policy: EditPolicy = EditPolicy.restart,
                 parent: QObject | None = None) -> None:
        super().__init__(parent)

        self.registry = registry
        self.context = context
        self.events = EventBus()
        self.dispatcher = Dispatcher(self)
        self.undo_group = QUndoGroup(self)
        self.live_mode = live_mode
        self.live_policy = live_policy
        self.jobs = jobs if jobs is not None else JobManager(registry)
        self.job_relay = EventRelay(self.jobs.events, self.events, coalesce=(JobChanged,), parent=self)
        self.documents: list[Document] = []
        self.current: Document | None = None
        self.parameter_widgets = ParameterWidgets()
        self.active_node_editor: Any = None

    def new_document(self, name: str = "untitled") -> Document:
        return self.add_document(Graph(self.registry, name=name, context=self.context))

    def open(self, path: str) -> Document:
        path = os.path.abspath(path)

        for document in self.documents:
            if document.path == path:
                self.set_current(document)
                return document

        return self.add_document(load_graph(path, self.registry, context=self.context), path)

    def add_document(self, graph: Graph, path: str | None = None) -> Document:
        if graph.context is None and self.context is not None:
            graph.context = self.context

        document = Document(self, graph, path)

        self.documents.append(document)
        self.events.dispatch(DocumentOpened(document))
        self.set_current(document)

        return document

    def close_document(self, document: Document) -> None:
        if document not in self.documents:
            return

        index = self.documents.index(document)

        self.documents.remove(document)

        document.close()

        self.events.dispatch(DocumentClosed(document))

        if self.current is document:
            self.set_current(self.documents[min(index, len(self.documents) - 1)] if self.documents else None)

    def set_current(self, document: Document | None) -> None:
        if document is self.current:
            return

        self.current = document
        self.undo_group.setActiveStack(document.undo_stack if document is not None else None)
        self.events.dispatch(CurrentDocumentChanged(document))

    def document_of(self, graph: Graph) -> Document | None:
        for document in self.documents:
            if document.owns(graph):
                return document

        return None

    def set_current_graph(self, graph: Graph) -> None:
        document = self.document_of(graph)

        if document is None:
            return

        if document is not self.current:
            self.set_current(document)

        if document.current_graph is not graph:
            document.current_graph = graph
            document.selection = ()

            self.events.dispatch(CurrentGraphChanged(document, graph))
            self.events.dispatch(SelectionChanged(document, ()))

    def select(self, nodes: Iterable[Node]) -> None:
        document = self.current

        if document is None:
            return

        selection = tuple(nodes)

        if selection == document.selection:
            return

        document.selection = selection

        self.events.dispatch(SelectionChanged(document, selection))

    def submit_job(self, document: Document | None = None) -> Job | None:
        document = document or self.current

        if document is None:
            return None

        targets = [node.name for node in document.graph.displayed_nodes()]

        return self.jobs.submit(document.graph, name=document.name, targets=targets,
                                variables=document.live.variables)

    def close(self) -> None:
        for document in list(self.documents):
            self.close_document(document)

        self.job_relay.close()
        self.jobs.cancel_all()
