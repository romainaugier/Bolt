from __future__ import annotations

import html
import logging
import time
from typing import TYPE_CHECKING

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget

from bolt.ui import theme
from bolt.ui.views.base import View

if TYPE_CHECKING:
    from bolt.ui.workspace import Workspace

levels = {"Debug": logging.DEBUG, "Info": logging.INFO, "Warning": logging.WARNING, "Error": logging.ERROR}


def level_color(level: int) -> QColor:
    if level >= logging.ERROR:
        return theme.error

    if level >= logging.WARNING:
        return theme.warning

    if level >= logging.INFO:
        return theme.text

    return theme.muted


class _Handler(logging.Handler):
    def __init__(self, view: LogView) -> None:
        super().__init__(logging.DEBUG)
        self.view = view

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = record.getMessage()

            if record.exc_info:
                message += "\n" + logging.Formatter().formatException(record.exc_info)
        except Exception:
            message = str(record.msg)

        self.view.workspace.dispatcher.call_soon(lambda: self.view.append(record.levelno, record.created, message))


class LogView(View):
    view_type = "log"
    label = "Log"
    description = "Messages from nodes, cooks and plugins."

    def __init__(self, workspace: Workspace, parent: QWidget | None = None) -> None:
        super().__init__(workspace, parent)
        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        self.text.setMaximumBlockCount(5000)
        self.text.setFont(theme.monospace())
        self.level = QComboBox()
        self.level.addItems(list(levels))
        self.level.setCurrentText("Info")
        clear = QPushButton("Clear")
        clear.clicked.connect(self.text.clear)
        bar = QHBoxLayout()
        bar.addWidget(self.level)
        bar.addStretch(1)
        bar.addWidget(clear)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addLayout(bar)
        layout.addWidget(self.text)
        self.handler = _Handler(self)
        logging.getLogger("bolt").addHandler(self.handler)

    def append(self, level: int, created: float, message: str) -> None:
        if level < levels[self.level.currentText()]:
            return

        color = level_color(level).name()
        stamp = time.strftime("%H:%M:%S", time.localtime(created))
        body = html.escape(message).replace("\n", "<br>")

        self.text.appendHtml(f'<span style="color:{theme.muted.name()}">{stamp}</span> '
                             f'<span style="color:{color}">{body}</span>')

    def save_state(self) -> dict[str, str]:
        return {"level": self.level.currentText()}

    def restore_state(self, state: dict[str, str]) -> None:
        if state.get("level") in levels:
            self.level.setCurrentText(state["level"])

    def close_view(self) -> None:
        logging.getLogger("bolt").removeHandler(self.handler)
        super().close_view()
