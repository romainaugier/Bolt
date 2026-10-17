import json
import re

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QSpinBox, QStyle, QToolButton
from qt_support import pump

from bolt.ui import theme
from bolt.ui.icons import bind_icon
from bolt.ui.views import NodeEditorView, ThemeEditorView


@pytest.fixture
def theme_editor(workspace):
    view = ThemeEditorView(workspace)
    view.show()
    pump()
    yield view
    view.close_view()


def test_presets_define_every_role():
    for preset in theme.presets.values():
        assert set(preset.colors) == {role.key for role in theme.color_roles}
        assert set(preset.metrics) == {role.key for role in theme.metric_roles}


def test_round_trip_and_partial_data():
    original = theme.presets["Palenight"]
    assert theme.Theme.from_dict(json.loads(json.dumps(original.to_dict()))) == original
    partial = theme.Theme.from_dict({"name": "Mine", "colors": {"canvas": "#80102030", "unknown": "#fff",
                                                                "text": "not a color"},
                                     "metrics": {"node_radius": 3, "connection_width": "wide"}})
    default = theme.presets[theme.default_preset]
    assert partial.name == "Mine"
    assert partial.colors["canvas"] == QColor(0x10, 0x20, 0x30, 0x80)
    assert partial.colors["text"] == default.colors["text"] and "unknown" not in partial.colors
    assert partial.metrics == {**default.metrics, "node_radius": 3.0}
    assert partial.to_dict()["colors"]["canvas"] == "#80102030"


def test_set_theme_notifies_and_saves(tmp_path):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.IniFormat)
    received = []
    theme.notifier().changed.connect(lambda: received.append(theme.canvas))
    theme.use_settings(settings)
    custom = theme.presets["Palenight"].copy("Custom")
    custom.colors["canvas"] = QColor("#123456")
    theme.set_theme(custom)
    assert theme.canvas == QColor("#123456") and received[-1] == QColor("#123456")
    theme.use_settings(None)
    theme.set_theme(theme.presets[theme.default_preset])
    theme.use_settings(QSettings(str(tmp_path / "settings.ini"), QSettings.IniFormat))
    assert theme.current() == custom


def test_bound_icons_follow_the_theme():
    button = QToolButton()
    bind_icon(button, "play_arrow-fill")
    before = button.icon().pixmap(16, 16).toImage()
    custom = theme.current().copy()
    custom.colors["text"] = QColor("#ff0000")
    theme.set_theme(custom)
    after = button.icon().pixmap(16, 16).toImage()
    assert before != after
    assert any(after.pixelColor(x, y).red() > 200 and after.pixelColor(x, y).green() < 50
               for x in range(16) for y in range(16))


def test_editor_changes_the_theme_live(theme_editor):
    assert theme_editor.preset.currentText() == theme.default_preset
    theme_editor.set_color("canvas", QColor("#010203"))
    assert theme.canvas != QColor("#010203")
    pump(0.05)
    assert theme.canvas == QColor("#010203")
    assert theme.current().name == "Custom" and theme_editor.preset.currentText() == "Custom"
    assert theme_editor.hex_edits["canvas"].text() == "#010203"

    theme_editor.spin_boxes["node_radius"].setValue(4)
    theme_editor.commit()
    assert theme.node_radius == 4.0

    theme_editor.reset()
    assert theme.current() == theme.presets[theme.default_preset]
    assert theme_editor.preset.currentText() == theme.default_preset
    assert theme_editor.spin_boxes["node_radius"].value() == 10


def test_editor_hex_fields(theme_editor):
    edit = theme_editor.hex_edits["error"]
    edit.setText("#40ff0000")
    edit.editingFinished.emit()
    theme_editor.commit()
    assert theme.error == QColor(255, 0, 0, 64)
    edit.setText("nonsense")
    edit.editingFinished.emit()
    assert edit.text() == "#40ff0000"


def test_editor_presets_import_and_export(theme_editor, tmp_path):
    theme_editor.preset.setCurrentText("Palenight")
    theme_editor.preset.activated.emit(theme_editor.preset.currentIndex())
    assert theme.current() == theme.presets["Palenight"]
    theme_editor.set_color("warning", QColor("#abcdef"))
    path = str(tmp_path / "mine.json")
    theme_editor.export_theme(path)
    assert json.load(open(path))["colors"]["warning"] == "#abcdef"

    theme_editor.reset()
    assert theme.current() == theme.presets["Palenight"]
    theme_editor.import_theme(path)
    assert theme.warning == QColor("#abcdef") and theme.text == theme.presets["Palenight"].colors["text"]
    theme_editor.import_theme(str(tmp_path / "missing.json"))
    assert theme.warning == QColor("#abcdef")


def test_color_dialog_previews_and_cancels(theme_editor):
    original = theme.accent
    dialog = theme_editor.pick_color("accent")
    dialog.setCurrentColor(QColor("#00ff00"))
    pump(0.05)
    assert theme.accent == QColor("#00ff00")
    dialog.reject()
    pump(0.05)
    assert theme.accent == original


def test_node_editor_repaints_with_the_theme(workspace, document):
    view = NodeEditorView(workspace)
    view.resize(400, 300)
    view.show()
    pump()
    try:
        custom = theme.current().copy()
        custom.colors["canvas"] = QColor("#204060")
        theme.set_theme(custom)
        pump()
        image = view.canvas.viewport().grab().toImage()
        assert image.pixelColor(3, 3) == QColor("#204060")
    finally:
        view.close_view()


def test_flat_controls(qapp):
    theme.apply(qapp)
    assert qapp.style().styleHint(QStyle.SH_UnderlineShortcut) == 0
    paths = re.findall(r"url\((.*?)\)", theme.stylesheet(theme.current()))
    assert paths and all(not QImage(path).isNull() for path in paths)

    spin_box = QSpinBox()
    spin_box.setRange(0, 10)
    spin_box.setValue(5)
    spin_box.resize(120, spin_box.sizeHint().height())
    spin_box.show()
    pump()
    image = spin_box.grab().toImage()
    text = theme.text
    arrow_pixels = [(x, y) for x in range(image.width() - 18, image.width()) for y in range(image.height())
                    if all(abs(a - b) < 40 for a, b in zip(image.pixelColor(x, y).getRgb()[:3], text.getRgb()[:3]))]
    assert arrow_pixels
