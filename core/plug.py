from __future__ import annotations

from enum import IntEnum
from typing import Any, List

class PlugWarning(Exception):
    pass

class PlugError(Exception):
    pass

class PlugType(IntEnum):
    INT = 0
    FLOAT = 1
    STR = 2
    BOOL = 3
    LIST = 4
    DICT = 5
    CUSTOM = 6

def plug_type_to_str(plug_type: PlugType) -> str:
    if plug_type == PlugType.INT:
        return "int"
    if plug_type == PlugType.FLOAT:
        return "float"
    if plug_type == PlugType.STR:
        return "str"
    if plug_type == PlugType.BOOL:
        return "bool"
    if plug_type == PlugType.LIST:
        return "list"
    if plug_type == PlugType.LIST:
        return "dict"

    return "custom"

def plug_type_from_str(plug_type_as_str: str) -> PlugType:
    if plug_type_as_str == "int":
        return PlugType.INT
    if plug_type_as_str == "float":
        return PlugType.FLOAT
    if plug_type_as_str == "str":
        return PlugType.STR
    if plug_type_as_str == "bool":
        return PlugType.BOOL
    if plug_type_as_str == "list":
        return PlugType.LIST
    if plug_type_as_str == "dict":
        return PlugType.DICT

    return PlugType.CUSTOM

class PlugMode(IntEnum):
    PLUG = 0
    PARAMETER = 1
    GRAPH_PARAMETER = 2

class Plug():
    def __init__(self,
                 short_name: str,
                 long_name: str,
                 parent_node: Node,
                 data: Any = None,
                 default_data: Any = None,
                 data_type: PlugType = PlugType.CUSTOM,
                 mode: PlugMode = PlugMode.PLUG) -> None:
        self._short_name = short_name
        self._long_name = long_name

        self._parent_node = parent_node

        self._data = data
        self._default_data = default_data
        self._data_type = data_type

        self._mode = mode

        self._connections = list()

    @property
    def short_name(self) -> str:
        return self._short_name

    @property
    def long_name(self) -> str:
        return self._long_name

    @property
    def parent_node(self) -> Node:
        return self._parent_node

    @property
    def data(self) -> Any:
        return self._data

    @data.setter
    def data(self,
             value: Any) -> None:
        self._data = value

    @property
    def default_data(self) -> Any:
        return self._default_data

    @property
    def data_type(self) -> PlugType:
        return self._data_type

    @property
    def mode(self) -> PlugMode:
        return self._mode

    @property
    def connections(self) -> List[Plug]:
        return self._connections

    def has_connections(self) -> bool:
        return len(self.connections) > 0

    def update_inputs(self) -> None:
        if len(self.connections) == 1:
            self.data = self.connections[0].data
        elif len(self.connections) > 1:
            self.data = list()

            for connection in self.connections:
                self.data.append(connection.data)
        else:
            raise PlugError(f"Plug {self.long_name} as no connections, "
                            f"cannot update data from inputs")

    def connect(self,
                other : Plug) -> None:
        if other is None:
            return

        if self.mode != PlugMode.PLUG or other.mode != PlugMode.PLUG:
            raise PlugError(f"Plug {self.long_name} cant be connected "
                            f"to plug {self.long_name}, either this plug or the "
                            f"other is a parameter or a graph parameter")

        self.connections.append(other)

    def disconnect(self,
                   other : Plug) -> None:
        if other is None:
            return

        if not other in self.connections:
            raise PlugError(f"Plug {other.long_name} is not connected to plug "
                            f"{self.long_name} and this cant be disconnected")

        self.connections.remove(other)
        other.connections.remove(self)

    def __rshift__(self,
                   other: Plug) -> None:
        self.connect(other)

    def __lshift__(self,
                   other: Plug) -> None:
        other.connect(self)
