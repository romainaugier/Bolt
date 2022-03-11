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
    
    ##############################################
    
    GREENCOLOR = QtGui.QColor(195, 232, 141)
    YELLOWCOLOR = QtGui.QColor(255, 203, 107)
    BLUECOLOR = QtGui.QColor(130, 170, 255)
    REDCOLOR = QtGui.QColor(240, 113, 120)
    PURPLECOLOR = QtGui.QColor(199, 146, 234)
    ORANGECOLOR = QtGui.QColor(247, 140, 108)
    CYANCOLOR = QtGui.QColor(137, 221, 255)
    GRAYCOLOR = QtGui.QColor(113, 124, 180)
    WHITECOLOR = QtGui.QColor(238, 255, 255)
    REDERRORCOLOR = QtGui.QColor(255, 83, 112)
    
    ##############################################
    
    ERRORCOLOR = REDERRORCOLOR
    WARNINGCOLOR = YELLOWCOLOR
    DONECOLOR = GREENCOLOR
    
    ##############################################
    
    COMMENTSCOLOR = GRAYCOLOR
    VARIABLESCOLOR = WHITECOLOR
    LINKSCOLOR = QtGui.QColor(128, 203, 196)
    FUNCTIONSCOLOR = BLUECOLOR
    KEYWORDSCOLOR = PURPLECOLOR
    TAGSCOLOR = REDCOLOR
    STRINGSCOLOR = GREENCOLOR
    OPERATORSCOLOR = CYANCOLOR
    ATTRIBUTESCOLOR = YELLOWCOLOR
    NUMBERSCOLOR = ORANGECOLOR
    PARAMETERSCOLOR = ORANGECOLOR
    

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

PLUGEDITORSTYLE = """
QWidget {
    background-color: rgb(13, 14, 25);
}

QFrame {
    color: rgb(74, 82, 107);
}

QLabel {
    color: rgb(143, 144, 160);
    border-radius: 0px;
}

QCheckBox {
    border: none;
}

QCheckBox::indicator::unchecked {
    background-color: rgb(234, 66, 74);
}

QCheckBox::indicator::checked {
    background-color: rgb(195, 232, 141);
}

QLineEdit {
    color: rgba(234, 235, 255, 180);
    background-color: rgb(69, 74, 92);
    border: none;
    border-radius: 0px;
    selection-color: rgb(255, 255, 255);
    selection-background-color : rgb(64, 69, 102);
}

QPushButton {
    color: rgb(143, 144, 160);
    background-color: rgba(74, 82, 107, 63);
    height: 40;
    width: 40;
    qproperty-iconSize: 25px;
    border-radius: 4px;
}

QPushButton:hover:!pressed {
    color: rgb(143, 144, 160);
    background-color: rgba(74, 82, 107, 127);
}

QScrollBar:vertical {
    background-color: rgb(8, 8, 10);
    width: 10px;
    border: none;
}

QScrollBar::handle:vertical {
    background-color: rgb(69, 74, 92);
    width: 10px;
    border-radius: 5px;
}

QScrollBar::add-line:vertical
{
    margin: 0px 3px 0px 3px;
    border-image: url(:/qss_icons/rc/right_arrow_disabled.png);
    width: 10px;
    height: 10px;
    subcontrol-position: right;
    subcontrol-origin: margin;
}

QScrollBar::sub-line:vertical
{
    margin: 0px 3px 0px 3px;
    border-image: url(:/qss_icons/rc/left_arrow_disabled.png);
    height: 10px;
    width: 10px;
    subcontrol-position: left;
    subcontrol-origin: margin;
}

QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical
{
    background: none;
}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical
{
    background: none;
}
"""


CODEEDITORSTYLE = """
QPlainTextEdit{
    color: rgb(143, 144, 160);
    background-color: rgb(13, 14, 25);
}
"""


def GetQColorFromPalette(colorEnum : ColorPalette) -> QtGui.QColor:
    """
    """
    return QtGui.QColor(colorEnum.value)

def GetColorFromPalette(colorEnum : ColorPalette) -> list:
    """
    """
    qColor = QtGui.QColor(colorEnum.value)

    return [qColor.red(), qColor.green(), qColor.blue()]