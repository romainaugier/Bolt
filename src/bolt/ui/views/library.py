from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QMimeData, Qt
from PySide6.QtGui import QDrag
from PySide6.QtWidgets import QLineEdit, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

from bolt.ui import icons, theme
from bolt.ui.events import NodeCreationRequested
from bolt.ui.views.base import View
from bolt.ui.views.node_editor import node_type_mime

if TYPE_CHECKING:
    from bolt.ui.workspace import Workspace


class _NodeTree(QTreeWidget):
    def startDrag(self, actions: Qt.DropActions) -> None:
        item = self.currentItem()
        type_name = item.data(0, Qt.UserRole) if item is not None else None

        if not type_name:
            return

        mime = QMimeData()
        mime.setData(node_type_mime, type_name.encode())
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec(Qt.CopyAction)


class NodeLibraryView(View):
    view_type = "node_library"
    label = "Node library"
    description = "Browse the node types; double-click or drag one into a node editor."

    def __init__(self, workspace: Workspace, parent: QWidget | None = None) -> None:
        super().__init__(workspace, parent)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Filter…")
        self.search.setClearButtonEnabled(True)
        self.tree = _NodeTree()
        self.tree.setHeaderHidden(True)
        self.tree.setDragEnabled(True)
        self.tree.itemActivated.connect(self._activated)
        self.search.textChanged.connect(self.refresh)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addWidget(self.search)
        layout.addWidget(self.tree)
        theme.notifier().changed.connect(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        words = self.search.text().lower().split()
        self.tree.clear()
        categories: dict[str, QTreeWidgetItem] = {}

        for node_class in sorted(self.workspace.registry.node_classes(), key=lambda cls: (cls.category, cls.type_name)):
            if node_class.type_name.startswith("bolt.graph_"):
                continue

            haystack = f"{node_class.type_name} {node_class.category} {node_class.description}".lower()

            if not all(word in haystack for word in words):
                continue

            category = node_class.category or "Other"
            parent = categories.get(category)

            if parent is None:
                parent = QTreeWidgetItem([category])
                parent.setFlags(parent.flags() & ~Qt.ItemIsDragEnabled)
                self.tree.addTopLevelItem(parent)
                categories[category] = parent

            item = QTreeWidgetItem([node_class.type_name])
            item.setData(0, Qt.UserRole, node_class.type_name)
            item.setToolTip(0, node_class.description)
            icon_name = node_class.ui.get("icon")

            if icon_name and icons.library.path(icon_name):
                item.setIcon(0, icons.library.icon(icon_name, theme.text))

            parent.addChild(item)

        self.tree.expandAll()

    def save_state(self) -> dict[str, str]:
        return {"filter": self.search.text()}

    def restore_state(self, state: dict[str, str]) -> None:
        self.search.setText(state.get("filter", ""))

    def _activated(self, item: QTreeWidgetItem) -> None:
        type_name = item.data(0, Qt.UserRole)

        if type_name:
            self.workspace.events.dispatch(NodeCreationRequested(type_name))
