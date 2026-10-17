import gc
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtCore import QStandardPaths  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from bolt.core.live import LiveMode  # noqa: E402
from bolt.ui import theme  # noqa: E402
from bolt.ui.collector import GarbageCollector  # noqa: E402
from bolt.core.registry import Registry  # noqa: E402
from bolt.ui.workspace import Workspace  # noqa: E402
from qt_support import pump  # noqa: E402


@pytest.fixture(scope="session")
def qapp():
    QStandardPaths.setTestModeEnabled(True)
    application = QApplication.instance() or QApplication([])
    collector = GarbageCollector(application)
    collector.start()
    yield application
    QApplication.clipboard().clear()
    collector.stop()


@pytest.fixture(autouse=True)
def _collect_garbage(qapp):
    """Collect each test's garbage on the GUI thread, like the editor does, so that it is never freed by a cooking
    thread. The session clears the clipboard at the end: its data crashes the offscreen platform plugin at exit.
    Tests changing the theme get the default one back."""
    yield
    gc.collect()
    pump()
    if theme.current() != theme.presets[theme.default_preset] or theme._settings is not None:
        theme.use_settings(None)
        theme.set_theme(theme.presets[theme.default_preset])


@pytest.fixture
def registry():
    registry = Registry()
    registry.load_plugin("bolt.stdlib")
    return registry


@pytest.fixture
def workspace(qapp, registry, tmp_path):
    from bolt.core.jobs import JobManager
    workspace = Workspace(registry, live_mode=LiveMode.manual, jobs=JobManager(registry, directory=str(tmp_path)))
    yield workspace
    workspace.close()
    pump()


@pytest.fixture
def document(workspace):
    return workspace.new_document()
