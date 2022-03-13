from PyQt5 import QtCore, QtGui, QtWidgets

class JobsQueue(QtWidgets.QWidget):
    """
    The Jobs Queue widget holds the Job System enabling the user to submit new graph jobs, have a look at the different
    jobs running, and pause/resume some jobs
    
    Multiple JobsQueue widget can be opened but they will display the same thing as there is only one job system available
    """
    def __init__(self, parent=None):
        """
        """
        super().__init__(parent=parent)