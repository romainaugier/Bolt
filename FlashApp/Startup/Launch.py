import os, sys, ctypes, platform

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from FlashApp import FLASHROOT

sys.path.append(FLASHROOT)

from PyQt5.QtWidgets import QApplication

from FlashApp.Interface.App import *

if __name__ == "__main__":
    app = QApplication(sys.argv[1:])

    appId = u"flash"
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(appId)

    # TODO : link with runtime path
    with open(f"{FLASHROOT}/Library/flash.style", "r") as file:
        stylesheet = file.read()

    win = App()
    win.setStyleSheet(stylesheet)
    # win.show()
    win.showMaximized()

    sys.exit(app.exec_())