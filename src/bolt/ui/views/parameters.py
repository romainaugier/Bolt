from __future__ import annotations

from typing import TYPE_CHECKING, Any

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFormLayout, QFrame, QGridLayout, QHBoxLayout, QLabel,
                               QLineEdit, QScrollArea, QToolButton, QVBoxLayout, QWidget)

from bolt.core import events
from bolt.core.node import Node, NodeState
from bolt.core.plugs import Input, Output, Parameter, Plug, PlugKind
from bolt.ui.commands import AddUserPlug, RemoveUserPlug, RenameNode, SetFlag, SetPlugKind, SetValue
from bolt.ui.events import CurrentDocumentChanged, CurrentGraphChanged, SelectionChanged
from bolt.ui.icons import bind_icon
from bolt.ui.parameters import ParameterEditor
from bolt.ui.views.base import View

if TYPE_CHECKING:
    from bolt.ui.workspace import Workspace

spec_classes = {"input": Input, "output": Output, "parameter": Parameter}


class ParametersView(View):
    view_type = "parameters"
    label = "Parameters"
    description = "Edit the values, flags and plugs of the selected node."

    def __init__(self, workspace: Workspace, parent: QWidget | None = None) -> None:
        super().__init__(workspace, parent)
        self.node: Node | None = None
        self.editors: dict[str, tuple[ParameterEditor | None, bool]] = {}
        self.flag_boxes: dict[str, QCheckBox] = {}
        self.kind_buttons: dict[str, QToolButton] = {}
        self.status: QLabel | None = None
        self.error: QLabel | None = None
        self._rebuild_pending = False
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.scroll)

        self.subscribe(SelectionChanged, lambda event: self._follow_selection())
        self.subscribe(CurrentDocumentChanged, lambda event: self._follow_selection())
        self.subscribe(CurrentGraphChanged, lambda event: self._follow_selection())
        self.subscribe(events.GraphEvent, self._on_graph_event)
        self._follow_selection()
        self.schedule_rebuild()

    def show_node(self, node: Node | None) -> None:
        self.node = node
        self.schedule_rebuild()

    def schedule_rebuild(self) -> None:
        """Rebuild the widgets once control returns to the event loop.

        Edits made through these widgets trigger rebuilds, and Qt crashes if a widget is destroyed while it is
        still emitting the signal that caused the rebuild, so a rebuild never happens synchronously."""
        if not self._rebuild_pending:
            self._rebuild_pending = True
            QTimer.singleShot(0, self, self._rebuild)

    def _rebuild(self) -> None:
        self._rebuild_pending = False

        node = self.node

        self.editors = {}
        self.flag_boxes = {}
        self.kind_buttons = {}

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        if node is None or node.graph is None:
            hint = QLabel("Select a node to edit it.")
            hint.setObjectName("muted")
            layout.addWidget(hint)
            layout.addStretch(1)

            self.status = self.error = None
            self._set_content(content)

            return

        layout.addLayout(self._header(node))

        self.status = QLabel()
        self.status.setObjectName("muted")

        layout.addWidget(self.status)

        self.error = QLabel()
        self.error.setObjectName("error")
        self.error.setWordWrap(True)
        self.error.setTextInteractionFlags(Qt.TextSelectableByMouse)

        layout.addWidget(self.error)

        self._update_status()

        for title, kind in (("Inputs", PlugKind.input), ("Parameters", PlugKind.parameter)):
            plugs = [plug for plug in node.plugs(kind)]

            if plugs:
                layout.addWidget(self._section(title))
                layout.addLayout(self._plug_grid(plugs))

        if type(node).user_plugs:
            layout.addWidget(self._section("Plugs"))
            layout.addLayout(self._user_plugs(node))

        layout.addStretch(1)

        self._set_content(content)

    def _set_content(self, content: QWidget) -> None:
        previous = self.scroll.takeWidget()

        self.scroll.setWidget(content)

        if previous is not None:
            previous.deleteLater()

    def _header(self, node: Node) -> QFormLayout:
        form = QFormLayout()
        name = QLineEdit(node.name)
        name.setObjectName("heading")
        name.editingFinished.connect(lambda: self._rename(name.text()))

        form.addRow(name)

        node_type = QLabel(f"{node.type_name or getattr(node, 'missing_type', '')}  ·  {type(node).category}")
        node_type.setObjectName("muted")

        form.addRow(node_type)

        if type(node).description:
            description = QLabel(type(node).description)
            description.setWordWrap(True)
            form.addRow(description)

        flags = QHBoxLayout()

        for flag, label in (("displayed", "Display"), ("disabled", "Disable")):
            box = QCheckBox(label)
            box.setChecked(getattr(node, flag))
            box.toggled.connect(lambda checked, flag=flag: self._set_flag(flag, checked))
            flags.addWidget(box)

            self.flag_boxes[flag] = box

        flags.addStretch(1)
        form.addRow(flags)

        return form

    @staticmethod
    def _section(title: str) -> QLabel:
        label = QLabel(title.upper())
        label.setObjectName("muted")

        return label

    def _plug_grid(self, plugs: list[Plug]) -> QGridLayout:
        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setColumnStretch(1, 1)

        field_height = QLineEdit().sizeHint().height()

        for row, plug in enumerate(plugs):
            label = QLabel(plug.spec.label)
            label.setMinimumHeight(field_height)
            label.setAlignment(Qt.AlignVCenter | Qt.AlignRight)

            promoted = f"\n(declared as an {plug.spec.kind.value})" if plug.promoted else ""

            label.setToolTip(f"{plug.name}: {plug.spec.type_name}{promoted}\n{plug.spec.description}".strip())

            grid.addWidget(label, row, 0, Qt.AlignTop | Qt.AlignRight)

            holder = QWidget()
            holder_layout = QHBoxLayout(holder)
            holder_layout.setContentsMargins(0, 0, 0, 0)

            grid.addWidget(holder, row, 1)

            self._add_kind_button(grid, row, plug)

            if plug.connections:
                sources = ", ".join(connection.source.path for connection in plug.connections)

                connected = QLabel(f"← {sources}")
                connected.setObjectName("muted")

                holder_layout.addWidget(connected)

                self.editors[plug.name] = (None, False)

                continue

            self._fill_editor(plug, holder_layout)

            toggle = QToolButton()
            toggle.setText("ƒ")
            toggle.setCheckable(True)
            toggle.setChecked(plug.is_expression)
            toggle.setToolTip("Use an expression: $(VARIABLE) or `python`")
            toggle.toggled.connect(lambda checked, plug=plug: self._toggle_expression(plug, checked))

            grid.addWidget(toggle, row, 2, Qt.AlignTop)

        return grid

    def _add_kind_button(self, grid: QGridLayout, row: int, plug: Plug) -> None:
        target = PlugKind.parameter if plug.kind is PlugKind.input else PlugKind.input

        if plug.kind_error(target) is not None:
            return

        button = QToolButton()

        if target is PlugKind.parameter:
            bind_icon(button, "tune")
            button.setToolTip("Make it a parameter: edit its value here instead of connecting it"
                              + (" (disconnects it)" if plug.connections else ""))
        else:
            bind_icon(button, "input")
            button.setToolTip("Make it an input: give it a plug on the node to connect it")

        button.clicked.connect(lambda checked=False, plug=plug, target=target: self.set_plug_kind(plug, target))
        grid.addWidget(button, row, 3, Qt.AlignTop)

        self.kind_buttons[plug.name] = button

    def set_plug_kind(self, plug: Plug, kind: PlugKind) -> None:
        document = self._document()

        if document is not None:
            document.push(SetPlugKind(document, plug, kind))

    def _fill_editor(self, plug: Plug, layout: QHBoxLayout) -> None:
        expression = plug.is_expression
        editor = self.workspace.parameter_widgets.create(plug, expression=expression)
        editor.set_value(plug.raw)
        editor.edited.connect(lambda value, plug=plug: self._edit(plug, value))
        layout.addWidget(editor)

        self.editors[plug.name] = (editor, expression)

    def _user_plugs(self, node: Node) -> QVBoxLayout:
        layout = QVBoxLayout()

        for plug in node.dynamic_plugs():
            row = QHBoxLayout()
            label = QLabel(f"{plug.spec.kind.value}  {plug.name}: {plug.spec.type_name}")
            row.addWidget(label, 1)
            remove = QToolButton()

            bind_icon(remove, "close", "muted")

            remove.setToolTip(f"Remove {plug.name}")
            remove.clicked.connect(lambda checked=False, name=plug.name: self._remove_plug(name))

            row.addWidget(remove)
            layout.addLayout(row)

        add_row = QHBoxLayout()

        kind = QComboBox()
        kinds = ("input", "output") if node.child_graphs() else ("input", "parameter", "output")
        kind.addItems(kinds)

        name = QLineEdit()
        name.setPlaceholderText("name")

        data_type = QComboBox()
        data_type.addItems(sorted(data_type.name for data_type in self.workspace.registry.data_types()))
        data_type.setCurrentText("any")

        add = QToolButton()

        bind_icon(add, "add")

        add.setToolTip("Add the plug")
        add.clicked.connect(lambda: self._add_plug(kind.currentText(), name.text(), data_type.currentText()))

        for widget in (kind, name, data_type, add):
            add_row.addWidget(widget)

        layout.addLayout(add_row)

        return layout

    def _update_status(self) -> None:
        node = self.node

        if node is None or self.status is None:
            return

        text = node.state.value

        if node.state is NodeState.cooked and node.cook_time is not None:
            text += f" in {node.cook_time * 1000:.1f} ms"

        self.status.setText(text)
        self.error.setVisible(node.state is NodeState.failed and bool(node.error))
        self.error.setText(node.error or "")

    def _follow_selection(self) -> None:
        document = self.workspace.current
        node = document.selection[-1] if document is not None and document.selection else None

        if node is not self.node:
            self.show_node(node)

    def _show_error(self, text: str) -> None:
        if self.error is not None:
            self.error.setText(text)
            self.error.setVisible(True)

    def _on_graph_event(self, event: events.GraphEvent) -> None:
        node = self.node

        if node is None:
            return

        if isinstance(event, events.NodeRemoved) and event.node is node:
            self.show_node(None)
        elif isinstance(event, events.ValueChanged) and event.plug.node is node:
            entry = self.editors.get(event.plug.name)

            if entry is None:
                return

            editor, expression = entry

            if editor is None or expression != event.plug.is_expression:
                self.schedule_rebuild()
            else:
                editor.set_value(event.plug.raw)

        elif isinstance(event, events.NodeChanged) and event.node is node:
            box = self.flag_boxes.get(event.attribute)

            if box is not None:
                box.blockSignals(True)
                box.setChecked(getattr(node, event.attribute))
                box.blockSignals(False)
        elif isinstance(event, (events.Connected, events.Disconnected)) and event.connection.target.node is node:
            self.schedule_rebuild()
        elif isinstance(event, (events.PlugAdded, events.PlugRemoved, events.PlugKindChanged, events.NodeRenamed)):
            affected = event.node if isinstance(event, (events.PlugRemoved, events.NodeRenamed)) else event.plug.node

            if affected is node:
                self.schedule_rebuild()
        elif isinstance(event, (events.NodeCookStarted, events.NodeCooked, events.NodeCookFailed,
                                events.NodeBlocked)) and event.node is node:
            self._update_status()

    def _document(self) -> Any:
        return self.workspace.document_of(self.node.graph) if self.node is not None else None

    def _edit(self, plug: Plug, value: Any) -> None:
        document = self._document()

        if document is not None:
            try:
                document.push(SetValue(document, plug, value))
            except Exception as error:
                self._show_error(str(error))

    def _toggle_expression(self, plug: Plug, checked: bool) -> None:
        if checked == plug.is_expression:
            return

        if checked:
            raw = plug.raw
            value = raw if isinstance(raw, str) and plug.data_type.string_like else f"`{raw!r}`"
        else:
            value = plug._default()

        self._edit(plug, value)

    def _rename(self, name: str) -> None:
        document = self._document()

        if document is None or name == self.node.name:
            return

        try:
            document.push(RenameNode(document, self.node, name))
        except Exception as error:
            self._show_error(str(error))

    def _set_flag(self, flag: str, value: bool) -> None:
        document = self._document()

        if document is not None and getattr(self.node, flag) != value:
            document.push(SetFlag(document, self.node, flag, value))

    def _add_plug(self, kind: str, name: str, data_type: str) -> None:
        document = self._document()

        if document is None or not name:
            return

        try:
            document.push(AddUserPlug(document, self.node, spec_classes[kind](name, data_type)))
        except Exception as error:
            self._show_error(str(error))

    def _remove_plug(self, name: str) -> None:
        document = self._document()

        if document is not None:
            document.push(RemoveUserPlug(document, self.node, name))
