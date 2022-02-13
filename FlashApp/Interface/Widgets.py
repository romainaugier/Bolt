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