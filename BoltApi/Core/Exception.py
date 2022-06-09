class BoltException(Exception):
    """Bolt Exception Class"""

class CompilationError(BoltException):
    """
    Raised when an error occurs during compilation
    of the op code of a node
    """