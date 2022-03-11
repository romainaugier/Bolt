from asyncio.windows_events import CONNECT_PIPE_INIT_DELAY
import os

from PyQt5 import QtCore, QtGui, QtWidgets


# Line Separators


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


# Label with Icon


class IconLabel(QtWidgets.QWidget):
    """
    """

    IconSize = QtCore.QSize(24, 24)
    HSpacing = 10

    def __init__(self, pixmap : QtGui.QPixmap, text : str, font : QtGui.QFont = QtGui.QFont("Helvetica", 14), finalStretch : bool = True):
        """
        """
        super(QtWidgets.QWidget, self).__init__()

        self.mainLayout = QtWidgets.QHBoxLayout()
        self.mainLayout.setSpacing(0)
        self.mainLayout.setAlignment(QtCore.Qt.AlignLeft)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)

        if pixmap is not None:
            self.icon = QtWidgets.QLabel()
            self.mainLayout.addWidget(self.icon)
            self.icon.setPixmap(pixmap.scaled(self.IconSize, QtCore.Qt.IgnoreAspectRatio, QtCore.Qt.SmoothTransformation))
            self.spacer = QtWidgets.QSpacerItem(self.HSpacing, 0)
            self.mainLayout.addSpacerItem(self.spacer)
        else:
            self.icon = None
            self.spacer = None

        self.text = QtWidgets.QLabel(text)

        self._font = font

        self.text.setFont(self._font)
        self.text.setStyleSheet("color: rgb(143, 144, 160)")
        self.mainLayout.addWidget(self.text)
        
        self.setLayout(self.mainLayout)

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
            self.icon.setPixmap(pixmap.scaled(self.IconSize, QtCore.Qt.IgnoreAspectRatio, QtCore.Qt.SmoothTransformation))
            self.spacer = QtWidgets.QSpacerItem(self.HSpacing, 0)
            self.mainLayout.addSpacerItem(self.spacer)
        else:   
            self.icon = None
            self.spacer = None

        self.text = QtWidgets.QLabel(text)
        self.text.setFont(self._font)
        self.text.setStyleSheet("color: rgb(143, 144, 160)")
        self.mainLayout.addWidget(self.text)

    def setIconSize(self, size : int):
        """
        """
        self.IconSize = QtCore.QSize(size, size)

    def setFont(self, fontName : str, fontSize : int, color : list):
        """
        """
        self._font = QtGui.QFont(fontName, fontSize)
        self.text.setFont(self._font)
        self.text.setStyleSheet(f"color: rgb({color[0]}, {color[1]}, {color[2]})")

    def setTextColor(self, color : list) -> None:
        """
        """
        self.text.setStyleSheet(f"color: rgb({color[0]}, {color[1]}, {color[2]})")


# Context Menu


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


# Line Edit with drag event


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
            
            
# Labeled Widgets

        
class LabeledLineEdit(QtWidgets.QWidget):
    """
    """
    def __init__(self, labelText : str, defaultText : str = "", parent = None) -> None:
        super().__init__(parent=parent)

        self.mainLayout = QtWidgets.QHBoxLayout()
        self.mainLayout.setSpacing(0)
        self.mainLayout.setAlignment(QtCore.Qt.AlignLeft)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        
        self.mainLabel = QtWidgets.QLabel(labelText)
        self.mainLayout.addWidget(self.mainLabel)
        
        self.mainLayout.addSpacing(20)
        
        self.mainLineEdit = LineEdit()
        self.mainLineEdit.setText(defaultText)
        self.mainLayout.addWidget(self.mainLineEdit)
        
        self.setLayout(self.mainLayout)
        
    def getLabel(self) -> QtWidgets.QLabel:
        """
        """
        return self.mainLabel
    
    def getLineEdit(self) -> LineEdit:
        """
        """
        return self.mainLineEdit


class LabeledComboBox(QtWidgets.QWidget):
    """
    """
    def __init__(self, labelText : str, stretch : bool = True, parent = None) -> None:
        super().__init__(parent=parent)

        self.mainLayout = QtWidgets.QHBoxLayout()
        self.mainLayout.setSpacing(0)
        self.mainLayout.setAlignment(QtCore.Qt.AlignLeft)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        
        self.mainLabel = QtWidgets.QLabel(labelText)
        self.mainLayout.addWidget(self.mainLabel)
        
        if stretch: 
            self.mainLayout.addStretch()
        
        self.mainComboBox = QtWidgets.QComboBox()
        self.mainLayout.addWidget(self.mainComboBox)
        
        self.setLayout(self.mainLayout)
        
    def getLabel(self) -> QtWidgets.QLabel:
        """
        """
        return self.mainLabel
    
    def getComboBox(self) -> QtWidgets.QComboBox:
        """
        """
        return self.mainComboBox


class LabeledCheckBox(QtWidgets.QWidget):
    """
    """
    def __init__(self, labelText : str, stretch : bool = True, parent = None) -> None:
        super().__init__(parent=parent)

        self.mainLayout = QtWidgets.QHBoxLayout()
        self.mainLayout.setSpacing(0)
        self.mainLayout.setAlignment(QtCore.Qt.AlignLeft)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        
        self.mainLabel = QtWidgets.QLabel(labelText)
        self.mainLayout.addWidget(self.mainLabel)
        
        if stretch:
            self.mainLayout.addStretch()
        
        self.mainCheckBox = QtWidgets.QCheckBox()
        self.mainLayout.addWidget(self.mainCheckBox)
        
        self.setLayout(self.mainLayout)
        
    def getLabel(self) -> QtWidgets.QLabel:
        """
        """
        return self.mainLabel
    
    def getCheckBox(self) -> QtWidgets.QCheckBox:
        """
        """
        return self.mainCheckBox
    
    
# Python Code Editor


class LineNumberArea(QtWidgets.QWidget):
    """
    """
    def __init__(self, editor):
        """
        """
        super().__init__(editor)
        
        self.editor = editor
        
    def sizeHint(self):
        """
        """
        return QtCore.QSize(self.editor.lineNumberAreaWidth(), 0)
    
    def paintEvent(self, event : QtCore.QEvent) -> None:
        """
        """
        self.editor.lineNumberAreaPaintEvent(event)
        
        
def Format(color : QtGui.QColor, style = "") -> QtGui.QTextCharFormat:
    """
    """
    fmt = QtGui.QTextCharFormat()
    fmt.setForeground(color)
    
    return fmt


class PySyntaxHighlighter(QtGui.QSyntaxHighlighter):
    """
    """
    keywords = [
        'and', 'assert', 'break', 'class', 'continue', 'def',
        'del', 'elif', 'else', 'except', 'exec', 'finally',
        'for', 'from', 'global', 'if', 'import', 'in',
        'is', 'lambda', 'not', 'or', 'pass', 'print',
        'raise', 'return', 'try', 'while', 'yield',
        'None', 'True', 'False'
    ]
    
    operators = [
        '=',
        '==', '!=', '<', '<=', '>', '>=',
        '\+', '-', '\*', '/', '//', '\%', '\*\*',
        '\+=', '-=', '\*=', '/=', '\%=',
        '\^', '\|', '\&', '\~', '>>', '<<'
    ]
    
    braces = [
        '\{', '\}', '\(', '\)', '\[', '\]',
    ]
    
    def __init__(self, parent : QtGui.QTextDocument, style : dict = None) -> None:
        """
        """
        super().__init__(parent)
        
        # Multi lines strings
        self.triSingle = (QtCore.QRegExp("'''"), 1, style["string"])
        self.triDouble = (QtCore.QRegExp("\"\"\""), 2, style["string"])
        
        rules = []
        
        # keyword, operators and braces
        rules += [(fr"\b{keyword}\b", 0, style["keyword"]) for keyword in self.keywords]
        rules += [(fr"{operator}", 0, style["operator"]) for operator in self.operators]
        rules += [(fr"{brace}", 0, style["brace"]) for brace in self.braces]
        
        rules += [
            # 'self'
            (r'\bself\b', 0, style["self"]),

            # 'def' followed by an identifier
            (r'\bdef\b\s*(\w+)', 1, style["defclass"]),
            # 'class' followed by an identifier
            (r'\bclass\b\s*(\w+)', 1, style["defclass"]),

            # Numeric literals
            (r'\b[+-]?[0-9]+[lL]?\b', 0, style["numbers"]),
            (r'\b[+-]?0[xX][0-9A-Fa-f]+[lL]?\b', 0, style["numbers"]),
            (r'\b[+-]?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\b', 0, style["numbers"]),

            # Double-quoted string, possibly containing escape sequences
            (r'"[^"\\]*(\\.[^"\\]*)*"', 0, style["string"]),
            # Single-quoted string, possibly containing escape sequences
            (r"'[^'\\]*(\\.[^'\\]*)*'", 0, style["string"]),

            # From '#' until a newline
            (r'#[^\n]*', 0, style["comment"]),
        ]
        
        self.rules = [(QtCore.QRegExp(pattern), index, format) for (pattern, index, format) in rules]
        
    def highlightBlock(self, text) -> None:
        """
        """
        self.tripleQuotesWithinStrings = []
        
        for expression, nth, format in self.rules:
            index = expression.indexIn(text, 0)
            
            if index >= 0:
                if expression.pattern() in [r'"[^"\\]*(\\.[^"\\]*)*"', r"'[^'\\]*(\\.[^'\\]*)*'"]:
                    innerIndex = self.triSingle[0].indexIn(text, index + 1)
                    
                    if innerIndex == -1:
                        innerIndex = self.triDouble[0].indexIn(text, index + 1)
                        
                    if innerIndex != -1:
                        tripleQuoteIndexes = range(innerIndex, innerIndex + 3)
                        self.tripleQuotesWithinStrings.extend(tripleQuoteIndexes)
                        
            while index >= 0:
                if index in self.tripleQuotesWithinStrings:
                    index += 1
                    expression.indexIn(text, index)
                    continue
                
                index = expression.pos(nth)
                length = len(expression.cap(nth))
                self.setFormat(index, length, format)
                index = expression.indexIn(text, index + length)
                
        self.setCurrentBlockState(0)
        
        inMultiline = self.matchMultiline(text, *self.triSingle)
        
        if not inMultiline:
            inMultiline = self.matchMultiline(text, *self.triDouble)
            
    def matchMultiline(self, text, delimiter, inState, style):
        """
        """
        if self.previousBlockState() == inState:
            start = 0
            add = 0
        else:
            start = delimiter.indexIn(text)
            
            if start in self.tripleQuotesWithinStrings:
                return False
            
            add = delimiter.matchedLength()
            
        while start >= 0:
            end = delimiter.indexIn(text, start + add)
            
            if end >= add:
                length = end - start + add + delimiter.matchedLength()
                self.setCurrentBlockState(0)
            else:
                self.setCurrentBlockState(inState)
                length = len(text) - start + add
            
            self.setFormat(start, length, style)
            
            start = delimiter.indexIn(text, start + length)
            
        if self.currentBlockState() == inState:
            return True
        else:
            return False


class PyCodeEditor(QtWidgets.QPlainTextEdit):
    """
    """
    def __init__(self, highlightStyle : dict, font : QtGui.QFont) -> None:
        """
        """
        super().__init__()
        
        self.lineNumberArea = LineNumberArea(self)
        
        self.highligther = PySyntaxHighlighter(self.document(), highlightStyle)
        
        self.lineHighlightColor = QtGui.QColor(QtCore.Qt.yellow).lighter(160)
        self.lineIndicesBgColor= QtCore.Qt.lightGray
        self.lineIndicesTextColor = QtCore.Qt.black
        
        self._font = font
        self.setFont(self._font)
        
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        
        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.updateRequest.connect(self.updateLineNumberArea)
        self.cursorPositionChanged.connect(lambda: (self.highlightCurrentLine(), self.ensureCursorVisible()))
        
        self.setCenterOnScroll(True)
        self.updateLineNumberAreaWidth(0)
        
    def setLineHighlightColor(self, color : QtGui.QColor) -> None:
        """
        """
        self.lineHighlightColor = color
    
    def setLineIndicesBgColor(self, color : QtGui.QColor) -> None:
        """
        """
        self.lineIndicesBgColor= color
    
    def setLineIndicesTextColor(self, color : QtGui.QColor) -> None:
        """
        """
        self.lineIndicesTextColor = color
        
    def lineNumberAreaWidth(self) -> int:
        """
        """
        digits = 3
        count = max(1, self.blockCount())
        
        while count >= 1000:
            count /= 10
            digits += 1
            
        space = 3 + self.fontMetrics().width('9') * digits
        
        return space
    
    @QtCore.pyqtSlot(int)
    def updateLineNumberAreaWidth(self, _) -> None:
        """
        """
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)
        
    @QtCore.pyqtSlot(QtCore.QRect, int)
    def updateLineNumberArea(self, rect : QtCore.QRect, dy : int) -> None:
        """
        """
        if dy:
            self.lineNumberArea.scroll(0, dy)
        else:
            self.lineNumberArea.update(0, rect.y(), self.lineNumberArea.width(), rect.height())
            
        if rect.contains(self.viewport().rect()):
            self.updateLineNumberAreaWidth(0)
        
    def lineNumberAreaPaintEvent(self, event : QtCore.QEvent) -> None:
        """
        """
        painter = QtGui.QPainter(self.lineNumberArea)
        painter.fillRect(event.rect(), self.lineIndicesBgColor)
        
        block = self.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()
        
        height = self.fontMetrics().height()
        
        while block.isValid() and (top <= event.rect().bottom()):
            if block.isVisible() and (bottom >= event.rect().top()):
                number = str(blockNumber + 1)
                
                painter.setPen(self.lineIndicesTextColor)
                painter.setFont(self._font)
                painter.drawText(0, top, self.lineNumberArea.width(), height, QtCore.Qt.AlignRight, number)
                
            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            blockNumber += 1
            
    def highlightCurrentLine(self):
        extraSelections = []
        
        if not self.isReadOnly():
            selection = QtWidgets.QTextEdit.ExtraSelection()
            
            lineColor = self
            
            selection.format.setBackground(self.lineHighlightColor)
            selection.format.setProperty(QtGui.QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extraSelections.append(selection)
            
        self.setExtraSelections(extraSelections)
            
    # EVENTS
            
    def resizeEvent(self, event : QtCore.QEvent) -> None:
        """
        """
        super().resizeEvent(event)
        
        cr = self.contentsRect()
        
        self.lineNumberArea.setGeometry(QtCore.QRect(cr.left(), cr.top(), 
                                                     self.lineNumberAreaWidth(), cr.height()))
        
    def keyPressEvent(self, event : QtCore.QEvent):
        """
        """
        if event.key() == QtCore.Qt.Key_Tab:
            cursor = self.textCursor()
            cursor.insertText("    ")
            return
        
        return super().keyPressEvent(event)