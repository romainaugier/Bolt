import os

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QToolButton
from qt_support import pump, wait_until

from bolt.core.node import NodeState
from bolt.ui import theme
from bolt.ui.app import Application
from bolt.ui.commands import create_node_command
from bolt.ui.icons import IconLibrary, Spinner, bind_icon, builtin_directory, library, spinner_frame_count
from bolt.ui.views import NodeEditorView


def opaque_pixels(image):
    return [(x, y) for x in range(image.width()) for y in range(image.height()) if image.pixelColor(x, y).alpha() > 200]


def test_material_symbols_are_shipped(qapp):
    assert os.path.isfile(os.path.join(builtin_directory, "LICENSE-material-symbols.txt"))
    for name in ("play_arrow-fill", "check_circle-fill", "error-fill", "schedule", "deployed_code"):
        assert name in library and library.path(name).endswith(".svg")
    assert library.path("bolt").endswith("bolt.png") and library.pixmap("bolt", 18).width() == 18
    for extent in (16, 18, 64):
        pixmap = library.pixmap("save", extent)
        assert pixmap.width() == extent and opaque_pixels(pixmap.toImage())
    assert library.pixmap("unknown").isNull() and library.icon("unknown").isNull()
    sizes = library.icon("save").availableSizes()
    assert min(size.width() for size in sizes) == 16 and max(size.width() for size in sizes) == 64


def test_tinting_keeps_the_shape(qapp):
    tinted = library.pixmap("add", 32, QColor("#ff0000")).toImage()
    original = library.pixmap("add", 32).toImage()
    opaque = opaque_pixels(original)
    assert opaque
    for x, y in opaque:
        assert tinted.pixelColor(x, y).red() > 200 and tinted.pixelColor(x, y).green() < 30
        assert tinted.pixelColor(x, y).alpha() == original.pixelColor(x, y).alpha()
    assert tinted.pixelColor(0, 0).alpha() == original.pixelColor(0, 0).alpha()


def test_folders_override_and_paths(qapp, tmp_path):
    image = QImage(8, 8, QImage.Format_ARGB32)
    image.fill(QColor("#00ff00"))
    image.save(str(tmp_path / "save.png"))
    image.save(str(tmp_path / "custom.png"))
    icons = IconLibrary([builtin_directory])
    assert icons.add_directory(str(tmp_path)) == ["custom", "save"]
    assert icons.path("save") == str(tmp_path / "save.png")
    assert icons.pixmap("custom").toImage().pixelColor(4, 4) == QColor("#00ff00")
    assert icons.path(str(tmp_path / "custom.png")) == str(tmp_path / "custom.png")
    assert icons.add_file(str(tmp_path / "custom.png"), "other") == "other" and "other" in icons


def test_bound_icons_follow_the_theme(qapp):
    button = QToolButton()
    bind_icon(button, "vertical_split")
    muted = QToolButton()
    bind_icon(muted, "close", "muted")
    before = button.icon().pixmap(32, 32).toImage()
    custom = theme.current().copy()
    custom.colors["text"] = QColor("#00ff00")
    custom.colors["muted"] = QColor("#0000ff")
    theme.set_theme(custom)
    after = button.icon().pixmap(32, 32).toImage()
    assert before != after
    for x, y in opaque_pixels(after):
        assert after.pixelColor(x, y).green() > 200 and after.pixelColor(x, y).red() < 30
    closed = muted.icon().pixmap(32, 32).toImage()
    assert all(closed.pixelColor(x, y).blue() > 200 for x, y in opaque_pixels(closed))


def test_spinner(qapp):
    spinner = Spinner()
    first = spinner.pixmap(32, QColor("#ffcb6b")).toImage()
    assert opaque_pixels(first) and first.pixelColor(0, 0).alpha() == 0
    frames = []
    spinner.advanced.connect(lambda: frames.append(spinner.frame))
    spinner.start()
    assert wait_until(lambda: len(frames) >= 3, 2)
    spinner.stop()
    assert spinner.pixmap(32, QColor("#ffcb6b")).toImage() != first
    assert all(0 <= frame < spinner_frame_count for frame in frames) and not spinner.running


@pytest.fixture
def editor(workspace, document):
    view = NodeEditorView(workspace)
    view.resize(600, 400)
    view.show()
    pump()
    yield view
    view.close_view()


def test_node_icons_and_cooking_indicator(editor, document):
    document.push(create_node_command(document, document.graph, "bolt.subgraph", (0, 0), name="sub"))
    document.push(create_node_command(document, document.graph, "math.add", (0, 100), name="add"))
    scene = editor.canvas.graph_scene
    sub, add = scene.node_items[document.graph.node("sub")], scene.node_items[document.graph.node("add")]
    header = sub.header_icon().toImage()
    expected = theme.node_text.getRgb()[:3]
    assert all(all(abs(a - b) <= 3 for a, b in zip(header.pixelColor(x, y).getRgb()[:3], expected))
               for x, y in opaque_pixels(header))
    assert add.header_icon() is None

    add.node.state = NodeState.cooking
    assert not scene.cooking_frame(add).isNull() and scene.spinner.running
    add.node.state = NodeState.cooked
    assert wait_until(lambda: not scene.spinner.running, 2)
    assert not scene.cooking_items


def test_document_tabs_show_the_cook_status(qapp):
    application = Application(organization="BoltTest", name="BoltIcons", discover=False, restore_layout=False)
    window = application.build()
    try:
        document = application.workspace.current
        assert window.status_icon(document).cacheKey() == library.icon("schedule", theme.muted).cacheKey()
        document.push(create_node_command(document, document.graph, "math.add", (0, 0), name="add"))
        window.cook()
        assert wait_until(lambda: window.document_status.get(document) == "done", 5)
        assert window.status_icon(document).cacheKey() == library.icon("check_circle-fill", theme.success).cacheKey()
        document.push(create_node_command(document, document.graph, "flow.fail", (0, 100), name="fail"))
        document.graph.node("fail").displayed = True
        window.cook()
        assert wait_until(lambda: window.document_status.get(document) == "error", 5)
        assert not window.document_tabs.tabIcon(0).isNull()
        assert not qapp.windowIcon().isNull() and not window.logo.pixmap().isNull()
    finally:
        document.undo_stack.setClean()
        window.close()


def test_node_library_shows_icons(workspace):
    from bolt.ui.views import NodeLibraryView
    view = NodeLibraryView(workspace)
    items = view.tree.findItems("bolt.subgraph", Qt.MatchExactly | Qt.MatchRecursive)
    assert items and not items[0].icon(0).isNull()
    view.close_view()
