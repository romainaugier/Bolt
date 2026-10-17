import time

from PySide6.QtWidgets import QApplication


def wait_until(predicate, timeout=5.0):
    deadline = time.monotonic() + timeout
    application = QApplication.instance()
    while time.monotonic() < deadline:
        application.processEvents()
        if predicate():
            return True
        time.sleep(0.005)
    application.processEvents()
    return predicate()


def pump(duration=0.05):
    wait_until(lambda: False, duration)
