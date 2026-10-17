from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import QSettings, QSize, Qt
from PySide6.QtGui import QAction, QCloseEvent, QIcon, QKeySequence
from PySide6.QtWidgets import (QComboBox, QDialog, QFileDialog, QInputDialog, QLabel, QMainWindow, QMessageBox,
                               QSizePolicy, QTabBar, QToolBar, QVBoxLayout, QWidget)

from bolt.core import events
from bolt.core.live import EditPolicy, LiveMode, LiveStateChanged
from bolt.ui.events import CurrentDocumentChanged, DocumentClosed, DocumentOpened, DocumentStateChanged
from bolt.ui import icons, theme
from bolt.ui.icons import bind_icon
from bolt.ui.layout import Workbench, closing_button
from bolt.ui.views.theme_editor import ThemeEditorView

if TYPE_CHECKING:
    from bolt.core.graph import Graph
    from bolt.ui.app import Application, UiRegistry
    from bolt.ui.workspace import Document, Workspace

logger = logging.getLogger("bolt.ui")
status_icons = {"waiting": ("schedule", "muted"), "edited": ("edit", "text"), "done": ("check_circle-fill", "success"),
                "error": ("error-fill", "error")}
file_filter = "Bolt graphs (*.bolt);;All files (*)"


class MainWindow(QMainWindow):
    def __init__(self, application: Application, workspace: Workspace, ui: UiRegistry) -> None:
        super().__init__()

        self.application = application
        self.workspace = workspace
        self.settings = QSettings(application.organization, application.name)
        self._theme_dialog: QDialog | None = None
        self.document_status: dict[Document, str] = {}
        self._tab_spinner = icons.Spinner(self)
        self._tab_spinner.advanced.connect(self._animate_tabs)

        theme.notifier().changed.connect(self._refresh_documents)

        self.workbench = Workbench(workspace, ui.views)
        self.setCentralWidget(self.workbench)
        self.resize(1440, 900)
        self._subscriptions = [
            workspace.events.subscribe(DocumentOpened, lambda event: self._refresh_documents()),
            workspace.events.subscribe(DocumentClosed, lambda event: self._refresh_documents()),
            workspace.events.subscribe(DocumentStateChanged, self._document_state_changed),
            workspace.events.subscribe(events.EvaluationStarted, self._evaluation_started),
            workspace.events.subscribe(CurrentDocumentChanged, lambda event: self._current_changed()),
            workspace.events.subscribe(LiveStateChanged, self._live_state),
            workspace.events.subscribe(events.EvaluationFinished, self._evaluation_finished),
            workspace.events.subscribe(events.EvaluationProgress, self._evaluation_progress),
        ]
        self._build_toolbar()
        self._build_menus()
        self.state_label = QLabel()
        self.statusBar().addPermanentWidget(self.state_label)
        self._restore_settings()
        self._refresh_documents()
        self._current_changed()

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Main")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(16, 16))

        self.addToolBar(Qt.TopToolBarArea, toolbar)
        self.document_tabs = QTabBar()
        self.document_tabs.setDrawBase(False)
        self.document_tabs.setExpanding(False)
        self.document_tabs.currentChanged.connect(self._tab_selected)

        toolbar.addWidget(self.document_tabs)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        toolbar.addWidget(spacer)

        self.cook_action = QAction("Cook", self)

        bind_icon(self.cook_action, "play_arrow-fill", "success")

        self.cook_action.setShortcut(QKeySequence("F5"))
        self.cook_action.setToolTip("Cook the displayed nodes, or the whole graph if none is displayed (F5)")
        self.cook_action.triggered.connect(self.cook)
        self.stop_action = QAction("Stop", self)

        bind_icon(self.stop_action, "stop-fill", "error")

        self.stop_action.setShortcut(QKeySequence("Shift+F5"))
        self.stop_action.triggered.connect(self.stop)
        self.auto_action = QAction("Auto cook", self)

        bind_icon(self.auto_action, "autorenew")

        self.auto_action.setCheckable(True)
        self.auto_action.setToolTip("Cook the displayed nodes automatically after every edit")
        self.auto_action.toggled.connect(self._set_auto)
        self.policy_box = QComboBox()
        self.policy_box.addItem("Edits restart the cook", EditPolicy.restart)
        self.policy_box.addItem("Edits wait for the cook", EditPolicy.finish)
        self.policy_box.currentIndexChanged.connect(self._set_policy)
        self.job_action = QAction("Submit job", self)

        bind_icon(self.job_action, "rocket_launch")

        self.job_action.setToolTip("Cook a snapshot of the graph in a background process")
        self.job_action.triggered.connect(lambda: self.workspace.submit_job())

        for item in (self.auto_action, self.policy_box, self.cook_action, self.stop_action, self.job_action):
            if isinstance(item, QAction):
                toolbar.addAction(item)
            else:
                toolbar.addWidget(item)

    def _build_menus(self) -> None:
        menu = self.menuBar()

        self.logo = QLabel()
        self.logo.setObjectName("logo")
        self.logo.setPixmap(icons.library.pixmap("bolt", 18))
        self.logo.setToolTip(self.application.name)

        menu.setCornerWidget(self.logo, Qt.TopLeftCorner)

        file_menu = menu.addMenu("&File")

        for text, icon_name, shortcut, slot in (
                ("New", "note_add", QKeySequence.New, self.new_document),
                ("Open…", "folder_open", QKeySequence.Open, self.open_document),
                ("Save", "save", QKeySequence.Save, self.save_document),
                ("Save as…", "save_as", QKeySequence.SaveAs, lambda: self.save_document(save_as=True)),
                ("Close", "close", QKeySequence.Close, self.close_document)):
            action = file_menu.addAction(text, slot)
            action.setShortcut(shortcut)
            bind_icon(action, icon_name)

        file_menu.addSeparator()
        file_menu.addAction("Quit", self.close).setShortcut(QKeySequence.Quit)

        edit_menu = menu.addMenu("&Edit")

        undo = self.workspace.undo_group.createUndoAction(self, "Undo")
        undo.setShortcut(QKeySequence.Undo)

        redo = self.workspace.undo_group.createRedoAction(self, "Redo")
        redo.setShortcut(QKeySequence.Redo)

        edit_menu.addAction(undo)
        edit_menu.addAction(redo)

        cook_menu = menu.addMenu("&Cook")

        for action in (self.cook_action, self.stop_action, self.auto_action, self.job_action):
            cook_menu.addAction(action)

        window_menu = menu.addMenu("&Window")
        window_menu.addAction("Save layout as…", self.save_layout_as)

        self.layouts_menu = window_menu.addMenu("Layouts")
        self.layouts_menu.aboutToShow.connect(self._fill_layouts_menu)

        window_menu.addAction("Reset layout", lambda: self.workbench.restore(self.application.default_layout))
        window_menu.addSeparator()

        bind_icon(window_menu.addAction("Theme editor…", self.show_theme_editor), "palette")

    def document(self) -> Document | None:
        return self.workspace.current

    def new_document(self) -> None:
        self.workspace.new_document()

    def open_document(self, path: str | None = None) -> None:
        if not path:
            path, _ = QFileDialog.getOpenFileName(self, "Open graph", "", file_filter)

        if path:
            try:
                self.workspace.open(path)
            except Exception as error:
                QMessageBox.critical(self, "Cannot open the graph", str(error))

    def save_document(self, save_as: bool = False) -> bool:
        document = self.document()

        if document is None:
            return False

        path = document.path

        if save_as or not path:
            path, _ = QFileDialog.getSaveFileName(self, "Save graph", path or f"{document.name}.bolt", file_filter)

            if not path:
                return False

        try:
            document.save(path)
        except Exception as error:
            QMessageBox.critical(self, "Cannot save the graph", str(error))

            return False

        return True

    def close_document(self, document: Document | None = None) -> bool:
        document = document or self.document()

        if document is None:
            return True

        if document.modified:
            self.workspace.set_current(document)
            answer = QMessageBox.question(self, "Unsaved changes", f"Save the changes to {document.name}?",
                                          QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)

            if answer == QMessageBox.Cancel or (answer == QMessageBox.Save and not self.save_document()):
                return False

        self.workspace.close_document(document)

        return True

    def cook(self) -> None:
        document = self.document()

        if document is not None:
            graph = document.graph
            document.live.cook(None if graph.displayed_nodes() else list(graph))

    def stop(self) -> None:
        document = self.document()

        if document is not None:
            document.live.stop()

    def show_theme_editor(self) -> QDialog:
        """The theme editor in its own window; it can also be opened in any pane as the "Theme" view."""
        if self._theme_dialog is None:
            dialog = QDialog(self)
            dialog.setWindowTitle("Theme")
            dialog.resize(420, 640)

            editor = ThemeEditorView(self.workspace, dialog)

            layout = QVBoxLayout(dialog)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(editor)

            dialog.finished.connect(lambda result: editor.commit())

            self._theme_dialog = dialog

        self._theme_dialog.show()
        self._theme_dialog.raise_()

        return self._theme_dialog

    def save_layout_as(self) -> None:
        name, accepted = QInputDialog.getText(self, "Save layout", "Name")

        if accepted and name:
            self.settings.setValue(f"layouts/{name}", json.dumps(self.workbench.to_dict()))

    def closeEvent(self, event: QCloseEvent) -> None:
        for document in list(self.workspace.documents):
            if not self.close_document(document):
                event.ignore()
                return

        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("layout", json.dumps(self.workbench.to_dict()))

        for subscription in self._subscriptions:
            subscription.close()

        for view in self.workbench.all_views():
            view.close_view()

        if self._theme_dialog is not None:
            self._theme_dialog.findChild(ThemeEditorView).close_view()

        self.workspace.close()

        event.accept()

    def _restore_settings(self) -> None:
        geometry = self.settings.value("geometry")

        if geometry is not None:
            self.restoreGeometry(geometry)

        layout = self.settings.value("layout") if self.application.restore_layout else None

        try:
            self.workbench.restore(json.loads(layout) if layout else self.application.default_layout)
        except Exception:
            logger.exception("cannot restore the saved layout")
            self.workbench.restore(self.application.default_layout)

    def _fill_layouts_menu(self) -> None:
        self.layouts_menu.clear()
        self.settings.beginGroup("layouts")

        names = self.settings.childKeys()

        self.settings.endGroup()

        for name in sorted(names):
            self.layouts_menu.addAction(name, lambda name=name: self.workbench.restore(
                json.loads(self.settings.value(f"layouts/{name}"))))

        if not names:
            self.layouts_menu.addAction("No saved layout").setEnabled(False)

    def _refresh_documents(self) -> None:
        for document in [document for document in self.document_status if document not in self.workspace.documents]:
            del self.document_status[document]

        tabs = self.document_tabs
        tabs.blockSignals(True)

        while tabs.count():
            tabs.removeTab(0)

        for document in self.workspace.documents:
            index = tabs.addTab(self.status_icon(document), document.name + (" *" if document.modified else ""))
            close = closing_button(f"Close {document.name}")
            close.clicked.connect(lambda checked=False, document=document: self.close_document(document))
            tabs.setTabButton(index, QTabBar.RightSide, close)

        if self.workspace.current in self.workspace.documents:
            tabs.setCurrentIndex(self.workspace.documents.index(self.workspace.current))

        tabs.blockSignals(False)
        self._update_title()

    def status_icon(self, document: Document) -> QIcon:
        """The tab icons of the original Bolt: waiting, edited, cooking (animated), done or error."""
        status = self.document_status.get(document, "edited" if document.modified else "waiting")

        if status == "cooking":
            return QIcon(self._tab_spinner.pixmap(32, theme.warning))

        name, role = status_icons[status]

        return icons.library.icon(name, getattr(theme, role))

    def _set_status(self, document: Document, status: str) -> None:
        self.document_status[document] = status

        if status == "cooking":
            self._tab_spinner.start()
        elif "cooking" not in self.document_status.values():
            self._tab_spinner.stop()

        if document in self.workspace.documents:
            self.document_tabs.setTabIcon(self.workspace.documents.index(document), self.status_icon(document))

    def _animate_tabs(self) -> None:
        for index, document in enumerate(self.workspace.documents):
            if self.document_status.get(document) == "cooking" and index < self.document_tabs.count():
                self.document_tabs.setTabIcon(index, self.status_icon(document))

    def _document_of(self, graph: Graph) -> Document | None:
        return next((document for document in self.workspace.documents if document.graph is graph), None)

    def _document_state_changed(self, event: DocumentStateChanged) -> None:
        document = event.document

        if document.modified and self.document_status.get(document) != "cooking":
            self.document_status[document] = "edited"

        self._refresh_documents()

    def _evaluation_started(self, event: events.EvaluationStarted) -> None:
        document = self._document_of(event.graph)

        if document is not None:
            self._set_status(document, "cooking")

    def _current_changed(self) -> None:
        self._refresh_documents()

        document = self.document()
        enabled = document is not None

        for action in (self.cook_action, self.stop_action, self.auto_action, self.job_action):
            action.setEnabled(enabled)

        self.policy_box.setEnabled(enabled)

        if document is not None:
            self._show_live(document.live.mode, document.live.policy, document.live.busy)

    def _update_title(self) -> None:
        document = self.document()
        title = self.application.name

        if document is not None:
            title = f"{document.name}{' *' if document.modified else ''} — {title}"

        self.setWindowTitle(title)

    def _tab_selected(self, index: int) -> None:
        if 0 <= index < len(self.workspace.documents):
            self.workspace.set_current(self.workspace.documents[index])

    def _set_auto(self, checked: bool) -> None:
        document = self.document()
        mode = LiveMode.auto if checked else LiveMode.manual

        self.workspace.live_mode = mode

        if document is not None and document.live.mode is not mode:
            document.live.mode = mode

    def _set_policy(self, index: int) -> None:
        policy = self.policy_box.itemData(index)
        document = self.document()

        self.workspace.live_policy = policy

        if document is not None and document.live.policy is not policy:
            document.live.policy = policy

    def _live_state(self, event: LiveStateChanged) -> None:
        document = self.document()

        if document is not None and event.graph is document.graph:
            self._show_live(event.mode, event.policy, event.busy)

    def _show_live(self, mode: LiveMode, policy: EditPolicy, busy: bool) -> None:
        self.auto_action.blockSignals(True)
        self.auto_action.setChecked(mode is LiveMode.auto)
        self.auto_action.blockSignals(False)
        self.policy_box.blockSignals(True)
        self.policy_box.setCurrentIndex(self.policy_box.findData(policy))
        self.policy_box.blockSignals(False)
        self.stop_action.setEnabled(busy)
        self.state_label.setText("cooking…" if busy else ("auto" if mode is LiveMode.auto else "manual"))

    def _evaluation_progress(self, event: events.EvaluationProgress) -> None:
        document = self.document()

        if document is not None and event.graph is document.graph and event.total:
            self.state_label.setText(f"cooking {event.done}/{event.total}")

    def _evaluation_finished(self, event: events.EvaluationFinished) -> None:
        finished = self._document_of(event.graph)

        if finished is not None:
            result = event.result
            self._set_status(finished, "error" if result.failed else "edited" if result.cancelled else "done")

        document = self.document()

        if document is None or event.graph is not document.graph:
            return

        result = event.result

        if result.cancelled:
            message = "Cook cancelled"
        elif result.failed:
            node, error = next(iter(result.failed.items()))
            message = f"{len(result.failed)} node(s) failed: {node.path}: {error.splitlines()[-1] if error else ''}"
        else:
            message = f"Cooked {len(result.cooked)} node(s) in {result.duration * 1000:.1f} ms"

        self.statusBar().showMessage(message, 8000)
