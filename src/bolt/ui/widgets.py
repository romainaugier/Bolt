from __future__ import annotations

from typing import Any

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QKeyEvent, QMouseEvent, QPainter, QWheelEvent
from PySide6.QtWidgets import QWidget

from bolt.ui import theme
from bolt.ui.qt import RepaintScheduler


class ImageCanvas(QWidget):
    """Shows an image that another thread may keep writing into.

    Give it a buffer once with set_buffer(), let your worker write pixels into that buffer and call request_update()
    from any thread: repaints are coalesced to the display rate and wrap the buffer without copying it.
    Wheel zooms, middle button (or Alt+left) pans, F fits, 1 shows pixels at 100%."""

    def __init__(self, parent: QWidget | None = None, max_fps: int = 60) -> None:
        super().__init__(parent)

        self.setFocusPolicy(Qt.StrongFocus)
        self.setMinimumSize(64, 64)
        self.overlay = ""
        self._source: tuple[Any, int, int, int, QImage.Format] | None = None
        self._image: QImage | None = None
        self._zoom = 1.0
        self._center = QPointF(0, 0)
        self._fit = True
        self._pan: QPointF | None = None
        self._repaint = RepaintScheduler(self, max_fps)

    def set_image(self, image: QImage | None) -> None:
        self._image = image
        self._source = None

        self.request_update()

    def set_buffer(self, buffer: Any, width: int, height: int,
                   image_format: QImage.Format = QImage.Format_RGBA8888, bytes_per_line: int | None = None) -> None:
        line = bytes_per_line if bytes_per_line is not None else width * 4

        self._source = (buffer, width, height, line, image_format)
        self._image = None

        self.request_update()

    def request_update(self) -> None:
        self._repaint.request()

    def image_size(self) -> tuple[int, int] | None:
        if self._source is not None:
            return self._source[1], self._source[2]

        if self._image is not None and not self._image.isNull():
            return self._image.width(), self._image.height()

        return None

    def fit(self) -> None:
        self._fit = True
        self.update()

    def actual_size(self) -> None:
        self._fit = False
        self._zoom = 1.0
        self._center = QPointF(0, 0)
        self.update()

    def paintEvent(self, event: Any) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), theme.base)
        image = self._current_image()

        if image is not None:
            target = self._target_rect(image.width(), image.height())
            self._checker(painter, target)
            painter.setRenderHint(QPainter.SmoothPixmapTransform, target.width() < image.width())
            painter.drawImage(target, image)

        if self.overlay:
            painter.setPen(theme.text)
            painter.drawText(self.rect().adjusted(8, 8, -8, -8), Qt.AlignLeft | Qt.AlignBottom, self.overlay)

        painter.end()

    def wheelEvent(self, event: QWheelEvent) -> None:
        size = self.image_size()

        if size is None:
            return

        if self._fit:
            self._zoom = self._fit_zoom(*size)
            self._fit = False

        factor = 1.0015 ** event.angleDelta().y()
        cursor = event.position() - QPointF(self.width() / 2, self.height() / 2)
        before = (cursor - self._center) / self._zoom

        self._zoom = min(max(self._zoom * factor, 0.02), 64.0)
        self._center = cursor - before * self._zoom
        self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MiddleButton or (event.button() == Qt.LeftButton
                                                 and event.modifiers() & Qt.AltModifier):
            if self._fit and self.image_size() is not None:
                self._zoom = self._fit_zoom(*self.image_size())
                self._fit = False

            self._pan = event.position()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._pan is not None:
            self._center += event.position() - self._pan
            self._pan = event.position()
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._pan = None

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key_F:
            self.fit()
        elif event.key() == Qt.Key_1:
            self.actual_size()
        else:
            super().keyPressEvent(event)

    def _current_image(self) -> QImage | None:
        if self._source is not None:
            buffer, width, height, line, image_format = self._source

            return QImage(buffer, width, height, line, image_format)

        return self._image

    def _fit_zoom(self, width: int, height: int) -> float:
        return min(max(self.width() - 16, 1) / width, max(self.height() - 16, 1) / height)

    def _target_rect(self, width: int, height: int) -> QRectF:
        zoom = self._fit_zoom(width, height) if self._fit else self._zoom
        center = QPointF(self.width() / 2, self.height() / 2) + (QPointF(0, 0) if self._fit else self._center)

        return QRectF(center.x() - width * zoom / 2, center.y() - height * zoom / 2, width * zoom, height * zoom)

    @staticmethod
    def _checker(painter: QPainter, rect: QRectF) -> None:
        painter.save()
        painter.setClipRect(rect)
        painter.fillRect(rect, QColor("#2a2a2a"))

        step = 12
        dark = QColor("#232323")
        y = int(rect.top())
        row = 0

        while y < rect.bottom():
            x = int(rect.left()) + (step if row % 2 else 0)

            while x < rect.right():
                painter.fillRect(x, y, step, step, dark)
                x += step * 2

            y += step
            row += 1

        painter.restore()
