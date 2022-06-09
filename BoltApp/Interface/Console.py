from BoltApi.Core.Logger import *
from BoltApp.Interface.Style import *
from BoltApp.Interface.Widgets import *
from BoltApp.Interface.Icons import *

from PyQt5 import QtCore, QtGui, QtWidgets

from collections import deque

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


class ConsoleLabel(QtWidgets.QLineEdit):
    """
    """
    def __init__(self, parent=None) -> None:
        """
        """
        super().__init__(parent=parent)

        self.backGroundColor = GetColorFromPalette(ColorPalette.BACKGROUND)
        self.textColor = GetColorFromPalette(ColorPalette.FOREGROUND)

        self.setTextColor(self.textColor)

    def setTextColor(self, color : list) -> None:
        """
        """
        self.setStyleSheet(f"""
        color : rgb({color[0]}, {color[1]}, {color[2]});
        background-color : rgb({self.backGroundColor[0]}, {self.backGroundColor[1]}, {self.backGroundColor[2]})
        """)


class LineConsole(QtWidgets.QWidget):
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

        # self.masterLayout.addWidget(self.messageIcon)

        self.masterLayout.addSpacing(10)

        self.messageDisplay = ConsoleLabel()
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
        elif level == LogLevel.DIAGNOSTIC:
            self.messageDisplay.setTextColor(GetColorFromPalette(ColorPalette.GREENCOLOR))
        else:
            self.messageDisplay.setTextColor(GetColorFromPalette(ColorPalette.FOREGROUND))

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
        
        
class ConsoleHighligher(QtGui.QSyntaxHighlighter):
    """
    Simple syntax highlighter for the console
    """
    def __init__(self, parent=None):
        """
        """
        super().__init__(parent=parent)
        
        self.messageFmt = QtGui.QTextCharFormat()
        self.messageFmt.setForeground(GetQColorFromPalette(ColorPalette.FOREGROUND))
        
        self.warningFmt = QtGui.QTextCharFormat()
        self.warningFmt.setForeground(GetColorFromPalette(ColorPalette.WARNINGCOLOR))
        
        self.errorFmt = QtGui.QTextCharFormat()
        self.errorFmt.setForeground(GetColorFromPalette(ColorPalette.ERRORCOLOR))
        
        self.messageFmt = QtGui.QTextCharFormat()
        self.messageFmt.setForeground(GetColorFromPalette(ColorPalette.FOREGROUND))
        
        self.diagnosticFmt = QtGui.QTextCharFormat()
        self.diagnosticFmt.setForeground(GetQColorFromPalette(ColorPalette.GREENCOLOR))
        
    def highlightBlock(self, text):
        if "ERROR" in text:
            self.setFormat(0, len(text), self.errorFmt)
        elif "WARNING" in text:
            self.setFormat(0, len(text), self.warningFmt)
        elif "MESSAGE" in text:
            self.setFormat(0, len(text), self.messageFmt)
        elif "DIAGNOSTIC" in text:
            self.setFormat(0, len(text), self.diagnosticFmt)
        

class Console(QtWidgets.QWidget):
    """
    Simple console to log everything happening in the application
    """
    pass