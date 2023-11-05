from __future__ import annotations

import json
import typing
import enum
import importlib
import threading
import functools
import traceback

from collections import OrderedDict

import bolt.utils.log as log
from bolt.utils.expression import globalExprEvaluator


class PlugWarning(Exception):
    pass


class PlugError(Exception):
    pass


class PlugType(enum.Enum):
    INT = 0
    FLOAT = 1
    STR = 2
    BOOL = 3
    LIST = 4
    DICT = 5
    CUSTOM = 6


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
            self.data = self.connections[0].eval()
        elif len(self.connections) > 1:
            self.data = list()

            for connection in self.connections:
                self.data.append(connection.eval())
        else:
            raise PlugError(f"Plug {self.short_name} as no connections, "
                            f"cannot update data from inputs")

    def connect(self,
                other : Plug) -> None:
        if other is None:
            return

        if self.mode != PlugMode.PLUG or other.mode != PlugMode.PLUG:
            raise PlugError(f"Plug {self.short_name} cant be connected "
                            f"to plug {self.short_name}, either this plug or the "
                            f"other is a parameter or a graph parameter")

        self.connections.append(other)

    def disconnect(self,
                   other : Plug) -> None:
        if other is None:
            return

        if not other in self.connections:
            raise PlugError(f"Plug {other.short_name} is not connected to plug "
                            f"{self.short_name} and this cant be disconnected")

        self.connections.remove(other)
        other.connections.remove(self)

    def __rshift__(self,
                   other: Plug) -> None:
        self.connect(other)

    def __lshift__(self,
                   other: Plug) -> None:
        other.connect(self)

    def eval(self) -> typing.Any:
        if self._data_type == PlugType.INT:
            if (globalExprEvaluator.stringContainsExpr(str(self.data)) or 
                globalExprEvaluator.stringContainsVar(str(self.data))):
                return int(globalExprEvaluator.expandString(self.data))
            else:
                return self.data
        elif self._data_type == PlugType.FLOAT:
            if (globalExprEvaluator.stringContainsExpr(str(self.data)) or 
                globalExprEvaluator.stringContainsVar(str(self.data))):
                return float(globalExprEvaluator.expandString(self.data))
            else:
                return self.data
        elif self._data_type == PlugType.STR:
            if (globalExprEvaluator.stringContainsExpr(str(self.data)) or 
                globalExprEvaluator.stringContainsVar(str(self.data))):
                return globalExprEvaluator.expandString(self.data)
            else:
                return self.data
        elif self._data_type == PlugType.BOOL:
            if (globalExprEvaluator.stringContainsExpr(str(self.data)) or 
                globalExprEvaluator.stringContainsVar(str(self.data))):
                return bool(globalExprEvaluator.expandString(self.data))
            else:
                return self.data
        elif self._data_type == PlugType.LIST:
            return self.data
        elif self._data_type == PlugType.DICT:
            return self.data
        elif self._data_type == PlugType.CUSTOM:
            return self.data


class NodeResult(enum.IntEnum):
    Ok = 0
    Error = 1


class NodeCookResult():
    def __init__(self, result: NodeResult, message: str = None) -> None:
        self._result = result
        self._message = message
        
    @property
    def result(self) -> NodeResult:
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
    Error = 3


class Node():

    def __init__(self):
        self._inputs = OrderedDict()
        self._outputs = OrderedDict()
        self._parameters = OrderedDict()

        self._metadata = dict()
        
        self._lock = threading.Lock()

        self._id = 0
        self._name = None
        self._parent_graph = None
        self._path = None
        self._is_disabled = False

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
    def path(self) -> str:
        return self._path
    
    @path.setter 
    def path(self, path: str) -> None:
        self._path = path

    @property
    def parent_graph(self) -> typing.Any:
        return self._parent_graph
    
    @parent_graph.setter 
    def parent_graph(self, parent_graph: typing.Any) -> None:
        self._parent_graph = parent_graph

    @property
    def is_disabled(self) -> bool:
        return self._is_disabled
    
    @is_disabled.setter 
    def is_disabled(self, disabled: bool) -> None:
        self._is_disabled = disabled

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

    def get_input_by_index(self, index: int) -> Plug:
        return self.get_input(self._inputs.keys()[index])

    def get_output(self, name: str) -> Plug:
        return self._outputs.get(name, None)

    def get_output_by_index(self, index: int) -> Plug:
        return self.get_output(self._outputs.keys()[index])

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

    def has_inputs(self) -> bool:
        return len(self._inputs) > 0

    def has_outputs(self) -> bool:
        return len(self._outputs) > 0

    def has_parameters(self) -> bool:
        return len(self._parameters) > 0

    @property
    def inputs(self) -> typing.Dict[str, Plug]:
        return self._inputs

    @property
    def outputs(self) -> typing.Dict[str, Plug]:
        return self._outputs

    @property
    def parameters(self) -> typing.Dict[str, Plug]:
        return self._parameters

    # Metadata
    
    def get_metadata(self, key: str) -> typing.Any:
        return self._metadata.get(key)

    def set_metadata(self, key: str, value: typing.Any) -> None:
        self._metadata[key] = value

    # Cooking
    
    def _cook(self) -> NodeCookResult:
        if not self.is_disabled:
            for input in self.inputs.values():
                input.update_inputs()

            with self._lock:
                self._state = NodeState.Cooking

            try:
                result = self.cook()
            except Exception:
                with self._lock:
                    self._state = NodeState.Error

                err_message = f"Error caught during node cooking ({self.path}) :\n{traceback.format_exc()}"

                result = NodeCookResult(NodeResult.Error, err_message)

                log.error(err_message)
        else:
            if self.has_inputs():
                first_input = self.get_input_by_index(0)

                for output in self._outputs.items():
                    output.set_data(first_input.eval())

                result = NodeCookResult(NodeResult.Ok)

        return result

    def cook(self) -> NodeCookResult:
        """
        This function should be overloaded by the users

        Returns:
            CookResult: result of the cooking op
        """
        return NodeCookResult(NodeResult.Ok)