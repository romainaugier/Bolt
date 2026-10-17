from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPaintEvent
from PySide6.QtWidgets import (QAbstractButton, QColorDialog, QComboBox, QDoubleSpinBox, QFileDialog, QGridLayout,
                               QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea, QVBoxLayout, QWidget)

from bolt.ui import theme
from bolt.ui.views.base import View

if TYPE_CHECKING:
    from bolt.ui.workspace import Workspace

logger = logging.getLogger("bolt.ui")

custom_name = "Custom"


def matching_preset(candidate: theme.Theme) -> str | None:
    for name, preset in theme.presets.items():
        if preset.colors == candidate.colors and preset.metrics == candidate.metrics:
            return name

    return None


class ColorSwatch(QAbstractButton):
    """A button showing a color over a checkerboard, so that transparency is visible."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.color = QColor()
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover)
        self.setFixedSize(QSize(46, 20))

    def set_color(self, color: QColor) -> None:
        if color != self.color:
            self.color = QColor(color)
            self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)

        if self.color.alpha() < 255:
            outline = QPainterPath()
            outline.addRoundedRect(rect, 4, 4)

            painter.save()
            painter.setClipPath(outline)
            painter.fillRect(rect, QColor("#ffffff"))

            step = 5

            for row in range(self.height() // step + 1):
                for column in range(row % 2, self.width() // step + 1, 2):
                    painter.fillRect(column * step, row * step, step, step, QColor("#c8c8c8"))

            painter.restore()

        painter.setBrush(self.color)
        painter.setPen(theme.border if not self.underMouse() else theme.text_strong)
        painter.drawRoundedRect(rect, 4, 4)
        painter.end()


class ThemeEditorView(View):
    view_type = "theme_editor"
    label = "Theme"
    description = "Colors and shapes of the editor, changed live and kept between sessions."

    def __init__(self, workspace: Workspace, parent: QWidget | None = None) -> None:
        super().__init__(workspace, parent)

        self.preset = QComboBox()
        self.preset.addItems([*theme.presets, custom_name])
        self.preset.setToolTip("Start from a preset. Editing any color makes the theme custom.")
        self.preset.activated.connect(lambda index: self._choose_preset(self.preset.itemText(index)))

        buttons = QHBoxLayout()
        buttons.addWidget(self.preset, 1)

        for text, tooltip, slot in (("Reset", "Go back to the preset this theme started from", self.reset),
                                    ("Import…", "Load a theme from a JSON file", self.import_theme),
                                    ("Export…", "Save this theme to a JSON file", self.export_theme)):
            button = QPushButton(text)
            button.setToolTip(tooltip)
            button.clicked.connect(slot)
            buttons.addWidget(button)

        self.swatches: dict[str, ColorSwatch] = {}
        self.hex_edits: dict[str, QLineEdit] = {}
        self.spin_boxes: dict[str, QDoubleSpinBox] = {}

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(4)
        grid.setColumnStretch(0, 1)

        row = 0

        group = ""

        for role in theme.color_roles:
            if role.group != group:
                group = role.group
                row = self._add_heading(grid, row, group)

            swatch = ColorSwatch()
            swatch.setToolTip(f"{role.label} ({role.key})")
            swatch.clicked.connect(lambda checked=False, key=role.key: self.pick_color(key))

            hex_edit = QLineEdit()
            hex_edit.setFixedWidth(84)
            hex_edit.setFont(theme.monospace())
            hex_edit.editingFinished.connect(lambda key=role.key: self._hex_edited(key))

            grid.addWidget(QLabel(role.label), row, 0)
            grid.addWidget(hex_edit, row, 1)
            grid.addWidget(swatch, row, 2)

            self.swatches[role.key] = swatch
            self.hex_edits[role.key] = hex_edit

            row += 1

        row = self._add_heading(grid, row, "Shapes")

        for metric in theme.metric_roles:
            spin_box = QDoubleSpinBox()
            spin_box.setRange(metric.minimum, metric.maximum)
            spin_box.setSingleStep(metric.step)
            spin_box.setDecimals(0 if float(metric.step).is_integer() else 2)
            spin_box.valueChanged.connect(lambda value, key=metric.key: self.set_metric(key, value))

            grid.addWidget(QLabel(metric.label), row, 0)
            grid.addWidget(spin_box, row, 1, 1, 2)

            self.spin_boxes[metric.key] = spin_box

            row += 1

        grid.setRowStretch(row, 1)

        content = QWidget()
        content.setLayout(grid)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addLayout(buttons)
        layout.addWidget(scroll, 1)

        self.base_preset = theme.default_preset
        self._pending: theme.Theme | None = None
        self._commit_timer = QTimer(self)
        self._commit_timer.setSingleShot(True)
        self._commit_timer.setInterval(16)
        self._commit_timer.timeout.connect(self.commit)

        theme.notifier().changed.connect(self.refresh)

        self.refresh()

    @staticmethod
    def _add_heading(grid: QGridLayout, row: int, text: str) -> int:
        heading = QLabel(text.upper())
        heading.setObjectName("muted")

        grid.addWidget(heading, row, 0, 1, 3, Qt.AlignBottom)
        grid.setRowMinimumHeight(row, 30 if row else 18)

        return row + 1

    def edited(self) -> theme.Theme:
        """The theme being edited: changes waiting for the next commit, else the current theme."""
        return self._pending if self._pending is not None else theme.current()

    def set_color(self, key: str, color: QColor) -> None:
        self._edit(lambda edited: edited.colors.__setitem__(key, QColor(color)))

    def set_metric(self, key: str, value: float) -> None:
        self._edit(lambda edited: edited.metrics.__setitem__(key, float(value)))

    def _edit(self, change: Callable[[theme.Theme], None]) -> None:
        edited = self.edited().copy()

        change(edited)

        edited.name = matching_preset(edited) or custom_name

        if edited == self.edited():
            return

        self._pending = edited
        self._show(edited)
        self._commit_timer.start()

    def commit(self) -> None:
        """Make pending changes current. Edits are coalesced: restyling the whole application on every move of the
        color dialog would make it lag."""
        self._commit_timer.stop()

        pending, self._pending = self._pending, None

        if pending is not None:
            theme.set_theme(pending)

    def pick_color(self, key: str) -> QColorDialog:
        original = self.edited().color(key)

        dialog = QColorDialog(original, self)
        dialog.setOption(QColorDialog.ShowAlphaChannel)
        dialog.setOption(QColorDialog.DontUseNativeDialog)
        dialog.setWindowTitle(next(role.label for role in theme.color_roles if role.key == key))
        dialog.setAttribute(Qt.WA_DeleteOnClose)
        dialog.currentColorChanged.connect(lambda color: self.set_color(key, color))
        dialog.rejected.connect(lambda: self.set_color(key, original))
        dialog.open()

        return dialog

    def _hex_edited(self, key: str) -> None:
        text = self.hex_edits[key].text().strip()

        if QColor.isValidColorName(text):
            self.set_color(key, QColor(text))
        else:
            self.hex_edits[key].setText(theme.color_name(self.edited().colors[key]))

    def _choose_preset(self, name: str) -> None:
        if name in theme.presets:
            self._pending = None
            self._commit_timer.stop()

            theme.set_theme(theme.presets[name])
        else:
            self.refresh()

    def reset(self) -> None:
        self._choose_preset(self.base_preset)

    def import_theme(self, path: str | None = None) -> None:
        if path is None:
            path, _ = QFileDialog.getOpenFileName(self, "Import theme", "", "Themes (*.json);;All files (*)")

            if not path:
                return
        try:
            with open(path, encoding="utf-8") as stream:
                imported = theme.Theme.from_dict(json.load(stream), theme.presets[self.base_preset])
        except (OSError, ValueError, AttributeError) as error:
            logger.error("cannot import the theme '%s': %s", path, error)
            return

        self._pending = None

        theme.set_theme(imported)

    def export_theme(self, path: str | None = None) -> None:
        if path is None:
            path, _ = QFileDialog.getSaveFileName(self, "Export theme", "theme.json", "Themes (*.json)")

            if not path:
                return

        self.commit()

        try:
            with open(path, "w", encoding="utf-8") as stream:
                json.dump(theme.current().to_dict(), stream, indent=2)
        except OSError as error:
            logger.error("cannot export the theme to '%s': %s", path, error)

    def refresh(self) -> None:
        self._show(self.edited())

    def _show(self, shown: theme.Theme) -> None:
        preset = matching_preset(shown)

        if preset is not None:
            self.base_preset = preset

        self.preset.setCurrentText(preset or custom_name)
        for key, swatch in self.swatches.items():

            swatch.set_color(shown.colors[key])
            hex_edit = self.hex_edits[key]

            if not hex_edit.hasFocus():
                hex_edit.setText(theme.color_name(shown.colors[key]))

        for key, spin_box in self.spin_boxes.items():
            if spin_box.value() != shown.metrics[key]:
                spin_box.blockSignals(True)
                spin_box.setValue(shown.metrics[key])
                spin_box.blockSignals(False)

    def save_state(self) -> dict[str, Any]:
        return {}

    def close_view(self) -> None:
        self.commit()

        super().close_view()
