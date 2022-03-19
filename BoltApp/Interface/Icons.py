import os

from PyQt5 import QtGui, QtCore

from BoltApp import BOLTROOT

class Icons():
    """
    """
    def __init__(self):
        """
        """
        # TODO : link with runtime path
        self.iconFolderPath = f"{BOLTROOT}/Library/Icons"

        self.icons = {}
        self.anims = {}
        self.pixmaps = {}

        allIcons = os.listdir(self.iconFolderPath)

        for icon in allIcons:
            name, ext = os.path.splitext(icon)
            path = os.path.join(self.iconFolderPath, icon)

            if "png" in ext:
                self.icons[name] = QtGui.QIcon(QtGui.QPixmap(path))
                self.pixmaps[name] = QtGui.QPixmap(path)
            elif "gif" in ext:
                self.anims[name] = QtGui.QMovie(path)

    def GetIcon(self, name : str) -> QtGui.QIcon:
        """
        """
        return self.icons[name]

    @staticmethod
    def LoadAndGetIcon(name : str, size : int = 18) -> QtGui.QIcon:
        """
        """
        iconFolderPath = f"{BOLTROOT}/Library/Icons"

        for icon in os.listdir(iconFolderPath):
            iconName, _ = os.path.splitext(icon)
            if name == iconName:
                return QtGui.QIcon(QtGui.QPixmap(f"{iconFolderPath}/{icon}").scaled(size, size))

    def AddPixmap(self, path : str) -> str:
        """
        Adds a pixmap to the pixmap library

        Args:
            path (str): path to the pixmap
        """
        pixname = os.path.splitext(os.path.basename(path))[0]

        if not pixname in self.pixmaps:
            self.pixmaps[pixname] = QtGui.QPixmap(path)
        
        return pixname

    def GetPixmap(self, name : str) -> QtGui.QPixmap:
        """
        Returns a QPixmap given a name

        Args:
            name (str): name of the pixmap

        Returns:
            QtGui.QPixmap: pixmap
        """
        return self.pixmaps[name]

    def GetColoredPixmap(self, name : str, color : QtGui.QColor) -> QtGui.QPixmap:
        """
        Returns a qpixmap given a name and a color to set the pixmap to (used
        to get the same black withicons with different colors)

        Args:
            name (str): pixmap name
            color (QtGui.QColor): new color

        Returns:
            QtGui.QPixmap: pixmap with the proper color applied
        """
        pixmap : QtGui.QPixmap = self.pixmaps[name]
        mask = pixmap.createMaskFromColor(QtGui.QColor(0, 0, 0), QtCore.Qt.MaskOutColor)

        newPixmap = QtGui.QPixmap(pixmap.size())
        newPixmap.fill(color)
        newPixmap.setMask(mask)
        return newPixmap   

    def GetAnim(self, name : str) -> QtGui.QMovie:
        """
        Returns a QMovie

        Args:
            name (str): name of the movie

        Returns:
            QtGui.QMovie: movie
        """
        return self.anims[name]