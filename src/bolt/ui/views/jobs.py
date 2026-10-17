from __future__ import annotations

import html
import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QHBoxLayout, QHeaderView, QPlainTextEdit, QProgressBar, QPushButton, QSplitter,
                               QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from bolt.core.jobs import Job, JobAdded, JobChanged, JobLog, JobRemoved, JobStatus
from bolt.ui import theme
from bolt.ui.views.base import View
from bolt.ui.views.log import level_color

if TYPE_CHECKING:
    from bolt.ui.workspace import Workspace

status_roles = {JobStatus.queued: "muted", JobStatus.running: "accent", JobStatus.paused: "warning",
                JobStatus.succeeded: "success", JobStatus.failed: "error", JobStatus.cancelled: "muted"}


class JobsView(View):
    view_type = "jobs"
    label = "Jobs"
    description = "Graphs cooking in background processes: progress, logs, pause and cancel."

    def __init__(self, workspace: Workspace, parent: QWidget | None = None) -> None:
        super().__init__(workspace, parent)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Job", "Status", "Progress", "Node", "Time"])
        self.tree.setRootIsDecorated(False)
        self.tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tree.currentItemChanged.connect(lambda current, previous: self._show_log())
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setFont(theme.monospace())
        self.log.setMaximumBlockCount(5000)
        self.items: dict[Job, QTreeWidgetItem] = {}
        self.bars: dict[Job, QProgressBar] = {}

        buttons = QHBoxLayout()

        for label, slot in (("Submit current graph", self._submit), ("Pause", self._pause), ("Resume", self._resume),
                            ("Cancel", self._cancel), ("Clear finished", self.workspace.jobs.clear_finished)):
            button = QPushButton(label)
            button.clicked.connect(slot)
            buttons.addWidget(button)

        buttons.addStretch(1)
        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self.tree)
        splitter.addWidget(self.log)
        splitter.setSizes([200, 120])
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addLayout(buttons)
        layout.addWidget(splitter)

        self.subscribe(JobAdded, lambda event: self._add(event.job))
        self.subscribe(JobChanged, lambda event: self._update(event.job))
        self.subscribe(JobRemoved, lambda event: self._remove(event.job))
        self.subscribe(JobLog, self._log)

        for job in workspace.jobs.jobs():
            self._add(job)

    def current_job(self) -> Job | None:
        item = self.tree.currentItem()

        return item.data(0, Qt.UserRole) if item is not None else None

    def _add(self, job: Job) -> None:
        if job in self.items:
            return

        item = QTreeWidgetItem([f"#{job.id} {job.name}", "", "", "", ""])
        item.setData(0, Qt.UserRole, job)
        self.tree.addTopLevelItem(item)
        bar = QProgressBar()
        bar.setRange(0, 1000)
        bar.setTextVisible(True)
        bar.setMaximumHeight(14)
        self.tree.setItemWidget(item, 2, bar)
        self.items[job] = item
        self.bars[job] = bar
        self._update(job)

        if self.tree.currentItem() is None:
            self.tree.setCurrentItem(item)

    def _update(self, job: Job) -> None:
        item = self.items.get(job)

        if item is None:
            return

        item.setText(1, job.status.value)
        item.setForeground(1, getattr(theme, status_roles[job.status]))
        item.setText(3, job.current_node or "")
        duration = job.duration
        item.setText(4, f"{duration:.1f}s" if duration is not None else "")
        bar = self.bars[job]
        bar.setValue(int(job.progress * 1000))
        bar.setFormat(f"{job.done}/{job.total}" if job.total else "")

    def _remove(self, job: Job) -> None:
        item = self.items.pop(job, None)
        self.bars.pop(job, None)

        if item is not None:
            self.tree.takeTopLevelItem(self.tree.indexOfTopLevelItem(item))

    def _log(self, event: JobLog) -> None:
        if event.job is self.current_job():
            self._append(event.level, event.message)

    def _show_log(self) -> None:
        self.log.clear()
        job = self.current_job()

        if job is not None:
            for level, message, node in list(job.log):
                self._append(level, message)

    def _append(self, level: int, message: str) -> None:
        color = level_color(level).name()
        self.log.appendHtml(f'<span style="color:{color}">{html.escape(message)}</span>')

    def _submit(self) -> None:
        job = self.workspace.submit_job()

        if job is None:
            logging.getLogger("bolt.ui").warning("open a graph before submitting a job")

    def _pause(self) -> None:
        job = self.current_job()

        if job is not None:
            job.pause()

    def _resume(self) -> None:
        job = self.current_job()

        if job is not None:
            job.resume()

    def _cancel(self) -> None:
        job = self.current_job()

        if job is not None:
            job.cancel()
