import threading
import enum
import typing

from bolt.core.node import Node, NodeResult, NodeCookResult

class GraphResult(enum.IntEnum):
    Ok = 0
    Error = 1
    
class GraphCookResult():
    def __init__(self, result: GraphResult, message: str = None) -> None:
        self._result = result
        self._message = message
        
    @property
    def result(self) -> GraphResult:
        return self._result
    
    @property
    def message(self) -> str:
        return self._message

        
class GraphEventType(enum.IntEnum):
    CookStart = 0
    CookEnd = 1
    CookPaused = 2
    CookResumed = 3
    CookError = 4


class Graph():
    def __init__(self, name: str = None) -> None:
        self._name = name

        self._nodes = list()
        self._sorted_nodes = list()

        self._lock = threading.Lock()
        self._event = threading.Event()

        self._callbacks = {key: list() for key in GraphEventType._value2member_map_.keys()}

    @property
    def name(self) -> str:
        return self._name
    
    @name.setter 
    def name(self, name: str) -> None:
        self._name = name

    @property
    def nodes(self) -> typing.List[Node]:
        return self._nodes

    @property
    def sorted_nodes(self) -> typing.List[Node]:
        return self._sorted_nodes

    # Callbacks
    
    def push_event_callback(self, callbackEventType: GraphEventType, callback: typing.Callable) -> None:
        self._callbacks[callbackEventType].append(callback)

    def pop_event_callback(self, callbackEventType: GraphEventType) -> typing.Callable:
        return self._callbacks[callbackEventType].pop()

    # Nodes

    def get_node_from_name(self, node_name: str) -> Node:
        for node in self.nodes:
            if node.name == node_name:
                return node

        return None
    
    def create_node(self, nodeType: str) -> None:
        self._nodes.append(node)

    def remove_node(self, node_name: str) -> None:
        pass

    # Sort and traversal