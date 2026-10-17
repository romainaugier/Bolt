from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QHBoxLayout, QLineEdit,
                               QPlainTextEdit, QSpinBox, QToolButton, QWidget)

from bolt.core.plugs import Plug
from bolt.ui import theme


class ParameterEditor(QWidget):
    """Edits one raw plug value. Emits edited(value) when the user changes it."""

    edited = Signal(object)

    def __init__(self, plug: Plug, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.plug = plug
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(4)

    def set_value(self, value: Any) -> None:
        raise NotImplementedError

    def _emit(self, value: Any) -> None:
        self.edited.emit(value)


class LineEditor(ParameterEditor):
    def __init__(self, plug: Plug, parent: QWidget | None = None) -> None:
        super().__init__(plug, parent)

        self.field = QLineEdit()
        self.field.editingFinished.connect(self._finished)
        self._layout.addWidget(self.field)
        self._current = ""

    def set_value(self, value: Any) -> None:
        self._current = self.to_text(value)

        if self.field.text() != self._current:
            self.field.setText(self._current)

        expression = isinstance(value, str) and self.plug.data_type is not None and self.plug.data_type.needs_expansion(value)

        self.field.setProperty("expression", "true" if expression else "false")
        self.field.style().polish(self.field)

    def to_text(self, value: Any) -> str:
        return "" if value is None else str(value)

    def from_text(self, text: str) -> Any:
        return text

    def _finished(self) -> None:
        text = self.field.text()

        if text != self._current:
            self._current = text
            self._emit(self.from_text(text))


class JsonLineEditor(LineEditor):
    def to_text(self, value: Any) -> str:
        if isinstance(value, str):
            return value

        try:
            return json.dumps(value)
        except TypeError:
            return repr(value)

    def from_text(self, text: str) -> Any:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text


class PathEditor(LineEditor):
    def __init__(self, plug: Plug, parent: QWidget | None = None) -> None:
        super().__init__(plug, parent)

        browse = QToolButton()
        browse.setText("…")
        browse.setToolTip("Browse")
        browse.clicked.connect(self._browse)

        self._layout.addWidget(browse)

    def _browse(self) -> None:
        mode = self.plug.spec.ui.get("mode", self.plug.data_type.ui.get("mode", "file") if self.plug.data_type else "file")

        if mode == "directory":
            path = QFileDialog.getExistingDirectory(self, self.plug.spec.label, self.field.text())
        elif mode == "save":
            path, _ = QFileDialog.getSaveFileName(self, self.plug.spec.label, self.field.text())
        else:
            path, _ = QFileDialog.getOpenFileName(self, self.plug.spec.label, self.field.text())

        if path:
            self.field.setText(path)
            self._finished()


class BoolEditor(ParameterEditor):
    def __init__(self, plug: Plug, parent: QWidget | None = None) -> None:
        super().__init__(plug, parent)

        self.box = QCheckBox()
        self.box.toggled.connect(self._emit)
        self._layout.addWidget(self.box)
        self._layout.addStretch(1)

    def set_value(self, value: Any) -> None:
        self.box.blockSignals(True)
        self.box.setChecked(bool(value))
        self.box.blockSignals(False)


class NumberEditor(ParameterEditor):
    def __init__(self, plug: Plug, parent: QWidget | None = None, floating: bool = False) -> None:
        super().__init__(plug, parent)

        ui = plug.spec.ui

        if floating:
            self.box = QDoubleSpinBox()
            self.box.setDecimals(int(ui.get("decimals", 4)))
            self.box.setSingleStep(float(ui.get("step", 0.1)))
            self.box.setRange(float(ui.get("min", -1e12)), float(ui.get("max", 1e12)))
        else:
            self.box = QSpinBox()
            self.box.setSingleStep(int(ui.get("step", 1)))
            self.box.setRange(int(ui.get("min", -2_000_000_000)), int(ui.get("max", 2_000_000_000)))

        self.box.setKeyboardTracking(False)
        self.box.valueChanged.connect(self._emit)
        self._layout.addWidget(self.box, 1)

    def set_value(self, value: Any) -> None:
        self.box.blockSignals(True)

        try:
            self.box.setValue(value if value is not None else 0)
        except TypeError:
            pass

        self.box.blockSignals(False)


class ChoiceEditor(ParameterEditor):
    def __init__(self, plug: Plug, parent: QWidget | None = None) -> None:
        super().__init__(plug, parent)

        self.box = QComboBox()

        for choice in plug.spec.ui.get("choices", ()):
            self.box.addItem(str(choice), choice)

        self.box.currentIndexChanged.connect(lambda index: self._emit(self.box.itemData(index)))
        self._layout.addWidget(self.box, 1)

    def set_value(self, value: Any) -> None:
        self.box.blockSignals(True)
        index = self.box.findData(value)

        if index < 0 and value is not None:
            self.box.addItem(str(value), value)
            index = self.box.count() - 1

        self.box.setCurrentIndex(index)
        self.box.blockSignals(False)


class TextBlockEditor(ParameterEditor):
    """Multi-line editor applied on focus loss or Ctrl+Return. JSON mode for lists and dicts."""

    def __init__(self, plug: Plug, parent: QWidget | None = None, as_json: bool = False) -> None:
        super().__init__(plug, parent)

        self.as_json = as_json
        self.text = _CommitTextEdit(self._commit)
        self.text.setFont(theme.monospace())
        self.text.setTabStopDistance(self.text.fontMetrics().horizontalAdvance(" ") * 4)

        lines = int(plug.spec.ui.get("lines", 8 if not as_json else 4))

        self.text.setFixedHeight(self.text.fontMetrics().lineSpacing() * lines + 12)
        self._layout.addWidget(self.text, 1)
        self._current = ""

    def set_value(self, value: Any) -> None:
        if self.as_json and not isinstance(value, str):
            try:
                text = json.dumps(value, indent=2)
            except TypeError:
                text = repr(value)
        else:
            text = "" if value is None else str(value)

        self._current = text

        if self.text.toPlainText() != text:
            self.text.setPlainText(text)

    def _commit(self) -> None:
        text = self.text.toPlainText()

        if text == self._current:
            return

        self._current = text

        if self.as_json:
            try:
                self._emit(json.loads(text))
                return
            except json.JSONDecodeError:
                pass

        self._emit(text)


class _CommitTextEdit(QPlainTextEdit):
    def __init__(self, commit: Callable[[], None]) -> None:
        super().__init__()

        self._commit = commit

    def focusOutEvent(self, event: Any) -> None:
        self._commit()

        super().focusOutEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key_Return, Qt.Key_Enter) and event.modifiers() & Qt.ControlModifier:
            self._commit()
            return

        super().keyPressEvent(event)


EditorFactory = Callable[[Plug], ParameterEditor]


class ParameterWidgets:
    """Chooses an editor for a plug: its ui 'widget' hint, its data type's hint, then its data type name."""

    def __init__(self) -> None:
        self._factories: dict[str, EditorFactory] = {
            "bool": BoolEditor,
            "int": lambda plug: NumberEditor(plug),
            "float": lambda plug: NumberEditor(plug, floating=True),
            "string": LineEditor,
            "path": PathEditor,
            "code": TextBlockEditor,
            "text": TextBlockEditor,
            "list": lambda plug: TextBlockEditor(plug, as_json=True),
            "dict": lambda plug: TextBlockEditor(plug, as_json=True),
            "choices": ChoiceEditor,
            "line": JsonLineEditor,
        }

    def register(self, key: str, factory: EditorFactory) -> None:
        self._factories[key] = factory

    def create(self, plug: Plug, expression: bool = False) -> ParameterEditor:
        if expression:
            return LineEditor(plug)

        data_type = plug.data_type
        keys = [plug.spec.ui.get("widget")]

        if "choices" in plug.spec.ui:
            keys.append("choices")

        if data_type is not None:
            keys += [data_type.ui.get("widget"), data_type.name]

        for key in keys:
            if key and key in self._factories:
                return self._factories[key](plug)

        return JsonLineEditor(plug)
