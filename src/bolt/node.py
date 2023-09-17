from __future__ import annotations

import json
import typing
import enum
import importlib
import threading

import log


class PlugWarning(Exception):
    pass


class PlugError(Exception):
    pass


class _PlugType():
    
    def __init__(self, id: int, name: str) -> None:
        self._id = id
        self._name = name

    def __str__(self) -> str:
        return self._name

    def __eq__(self, other: _PlugType) -> bool:
        return self._id == other._id


class PlugType():
    INT = _PlugType(0, "int")
    FLOAT = _PlugType(1, "float")
    STR = _PlugType(2, "str")
    BOOL = _PlugType(3, "bool")
    LIST = _PlugType(4, "list")
    DICT = _PlugType(5, "dict")
    CUSTOM = _PlugType(6, "custom")


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


class PlugMode(enum.IntEnum):
    PLUG = 0
    PARAMETER = 1
    GRAPH_PARAMETER = 2


class Plug():
    def __init__(self,
                 short_name: str,
                 parent_node: Node,
                 data: typing.Any = None,
                 default_data: typing.Any = None,
                 data_type: PlugType = PlugType.CUSTOM,
                 mode: PlugMode = PlugMode.PLUG) -> None:
        self._short_name = short_name

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
    def parent_node(self) -> Node:
        return self._parent_node

    @property
    def data(self) -> typing.Any:
        return self._data

    @data.setter
    def data(self,
             value: typing.Any) -> None:
        self._data = value

    @property
    def default_data(self) -> typing.Any:
        return self._default_data

    @property
    def data_type(self) -> PlugType:
        return self._data_type

    @property
    def mode(self) -> PlugMode:
        return self._mode

    @property
    def connections(self) -> typing.List[Plug]:
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


class Result(enum.IntEnum):
    Ok = 0
    Warning = 1
    Error = 2


class CookResult():
    def __init__(self, result: Result, message: str = None) -> None:
        self._result = result
        self._message = message
        
    @property
    def result(self) -> Result:
        return self._result
    
    @property
    def message(self) -> str:
        return self._message

        
class NodeError(Exception):
    pass


class NodeState(enum.IntEnum):
    Dirty = 0
    Cooking = 1
    Cooked = 2


class Node():

    def __init__(self):
        self._definition = dict()

        self._inputs = dict()
        self._outputs = dict()
        self._parameters = dict()
        
        self._lock = threading.Lock()

        self._id = 0
        self._name = None
        self._parent_graph = None

        self._state = NodeState.Dirty

        self._in_queue = False
        self._in_temp_queue = False

    # Properties
    
    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, name: str) -> None:
        self._name = name

    @property
    def id(self) -> int:
        return self._id
    
    @id.setter 
    def id(self, id: int) -> None:
        self._id = id

    @property
    def parent_graph(self) -> typing.Any:
        return self._parent_graph
    
    @parent_graph.setter 
    def parent_graph(self, parent_graph: typing.Any) -> None:
        self._parent_graph = parent_graph

    @property
    def in_queue(self) -> bool:
        return self._in_queue
    
    @in_queue.setter 
    def in_queue(self, in_queue: bool) -> None:
        self._in_queue = in_queue
        
    @property
    def in_temp_queue(self) -> bool:
        return self._in_temp_queue
    
    @in_temp_queue.setter 
    def in_temp_queue(self, in_temp_queue: bool) -> None:
        self._in_temp_queue = in_temp_queue
        
    # Inputs and outputs

    def add_input(self, 
                  name: str,
                  default: typing.Any,
                  data_type: PlugType) -> None:
        if name in self._inputs:
            raise NodeError(f"This node already has an input plug with this name : {name}")

        self._inputs[name] = Plug(name, self, data=default, default=default, data_type=data_type)

    def add_output(self, 
                   name: str,
                   default: typing.Any,
                   data_type: PlugType) -> None:
        if name in self._outputs:
            raise NodeError(f"This node already has an output plug with this name : {name}")

        self._outputs[name] = Plug(name, self, data=default, default=default, data_type=data_type)

    def add_parameter(self,
                      name: str,
                      default: typing.Any,
                      data_type: PlugType) -> None:
        if name in self._parameters:
            raise NodeError(f"This node already has a parameter with this name : {name}")

        self._parameters[name] = Plug(name, self, data=default, default_data=default, data_type=data_type, mode=PlugMode.PARAMETER)

    def remove_input(self, name: str) -> None:
        if not name in self._inputs:
            log.error(f"Input \"{name}\" does not exist and thus cannot be removed")
            return

        self._inputs.pop(name)
    
    def remove_output(self, name: str) -> None:
        if not name in self._outputs:
            log.error(f"Output \"{name}\" does not exist and thus cannot be removed")
            return

        self._outputs.pop(name)

    def remove_parameter(self, name: str) -> None:
        if not name in self._parameters:
            log.error(f"Parameter \"{name}\" does not exist and thus cannot be removed")
            return

        self._parameters.pop(name)

    def get_input(self, name: str) -> Plug:
        return self._inputs.get(name, None)

    def get_output(self, name: str) -> Plug:
        return self._outputs.get(name, None)

    def get_parameter(self, name: str) -> Plug:
        return self._parameters.get(name, None)

    def __getitem__(self, name: str) -> Plug:
        if name in self._inputs:
            return self._inputs[name]
        elif name in self._outputs:
            return self._outputs[name]
        elif name in self._parameters:
            return self._parameters[name]
        else:
            return None