import os

from PyQt5 import QtGui


class Icons():
    """
    """
    def __init__(self):
        """
        """
        # TODO : link with runtime path
        self.iconFolderPath = "D:/dev/Flash/Library/Icons"

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

    def GetPixmap(self, name : str) -> QtGui.QPixmap:
        """
        Returns a QPixmap given a name

        Args:
            name (str): name of the pixmap

        Returns:
            QtGui.QPixmap: pixmap
        """
        return self.pixmaps[name]

    def GetAnim(self, name : str) -> QtGui.QMovie:
        """
        Returns a QMovie

        Args:
            name (str): name of the movie

        Returns:
            QtGui.QMovie: movie
        """
        return self.anims[name]