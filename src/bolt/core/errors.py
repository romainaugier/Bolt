from __future__ import annotations


class BoltError(Exception):
    pass


class InvalidNameError(BoltError, ValueError):
    pass


class InvalidValueError(BoltError, ValueError):
    pass


class UnknownTypeError(BoltError, LookupError):
    pass


class UnknownNodeTypeError(BoltError, LookupError):
    pass


class RegistryError(BoltError):
    pass


class PluginError(BoltError):
    pass


class GraphError(BoltError):
    pass


class NodeNotFoundError(GraphError, LookupError):
    pass


class PlugNotFoundError(GraphError, LookupError):
    pass


class InvalidConnectionError(GraphError):
    pass


class GraphBusyError(GraphError):
    pass


class ExpressionError(BoltError):
    pass


class CookError(BoltError):
    pass


class Cancelled(BoltError):
    pass


class SerializationError(BoltError):
    pass
