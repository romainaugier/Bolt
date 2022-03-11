import os, sys, ctypes, platform

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from BoltApp import BOLTROOT

sys.path.append(BOLTROOT)

from PyQt5.QtWidgets import QApplication

from BoltApp.Interface.App import *

if __name__ == "__main__":
    app = QApplication(sys.argv[1:])

    appId = u"bolt"
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(appId)

    # TODO : link with runtime path
    with open(f"{BOLTROOT}/Library/bolt.style", "r") as file:
        stylesheet = file.read()

    win = App()
    win.setStyleSheet(stylesheet)
    # win.show()
    win.showMaximized()

    sys.exit(app.exec_())