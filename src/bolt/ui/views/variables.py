from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (QHBoxLayout, QHeaderView, QLabel, QPushButton, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)

from bolt.core import events
from bolt.ui.commands import SetVariable
from bolt.ui.events import CurrentDocumentChanged, CurrentGraphChanged
from bolt.ui.views.base import View

if TYPE_CHECKING:
    from bolt.ui.workspace import Workspace


def parse(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def show(value: Any) -> str:
    return value if isinstance(value, str) else json.dumps(value, default=repr)


class _VariableTable(QWidget):
    def __init__(self, title: str, on_set: Any, on_remove: Any) -> None:
        super().__init__()

        self.on_set = on_set
        self.on_remove = on_remove
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Name", "Value"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.verticalHeader().hide()
        self.table.itemChanged.connect(self._changed)

        add = QPushButton("Add")
        add.clicked.connect(self._add)

        remove = QPushButton("Remove")
        remove.clicked.connect(self._remove)

        title_label = QLabel(title.upper())
        title_label.setObjectName("muted")

        bar = QHBoxLayout()
        bar.addWidget(title_label)
        bar.addStretch(1)
        bar.addWidget(add)
        bar.addWidget(remove)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(bar)
        layout.addWidget(self.table)

        self._names: list[str] = []

    def set_variables(self, variables: dict[str, Any]) -> None:
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        self._names = list(variables)

        for row, (name, value) in enumerate(variables.items()):
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(name))
            self.table.setItem(row, 1, QTableWidgetItem(show(value)))

        self.table.blockSignals(False)

    def _changed(self, item: QTableWidgetItem) -> None:
        row = item.row()

        name_item = self.table.item(row, 0)

        value_item = self.table.item(row, 1)

        if name_item is None or not name_item.text():
            return

        old_name = self._names[row] if row < len(self._names) else None

        if old_name and old_name != name_item.text():
            self.on_remove(old_name)

        self.on_set(name_item.text(), parse(value_item.text() if value_item else ""))

    def _add(self) -> None:
        existing = set(self._names)
        index = 1

        while f"VARIABLE{index}" in existing:
            index += 1

        self.on_set(f"VARIABLE{index}", "")

    def _remove(self) -> None:
        row = self.table.currentRow()

        if 0 <= row < len(self._names):
            self.on_remove(self._names[row])


class VariablesView(View):
    view_type = "variables"
    label = "Variables"
    description = "Variables of the current graph, and the evaluation variables of live cooking (e.g. FRAME)."

    def __init__(self, workspace: Workspace, parent: QWidget | None = None) -> None:
        super().__init__(workspace, parent)
        self.graph_table = _VariableTable("Graph variables", self._set_graph, self._remove_graph)
        self.live_table = _VariableTable("Live cook variables", self._set_live, self._remove_live)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addWidget(self.graph_table)
        layout.addWidget(self.live_table)

        self._refresh_pending = False
        self.subscribe(CurrentDocumentChanged, lambda event: self.refresh())
        self.subscribe(CurrentGraphChanged, lambda event: self.refresh())
        self.subscribe(events.VariableChanged, lambda event: self.refresh())
        self._refresh_now()

    def refresh(self) -> None:
        """Rebuild the tables once control returns to the event loop: the edit that triggers a refresh comes from a
        table item, which must not be destroyed while Qt is still handling it."""
        if not self._refresh_pending:
            self._refresh_pending = True
            QTimer.singleShot(0, self, self._refresh_now)

    def _refresh_now(self) -> None:
        self._refresh_pending = False

        document = self.workspace.current

        self.setEnabled(document is not None)

        if document is None:
            self.graph_table.set_variables({})
            self.live_table.set_variables({})
            return

        self.graph_table.set_variables(dict(document.current_graph.variables))
        self.live_table.set_variables(dict(document.live.variables))

    def _set_graph(self, name: str, value: Any) -> None:
        document = self.workspace.current

        if document is not None:
            document.push(SetVariable(document, document.current_graph, name, value))

    def _remove_graph(self, name: str) -> None:
        document = self.workspace.current

        if document is not None:
            document.push(SetVariable(document, document.current_graph, name, None, remove=True))

    def _set_live(self, name: str, value: Any) -> None:
        document = self.workspace.current

        if document is not None:
            document.live.set_variables({**document.live.variables, name: value})

            self.refresh()

    def _remove_live(self, name: str) -> None:
        document = self.workspace.current

        if document is not None:
            variables = dict(document.live.variables)
            variables.pop(name, None)

            document.live.set_variables(variables)

            self.refresh()
