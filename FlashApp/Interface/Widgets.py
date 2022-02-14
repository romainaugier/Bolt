import os

from PyQt5 import QtCore, QtGui, QtWidgets


class QHLine(QtWidgets.QFrame):
    def __init__(self):
        super().__init__()
        self.setMinimumWidth(1)
        self.setFixedHeight(10)
        self.setLineWidth(2)
        self.setFrameShape(QtWidgets.QFrame.HLine)
        self.setFrameShadow(QtWidgets.QFrame.Plain)
        self.setContentsMargins(0, 0, 0, 0)
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Minimum)

    def setColor(self, color : QtGui.QColor):
        pal = self.palette()
        pal.setColor(QtGui.QPalette.WindowText, color)
        self.setPalette(pal)
    

class QVLine(QtWidgets.QFrame):
    def __init__(self):
        super().__init__()
        self.setFixedWidth(10)
        self.setMinimumHeight(1)
        self.setLineWidth(2)
        self.setFrameShape(QtWidgets.QFrame.VLine)
        self.setFrameShadow(QtWidgets.QFrame.Plain)
        self.setContentsMargins(0, 0, 0, 0)
        self.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)
        
    def setColor(self, color : QtGui.QColor):
        pal = self.palette()
        pal.setColor(QtGui.QPalette.WindowText, color)
        self.setPalette(pal)


class IconLabel(QtWidgets.QWidget):
    """
    """

    IconSize = QtCore.QSize(20, 20)
    HSpacing = 10

    def __init__(self, pixmap : QtGui.QPixmap, text : str, finalStretch : bool = True):
        """
        """
        super(QtWidgets.QWidget, self).__init__()

        self.mainLayout = QtWidgets.QHBoxLayout()
        self.mainLayout.setSpacing(0)
        self.mainLayout.setAlignment(QtCore.Qt.AlignLeft)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(self.mainLayout)
        
        if pixmap is not None:
            self.icon = QtWidgets.QLabel()
            self.mainLayout.addWidget(self.icon)
            self.icon.setPixmap(pixmap.scaled(self.IconSize))
            self.spacer = QtWidgets.QSpacerItem(self.HSpacing, 0)
            self.mainLayout.addSpacerItem(self.spacer)
        else:
            self.icon = None
            self.spacer = None

        self.text = QtWidgets.QLabel(text)
        self.text.setFont(QtGui.QFont("Helvetica", 14))
        self.text.setStyleSheet("color: rgb(143, 144, 160)")
        self.mainLayout.addWidget(self.text)

    def setText(self, text : str) -> None:
        """
        """
        self.text.setText(text)

    def setIcon(self, pixmap = QtGui.QPixmap) -> None:
        """
        """
        text = self.text.text()

        self.text.setParent(None)

        if self.icon is not None:
            self.icon.setParent(None)

        if self.spacer is not None:
            self.mainLayout.removeItem(self.spacer)

        if pixmap is not None:
            self.icon = QtWidgets.QLabel()
            self.mainLayout.addWidget(self.icon)
            self.icon.setPixmap(pixmap.scaled(self.IconSize))
            self.spacer = QtWidgets.QSpacerItem(self.HSpacing, 0)
            self.mainLayout.addSpacerItem(self.spacer)
        else:
            self.icon = None
            self.spacer = None

        self.text = QtWidgets.QLabel(text)
        self.text.setFont(QtGui.QFont("Helvetica", 14))
        self.text.setStyleSheet("color: rgb(143, 144, 160)")
        self.mainLayout.addWidget(self.text)

    def setIconSize(self, size : int):
        """
        """
        self.IconSize = QtCore.QSize(size, size)

    def setFont(self, fontName : str, fontSize : int, color : list):
        """
        """
        self.text.setFont(QtGui.QFont(fontName, fontSize))
        self.text.setStyleSheet(f"color: rgb({color[0]}, {color[1]}, {color[2]})")

class ContextMenu(QtWidgets.QMenu):
    """
    """
    def __init__(self, parent=None):
        """
        """
        super(ContextMenu, self).__init__()

        self.radius = 5

        self.setStyleSheet("""
    QMenu {
        background-color: rgb(13, 14, 25);
        border-radius: 20px;
    }

    QMenu::item {
        color: rgb(143, 144, 160);
        background-color: transparent;
    }

    QMenu::item:selected {
        color: rgb(255, 255, 255);
        background-color: rgb(64, 69, 102);
    }
""")

    # https://stackoverflow.com/questions/65574567/rounded-corners-for-qmenu-in-pyqt
    def resizeEvent(self, event):
        """
        """
        path = QtGui.QPainterPath()
        # the rectangle must be translated and adjusted by 1 pixel in order to 
        # correctly map the rounded shape
        rect = QtCore.QRectF(self.rect()).adjusted(.5, .5, -1.5, -1.5)
        path.addRoundedRect(rect, self.radius, self.radius)
        # QRegion is bitmap based, so the returned QPolygonF (which uses float
        # values must be transformed to an integer based QPolygon
        region = QtGui.QRegion(path.toFillPolygon(QtGui.QTransform()).toPolygon())
        self.setMask(region)


class LineEdit(QtWidgets.QLineEdit):
    """
    """

    def __init__(self, parent=None):
        """
        """
        super(LineEdit, self).__init__(parent)

        self.setAcceptDrops(True)
        
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls:
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls:
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls:
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()

            for url in event.mimeData().urls():
                itemPath = url.toLocalFile()
                
                if os.path.isfile(itemPath):
                    self.setText(itemPath)
                    self.editingFinished.emit()
        else:
            event.ignore()