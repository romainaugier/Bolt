from FlashApi.Core.Logger import *
from FlashApp.Interface.Style import *
from FlashApp.Interface.Widgets import *
from FlashApp.Interface.Icons import *

from PyQt5 import QtCore, QtGui, QtWidgets

class ConsoleLineEdit(QtWidgets.QLineEdit):
    """
    """
    def __init__(self, parent=None) -> None:
        """
        """
        super().__init__(parent=parent)

        self.backGroundColor = GetColorFromPalette(ColorPalette.CONTRAST)
        self.textColor = GetColorFromPalette(ColorPalette.TEXT)

        self.setTextColor(self.textColor)

    def setTextColor(self, color : list) -> None:
        """
        """
        self.setStyleSheet(f"""
        color : rgb({color[0]}, {color[1]}, {color[2]});
        background-color : rgb({self.backGroundColor[0]}, {self.backGroundColor[1]}, {self.backGroundColor[2]})
        """)


class Console(QtWidgets.QWidget):
    """
    """

    newMessageLogged = QtCore.pyqtSignal()
    newMessageSubmitted = QtCore.pyqtSignal()

    def __init__(self, iconsLib : Icons, parent=None):
        """
        """
        super().__init__(parent=parent)

        self.iconsLib = iconsLib

        self.messageQueue = []

        self.masterLayout = QtWidgets.QHBoxLayout()
        self.masterLayout.setSpacing(0)
        self.masterLayout.setAlignment(QtCore.Qt.AlignLeft)
        self.masterLayout.setContentsMargins(0, 0, 0, 0)

        icon = self.iconsLib.GetColoredPixmap("badge-message", GetQColorFromPalette(ColorPalette.TEXT))
        self.messageIcon = QtWidgets.QLabel()
        self.messageIcon.setPixmap(icon.scaled(24, 24))

        self.masterLayout.addWidget(self.messageIcon)

        self.masterLayout.addSpacing(10)

        self.messageDisplay = ConsoleLineEdit()
        self.messageDisplay.setFixedHeight(20)
        self.messageDisplay.setFont(QtGui.QFont("Helvetica", 8))

        self.masterLayout.addWidget(self.messageDisplay)

        self.setLayout(self.masterLayout)

        self.newMessageSubmitted.connect(self.updateDisplay)

    def log(self, level : LogLevel, message : str) -> None:
        """
        """
        self.messageQueue.append((level, message))

        self.newMessageSubmitted.emit()

    def displayMessage(self) -> None:
        """
        """
        level, message = self.messageQueue.pop()

        if level == LogLevel.ERROR:
            self.messageDisplay.setTextColor(GetColorFromPalette(ColorPalette.ERRORCOLOR))
        elif level == LogLevel.WARNING:
            self.messageDisplay.setTextColor(GetColorFromPalette(ColorPalette.WARNINGCOLOR))
        else:
            self.messageDisplay.setTextColor(GetColorFromPalette(ColorPalette.TEXT))

        self.messageDisplay.setText(message)
        self.messageDisplay.text

        self.newMessageLogged.emit() 

    def updateDisplay(self) -> None:
        """
        """
        self.displayMessage()

    def reset(self) -> None:
        """
        """
        self.messageDisplay.setText("")
