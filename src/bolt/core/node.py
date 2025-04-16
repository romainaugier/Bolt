from __future__ import annotations

import json
import typing
import enum
import importlib
import threading
import functools
import traceback
import time
import uuid
import weakref

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
                 parent_node: typing.Union[Node, Graph],
                 data: typing.Any = None,
                 default_data: typing.Any = None,
                 data_type: PlugType = PlugType.CUSTOM,
                 mode: PlugMode = PlugMode.PLUG) -> None:
        self._short_name = short_name
        self._parent_node = weakref.ref(parent_node)
        self._data = data
        self._default_data = default_data if default_data is not None else data
        self._data_type = data_type
        self._mode = mode
        self._connections = list()

    @property
    def short_name(self) -> str:
        return self._short_name

    @property
    def parent_node(self) -> typing.Union[Node, Graph]:
        return self._parent_node

    @property
    def data(self) -> typing.Any:
        if self.mode != PlugMode.PLUG:
            return self.eval()

        return self._data

    @data.setter
    def data(self, value: typing.Any) -> None:
        self._data = value

        if isinstance(self._parent_node, Node):
            self._parent_node.set_downstream_dirty()

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

    def get_path(self) -> str:
        parent_path = self.parent_node.path if self.parent_node else ""

        return f"{parent_path}.{self.short_name}"

    def has_connections(self) -> bool:
        return len(self.connections) > 0

    def update_inputs(self) -> None:
        if self.mode != PlugMode.PLUG:
            return

        if not self.has_connections():
            return

        try:
            if len(self.connections) == 1:
                self.data = self.connections[0].eval()
            elif len(self.connections) > 1:
                self.data = [conn.eval() for conn in self.connections]
        except Exception as e:
            raise PlugError(f"Error evaluating connection for plug {self.get_path()}: {e}") from e

    def connect(self, other: Plug) -> bool:
        if other is None:
            log.warning(f"Attempted to connect plug {self.get_path()} to None.")
            return False
        if self.mode != PlugMode.PLUG or other.mode != PlugMode.PLUG:
            raise PlugError(f"Connection failed: Plug {self.get_path()} ({self.mode.name}) cannot be connected "
                            f"to plug {other.get_path()} ({other.mode.name}). Only PLUG modes can connect.")
        if self == other:
            raise PlugError(f"Connection failed: Cannot connect plug {self.get_path()} to itself.")

        if other in self.connections:
            log.warning(f"Plugs {self.get_path()} and {other.get_path()} are already connected.")
            return True

        self.connections.append(other)

        if isinstance(self.parent_node, Node):
            self.parent_node.set_downstream_dirty()

        return True

    def disconnect(self, other: Plug) -> bool:
        if other is None:
            return False

        if other not in self.connections:
            log.warning(f"Plug {other.get_path()} is not connected to plug {self.get_path()}. Cannot disconnect.")
            return False

        self.connections.remove(other)

        if isinstance(self.parent_node, Node):
            self.parent_node.set_downstream_dirty()

        return True

    def disconnect_all(self) -> None:
        if self.mode == PlugMode.PLUG and self.has_connections():
            connected_plugs = list(self.connections)

            for other_plug in connected_plugs:
                self.disconnect(other_plug)

        if isinstance(self.parent_node, Node):
            self.parent_node.set_downstream_dirty()

    def __rshift__(self, other: Plug) -> None:
        other.connect(self)

    def __lshift__(self, other: Plug) -> None:
        self.connect(other)

    def eval(self) -> typing.Any:
        current_data = self.data
        data_str = str(current_data)

        if self._data_type in (PlugType.INT, PlugType.FLOAT, PlugType.STR, PlugType.BOOL):
            needs_eval = (isinstance(current_data, str) and
                         (globalExprEvaluator.string_contains_expr(data_str) or
                          globalExprEvaluator.string_contains_var(data_str)))

            if needs_eval:
                try:
                    evaluated_str = globalExprEvaluator.expand_string(data_str)
                    if self._data_type == PlugType.INT:
                        return int(evaluated_str)
                    elif self._data_type == PlugType.FLOAT:
                        return float(evaluated_str)
                    elif self._data_type == PlugType.BOOL:
                        lower_str = evaluated_str.lower()

                        if lower_str in ('false', '0', 'no', 'off'):
                            return False

                        try:
                            return bool(int(evaluated_str))
                        except ValueError:
                            pass
                        try:
                            return bool(float(evaluated_str))
                        except ValueError:
                            pass

                        return bool(evaluated_str)
                    elif self._data_type == PlugType.STR:
                        return evaluated_str

                except Exception as e:
                    raise PlugError(f"Error evaluating expression '{data_str}' for plug {self.get_path()}: {e}") from e
            else:
                try:
                    if self._data_type == PlugType.INT: return int(current_data)
                    if self._data_type == PlugType.FLOAT: return float(current_data)
                    if self._data_type == PlugType.BOOL: return bool(current_data)
                    if self._data_type == PlugType.STR: return str(current_data)
                except (ValueError, TypeError) as e:
                    log.warning(f"Data type mismatch for plug {self.get_path()}. Expected {self.data_type.name}, got {type(current_data)}. Returning default.")

                    return self.default_data

        elif self._data_type in (PlugType.LIST, PlugType.DICT, PlugType.CUSTOM):
            return current_data

        return current_data

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        state = {
            "short_name": self.short_name,
            "data": self.data,
            "_data": self._data,
            "default_data": self.default_data,
            "data_type": self.data_type.name,
            "mode": self.mode.value,
            "connections": []
        }

        if self.mode == PlugMode.PLUG:
            state["connections"] = [
                { "node_id": conn.parent_node.id, "plug_name": conn.short_name }
                for conn in self.connections if isinstance(conn.parent_node, Node)
            ]

        return state

    @classmethod
    def from_dict(cls,
                  data: typing.Dict[str, typing.Any],
                  parent_node: typing.Union[Node, Graph]) -> Plug:
        plug = cls(
            short_name=data["short_name"],
            parent_node=parent_node,
            data=data.get("_data", data.get("data")),
            default_data=data["default_data"],
            data_type=PlugType[data["data_type"]],
            mode=PlugMode(data["mode"])
        )

        return plug

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

    node_type_name: typing.ClassVar[str] = "base.Node"

    def __init__(self):
        self._inputs = OrderedDict()
        self._outputs = OrderedDict()
        self._parameters = OrderedDict()
        self._metadata = dict()

        self._lock = threading.Lock()

        self._id = uuid.uuid4().hex
        self._name = f"{self.__class__.__name__}_{self._id[:4]}"
        self._parent_graph = None
        self._path = None
        self._is_disabled = False
        self._state = NodeState.Dirty

        self._in_queue = False
        self._in_temp_queue = False

        self._cook_time = None
        self._error_message = None

        self.color = (40, 40, 40)

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, name: str) -> None:
        if self._name == name:
            return
        old_path = self.path
        self._name = name
        self._update_path()

        if self.parent_graph:
             self.parent_graph._handle_node_renamed(self, old_path)

        self.set_downstream_dirty()

    @property
    def id(self) -> str:
        return self._id

    @property
    def path(self) -> str:
        if self._path is None and self._parent_graph:
            self._update_path()
        return self._path if self._path else f"/{self.name}"

    @path.setter
    def path(self, path: str) -> None:
        self._path = path

    def _update_path(self):
        if self._parent_graph:
            self._path = f"{self.parent_graph.path}/{self.name}"
        else:
            self._path = f"/{self.name}"

    @property
    def parent_graph(self) -> typing.Optional[Graph]:
        return self._parent_graph

    @parent_graph.setter
    def parent_graph(self, parent_graph: typing.Optional[Graph]) -> None:
        self._parent_graph = weakref.ref(parent_graph)
        self._update_path()

    @property
    def is_disabled(self) -> bool:
        return self._is_disabled

    @is_disabled.setter
    def is_disabled(self, disabled: bool) -> None:
        if self._is_disabled != disabled:
            self._is_disabled = disabled
            self.set_downstream_dirty()

    @property
    def state(self) -> NodeState:
        return self._state

    def _set_state(self, state: NodeState) -> None:
        if self._state != state:
            self._state = state

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

    @property
    def cook_time(self) -> typing.Optional[float]:
        return self._cook_time

    @property
    def error_message(self) -> typing.Optional[str]:
        return self._error_message

    @property
    def color(self) -> typing.Tuple[int, int, int]:
        return self.get_metadata("__color", (40, 40, 40))

    @color.setter
    def color(self, color: typing.Tuple[int, int, int]) -> None:
        self.set_metadata("__color", color)

    @property
    def icon_path(self) -> typing.Optional[str]:
        return self.get_metadata("__icon_path")

    @icon_path.setter
    def icon_path(self, path: typing.Optional[str]) -> None:
        self.set_metadata("__icon_path", path)

    @property
    def category(self) -> typing.Optional[str]:
        return self.get_metadata("__category")

    @category.setter
    def category(self, category: typing.Optional[str]) -> None:
        self.set_metadata("__category", category)

    def _add_plug(self,
                  plug_dict: typing.MutableMapping[str, Plug],
                  name: str,
                  default: typing.Any,
                  data_type: PlugType,
                  mode: PlugMode) -> Plug:
        if name in plug_dict or name in self._inputs or name in self._outputs or name in self._parameters:
            raise NodeError(f"Node {self.path} already has a plug/parameter named '{name}'")

        plug = Plug(name, self, data=default, default_data=default, data_type=data_type, mode=mode)
        plug_dict[name] = plug
        self.set_downstream_dirty()

        return plug

    def add_input(self, name: str, default: typing.Any, data_type: PlugType) -> Plug:
        return self._add_plug(self._inputs, name, default, data_type, PlugMode.PLUG)

    def add_output(self, name: str, default: typing.Any, data_type: PlugType) -> Plug:
        return self._add_plug(self._outputs, name, default, data_type, PlugMode.PLUG)

    def add_parameter(self, name: str, default: typing.Any, data_type: PlugType) -> Plug:
        return self._add_plug(self._parameters, name, default, data_type, PlugMode.PARAMETER)

    def _remove_plug(self, plug_dict: typing.MutableMapping[str, Plug], name: str) -> None:
        if name not in plug_dict:
            log.warning(f"Plug/Parameter '{name}' not found in node {self.path}, cannot remove.")
            return

        plug_to_remove = plug_dict[name]

        plug_to_remove.disconnect_all()

        if plug_to_remove in self._outputs.values():
             if self.parent_graph:
                 self.parent_graph._clear_connections_to_plug(plug_to_remove)

        plug_dict.pop(name)

        self.set_downstream_dirty()

    def remove_input(self, name: str) -> None:
        self._remove_plug(self._inputs, name)

    def remove_output(self, name: str) -> None:
        self._remove_plug(self._outputs, name)

    def remove_parameter(self, name: str) -> None:
        self._remove_plug(self._parameters, name)

    def get_input(self, name: str) -> typing.Optional[Plug]:
        return self._inputs.get(name)

    def get_output(self, name: str) -> typing.Optional[Plug]:
        return self._outputs.get(name)

    def get_parameter(self, name: str) -> typing.Optional[Plug]:
        return self._parameters.get(name)

    def __getitem__(self, name: str) -> typing.Optional[Plug]:
        return self.get_parameter(name) or self.get_input(name) or self.get_output(name)

    @property
    def inputs(self) -> typing.Mapping[str, Plug]:
        return self._inputs

    @property
    def outputs(self) -> typing.Mapping[str, Plug]:
        return self._outputs

    @property
    def parameters(self) -> typing.Mapping[str, Plug]:
        return self._parameters

    def get_metadata(self, key: str, default: typing.Any = None) -> typing.Any:
        return self._metadata.get(key, default)

    def set_metadata(self, key: str, value: typing.Any) -> None:
        self._metadata[key] = value

    def set_dirty(self) -> None:
        if self.state != NodeState.Dirty:
            self._set_state(NodeState.Dirty)
            self._cook_time = None
            self._error_message = None
            self.set_downstream_dirty()

    def set_downstream_dirty(self) -> None:
        if not self.parent_graph:
            return

        for output_plug in self.outputs.values():
            downstream_nodes = self.parent_graph.get_downstream_nodes(output_plug)

            for node in downstream_nodes:
                 if node.state != NodeState.Dirty:
                     node.set_dirty()

    def needs_cook(self) -> bool:
        if self.is_disabled:
            return False

        if self.state == NodeState.Dirty or self.state == NodeState.Error:
            return True

        return False

    def _pre_cook(self) -> None:
        if self.is_disabled:
            return

        for input_plug in self.inputs.values():
            if input_plug.has_connections():
                try:
                    input_plug.update_inputs()
                except PlugError as e:
                    err_msg = f"Error updating input '{input_plug.short_name}' for node {self.path}: {e}"
                    log.error(err_msg)
                    self._error_message = err_msg
                    self._set_state(NodeState.Error)
                    raise NodeError(err_msg) from e
            else:
                err_msg = f"Error input \"{input_plug.short_name}\" for node {self.path} should have connections"
                log.error(err_msg)
                self._error_message = err_msg
                self._set_state(NodeState.Error)
                raise NodeError(err_msg)

        self._set_state(NodeState.Cooking)
        self._error_message = None
        self._cook_time = None

    def _post_cook(self, result: NodeCookResult) -> None:
        if self.is_disabled:
            if self.inputs:
                first_input = next(iter(self.inputs.values()))

                try:
                    passthrough_data = first_input.eval()
                    for output_plug in self.outputs.values():
                        output_plug.data = passthrough_data
                    self._set_state(NodeState.Cooked)
                except Exception as e:
                    log.error(f"Error evaluating passthrough data for disabled node {self.path}: {e}")
                    self._set_state(NodeState.Error)
                    self._error_message = f"Disabled node passthrough error: {e}"
            else:
                self._set_state(NodeState.Cooked)
            return

        if result.result == NodeResult.Ok:
            self._set_state(NodeState.Cooked)
        else:
            self._set_state(NodeState.Error)
            self._error_message = result.message or f"Node {self.path} cook failed with no specific message."
            log.error(f"Node {self.path} failed to cook: {self._error_message}")


    def _cook_node(self) -> NodeCookResult:
        final_result = NodeCookResult(NodeResult.Ok)

        if self.is_disabled:
            self._pre_cook()
            self._post_cook(final_result)
            return final_result

        if self.state == NodeState.Cooked:
            log.debug(f"Skipping cook for already cooked node {self.path}")
            return final_result

        try:
            self._pre_cook()

            start_time = time.perf_counter()

            try:
                cook_result = self.cook()

                if not isinstance(cook_result, NodeCookResult):
                    log.warning(f"Node {self.path} cook() method did not return NodeCookResult. Assuming Ok.")
                    cook_result = NodeCookResult(NodeResult.Ok)

                final_result = cook_result

            except NotImplementedError:
                err_msg = f"Node {self.path} ({self.__class__.__name__}) does not implement the 'cook' method."
                log.error(err_msg)
                final_result = NodeCookResult(NodeResult.Error, err_msg)
            except Exception:
                err_msg = f"Error during node cook ({self.path}):\n{traceback.format_exc()}"
                log.error(err_msg)
                final_result = NodeCookResult(NodeResult.Error, err_msg)

            finally:
                self._cook_time = time.perf_counter() - start_time

            self._post_cook(final_result)

        except NodeError as e:
            final_result = NodeCookResult(NodeResult.Error, str(e))
        except Exception as e:
            err_msg = f"Unexpected error in _cook_node for {self.path}:\n{traceback.format_exc()}"
            log.error(err_msg)
            final_result = NodeCookResult(NodeResult.Error, err_msg)
            self._set_state(NodeState.Error)
            self._error_message = err_msg

        return final_result

    def cook(self) -> NodeCookResult:
        """
        Should be overriden by the user
        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement the cook method.")

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        return {
            "id": self.id,
            "node_type": self.node_type_name,
            "name": self.name,
            "is_disabled": self.is_disabled,
            "metadata": self._metadata,
            "parameters": {name: plug.to_dict() for name, plug in self.parameters.items()},
            "inputs": {name: plug.to_dict() for name, plug in self.inputs.items()},
            "outputs": {name: plug.to_dict() for name, plug in self.outputs.items()},
        }

    def from_dict(self, data: typing.Dict[str, typing.Any]) -> None:
        self.name = data["name"]
        self._is_disabled = data.get("is_disabled", False)
        self._metadata = data.get("metadata", {})

        self._parameters.clear()
        self._inputs.clear()
        self._outputs.clear()

        for name, plug_data in data.get("parameters", {}).items():
            self._parameters[name] = Plug.from_dict(plug_data, self)

        for name, plug_data in data.get("inputs", {}).items():
            self._inputs[name] = Plug.from_dict(plug_data, self)

        for name, plug_data in data.get("outputs", {}).items():
            self._outputs[name] = Plug.from_dict(plug_data, self)

        self._set_state(NodeState.Dirty)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(path='{self.path}', state={self.state.name})>"
