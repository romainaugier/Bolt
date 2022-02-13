from PyQt5 import QtCore, QtGui, QtWidgets


def CleanLayout(layout : QtWidgets.QLayout) -> None:
    """
    Deletes widgets and layouts recursively

    Args:
        layout (QtWidgets.QLayout): layout to clear
    """
    if layout.count() > 0:
        while layout.count():
            item = layout.itemAt(0)
            widget = item.widget()

            if widget is not None:
                widget.setParent(None)
            else:
                CleanLayout(item.layout())


def QColorToStyleSheet(foreground : QtGui.QColor = None, background : QtGui.QColor = None) -> str:
    """
    Returns a stylesheet string from the given color
    """
    styleSheetStr = ""
    
    if foreground is not None:
        styleSheetStr += f"color: rgb({foreground.red()}, {foreground.green()}, {foreground.blue()})"
    
    if background is not None:
        styleSheetStr += f"background-color: rgb({foreground.red()}, {foreground.green()}, {foreground.blue()})"

    return styleSheetStr