from enum import Enum

from PyQt5 import QtGui, QtCore, QtWidgets

class ColorPalette(Enum):
    BACKGROUND = QtGui.QColor(13, 14, 25)
    FOREGROUND = QtGui.QColor(143, 144, 160)
    TEXT = QtGui.QColor(74, 82, 107)
    SELECTIONBACKGROUND = QtGui.QColor(64, 69, 102)
    SELECTIONFOREGROUND = QtGui.QColor(255, 255, 255)
    BUTTONS = QtGui.QColor(74, 82, 107)
    SECONDBACKGROUND = QtGui.QColor(3, 25, 28)
    DISABLED = QtGui.QColor(69, 74, 92)
    CONTRAST = QtGui.QColor(8, 8, 10)
    ACTIVE = QtGui.QColor(25, 25, 36)
    BORDER = QtGui.QColor(13, 15, 25)
    HIGHLIGHT = QtGui.QColor(30, 31, 51)
    TREE = QtGui.QColor(255, 255, 255)
    NOTIFICATIONS = QtGui.QColor(8, 8, 10)
    ACCENTCOLOR = QtGui.QColor(104, 240, 222)
    EXCLUDEDFILESCOLOR = QtGui.QColor(41, 43, 61)
    ERRORCOLOR: QtGui.QColor(234, 66, 74)


QMENUSTYLE = f"""
    QMenu {{
        background-color: rgb(13, 14, 25);
        border-radius: 20px;
    }}

    QMenu::item {{
        color: rgb(143, 144, 160);
        background-color: transparent;
    }}

    QMenu::item:selected {{
        color: rgb(255, 255, 255);
        background-color: rgb(64, 69, 102);
    }}
"""


def GetQColorFromPalette(colorEnum : ColorPalette) -> QtGui.QColor:
    """
    """
    return QtGui.QColor(colorEnum.value)

