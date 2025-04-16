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
import os
import weakref

from collections import OrderedDict

import bolt.utils.log as log

from bolt.core.node import Node, Plug, NodeResult, NodeState, NodeError, PlugError
from bolt.core.node_library import NodeLibrary
from bolt.utils.expression import globalExprEvaluator

class GraphResult(enum.IntEnum):
    Ok = 0
    Error = 1
    Cancelled = 2

class GraphCookResult():
    def __init__(self, result: GraphResult, message: str = None, cook_time: float = 0.0) -> None:
        self._result = result
        self._message = message
        self._cook_time = cook_time

    @property
    def result(self) -> GraphResult:
        return self._result

    @property
    def message(self) -> str:
        return self._message

    @property
    def cook_time(self) -> float:
        return self._cook_time

class GraphEventType(enum.Enum):
    CookStart = "cook_start"
    CookEnd = "cook_end"
    CookProgress = "cook_progress"
    CookPaused = "cook_paused"
    CookResumed = "cook_resumed"
    NodeCooked = "node_cooked"
    GraphError = "graph_error"

class GraphError(Exception):
    pass

class Graph():

    def __init__(self, name: str = "unnamed_graph") -> None:
        self._id = uuid.uuid4().hex
        self._name = name
        self._save_path: typing.Optional[str] = None
        self._parent_graph: typing.Optional[Graph] = None

        self._nodes = OrderedDict()
        self._sorted_nodes: typing.List[Node] = list()

        self._is_cooking: bool = False
        self._has_error: bool = False
        self._stop_cook_requested: bool = False
        self._cook_progress: float = 0.0
        self._cook_time: typing.Optional[float] = None

        self._cooked_node_ids: typing.Set[str] = set()

        self._lock = threading.Lock()
        self._cook_control_event = threading.Event()
        self._cook_control_event.set()

        self._callbacks: typing.Dict[GraphEventType, typing.List[typing.Callable]] = {event_type: [] for event_type in GraphEventType}

        self._parameters = OrderedDict()

        self._node_name_to_id: typing.Dict[str, str] = dict()

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, name: str) -> None:
        if self._name == name:
            return
        with self._lock:
            self._name = name

            for node in self.nodes:
                node._update_path()


    @property
    def path(self) -> str:
        if self.parent_graph is not None:
            return f"{self.parent_graph.path}/{self.name}"
        else:
            return f"/{self.name}"

    @property
    def save_path(self) -> typing.Optional[str]:
        return self._save_path

    @save_path.setter
    def save_path(self, path: typing.Optional[str]) -> None:
        if self._save_path != path:
            self._save_path = path

    @property
    def parent_graph(self) -> typing.Optional[Graph]:
        return self._parent_graph

    @parent_graph.setter
    def parent_graph(self, parent: typing.Optional[Graph]):
        self._parent_graph = weakref.ref(parent)

        for node in self.nodes:
            node._update_path()

    @property
    def nodes(self) -> typing.Sequence[Node]: 
        return list(self._nodes.values())

    @property
    def sorted_nodes(self) -> typing.Sequence[Node]:
        
        
        return self._sorted_nodes

    @property
    def parameters(self) -> typing.Mapping[str, Plug]:
         return self._parameters

    
    @property
    def is_cooking(self) -> bool:
        return self._is_cooking

    @property
    def has_error(self) -> bool:
        return self._has_error

    @property
    def cook_progress(self) -> float:
        return self._cook_progress

    @property
    def cook_time(self) -> typing.Optional[float]:
        return self._cook_time

    def add_event_callback(self, event_type: GraphEventType, callback: typing.Callable) -> None:
        if not callable(callback):
            log.error("Callback must be callable")
            return

        with self._lock:
            self._callbacks[event_type].append(callback)
            log.debug(f"Added callback for event {event_type.name}")

    def remove_event_callback(self, event_type: GraphEventType, callback: typing.Callable) -> None:
        with self._lock:
            try:
                self._callbacks[event_type].remove(callback)
                log.debug(f"Removed callback for event {event_type.name}")
            except ValueError:
                log.warning(f"Callback not found for event {event_type.name}, cannot remove.")

    def clear_event_callbacks(self, event_type: typing.Optional[GraphEventType] = None) -> None:
        with self._lock:
            if event_type:
                self._callbacks[event_type].clear()
                log.debug(f"Cleared all callbacks for event {event_type.name}")
            else:
                for key in self._callbacks:
                    self._callbacks[key].clear()

                log.debug("Cleared all callbacks for all events")

    def _emit_event(self, event_type: GraphEventType, *args, **kwargs) -> None:
        with self._lock:
            callbacks_to_run = list(self._callbacks[event_type])

        if callbacks_to_run:
            for callback in callbacks_to_run:
                try:
                    callback(*args, **kwargs)
                except Exception as e:
                    log.error(f"Error executing callback for event {event_type.name}: {e}\n{traceback.format_exc()}")
    
    def _generate_unique_node_name(self, base_name: str) -> str:
        if base_name not in self._node_name_to_id:
            return base_name

        i = 1

        while True:
            new_name = f"{base_name}_{i}"

            if new_name not in self._node_name_to_id:
                return new_name

            i += 1

    def add_node(self, node: Node) -> None:
        if not isinstance(node, Node):
            log.error("Can only add Node instances to the graph")
            return

        if node.id in self._nodes:
            log.warning(f"Node with ID {node.id} (\"{node.name}\") already exists in graph \#{self.name}\#.")
            return 

        with self._lock:
            node.name = self._generate_unique_node_name(node.name)
            node.parent_graph = self
            self._nodes[node.id] = node
            self._node_name_to_id[node.name] = node.id
            
            self._invalidate_sort_cache()
            
            node.set_dirty()

    def create_node(self, node_type_name: str, name: str = None) -> typing.Optional[Node]:
        node_instance = NodeLibrary().get_node(node_type_name)

        if node_instance is not None:
            if name is not None:
                node_instance.name = name 

            self.add_node(node_instance) 

            return node_instance

        return None

    def remove_node(self, node_ref: typing.Union[str, Node]) -> None:
        with self._lock:
            node_to_remove = self.get_node(node_ref)

            if not node_to_remove:
                log.warning(f"Cannot remove node: Reference \"{node_ref}\" not found in graph \"{self.name}\".")
                return

            node_id = node_to_remove.id
            node_name = node_to_remove.name
            
            for input_plug in node_to_remove.inputs.values():
                input_plug.disconnect_all() 
            
            for output_plug in node_to_remove.outputs.values():
                self._clear_connections_to_plug(output_plug) 

            del self._nodes[node_id]
            if node_name in self._node_name_to_id and self._node_name_to_id[node_name] == node_id:
                del self._node_name_to_id[node_name]
            
            node_to_remove.parent_graph = None
            
            self._invalidate_sort_cache()

    def get_node(self, node_ref: typing.Union[str, Node]) -> typing.Optional[Node]:
        if isinstance(node_ref, Node):
            return self._nodes.get(node_ref.id) if node_ref.id in self._nodes else None
        elif isinstance(node_ref, str):
            node = self._nodes.get(node_ref)

            if node:
                return node
            
            node_id = self._node_name_to_id.get(node_ref)

            if node_id:
                return self._nodes.get(node_id)
        
        return None

    def _handle_node_renamed(self, node: Node, old_name: str) -> None:
        with self._lock:
            old_id = self._node_name_to_id.pop(old_name, None)

            if old_id == node.id: 
                new_name = self._generate_unique_node_name(node.name)

                if new_name != node.name: 
                    node.name = new_name
                self._node_name_to_id[node.name] = node.id
            else:
                self._rebuild_name_lookup()

    def _rebuild_name_lookup(self) -> None:
        with self._lock:
            self._node_name_to_id.clear()

            collisions = dict()

            for node_id, node in self._nodes.items():
                if node.name in self._node_name_to_id:
                    collisions.setdefault(node.name, []).append(node)
                else:
                    self._node_name_to_id[node.name] = node_id
    
    def _clear_connections_to_plug(self, target_output_plug: Plug) -> None:
        if not isinstance(target_output_plug.parent_node, Node):
            return 

        nodes_to_check = list(self._nodes.values()) 

        for node in nodes_to_check:
            for input_plug in node.inputs.values():
                if target_output_plug in input_plug.connections:
                    input_plug.disconnect(target_output_plug) 

    def get_downstream_nodes(self, output_plug: Plug) -> typing.List[Node]:
        downstream_nodes = list()

        if not isinstance(output_plug.parent_node, Node) or output_plug not in output_plug.parent_node.outputs.values():
            return list()
        
        for node in self.nodes:
             for input_plug in node.inputs.values():
                 if output_plug in input_plug.connections:
                      downstream_nodes.append(node)
                      
        return list(set(downstream_nodes)) 

    def get_upstream_nodes(self, input_plug: Plug) -> typing.List[Node]:
        upstream_nodes = list()

        if not isinstance(input_plug.parent_node, Node) or input_plug not in input_plug.parent_node.inputs.values():
            return list()

        for connection in input_plug.connections:
            if isinstance(connection.parent_node, Node): 
                upstream_nodes.append(connection.parent_node)

        return list(set(upstream_nodes)) 
    
    def _invalidate_sort_cache(self) -> None:
        with self._lock:
            self._sorted_nodes = list()

    def sort_nodes(self) -> bool:
        with self._lock: 
            if self._sorted_nodes:
                return True 

            self._sorted_nodes = [] 
            temp_marked = set() 
            perm_marked = set() 
            node_list = list(self._nodes.values()) 

            has_error = False
            error_message = ""

            def visit(node: Node):
                nonlocal has_error, error_message

                if has_error:
                    return 

                if node.id in perm_marked:
                    return 

                if node.id in temp_marked:
                    has_error = True
                    error_message = f"Cycle detected involving node \"{node.path}\"."
                    log.error(error_message)
                    return 

                temp_marked.add(node.id) 
                
                for input_plug in node.inputs.values():
                    upstream_nodes = self.get_upstream_nodes(input_plug)

                    for upstream_node in upstream_nodes:
                        visit(upstream_node)

                        if has_error:
                            return 
                
                temp_marked.remove(node.id)
                perm_marked.add(node.id)
                self._sorted_nodes.append(node) 
            
            for node in node_list:
                if node.id not in perm_marked:
                    visit(node)

                    if has_error:
                        break 

            if has_error:
                self._sorted_nodes = list()
                self._has_error = True 
                self._emit_event(GraphEventType.GraphError, error_message)
                return False
            else:
                self._has_error = False 
                return True
    
    def set_all_dirty(self) -> None:
        with self._lock:
            for node in self.nodes:
                node.set_dirty() 

            self._cooked_node_ids.clear() 
            self._invalidate_sort_cache() 
            self._has_error = False 
            self._cook_time = None
            self._cook_progress = 0.0

    def pause_cook(self) -> None:
        if self._is_cooking:
            self._cook_control_event.clear() 
            self._emit_event(GraphEventType.CookPaused)

    def resume_cook(self) -> None:
        if self._is_cooking:
            self._cook_control_event.set() 
            self._emit_event(GraphEventType.CookResumed)

    def stop_cook(self) -> None:
        if self._is_cooking:
            with self._lock:
                 self._stop_cook_requested = True

            self._cook_control_event.set() 
    
    def cook(self,
             last_node_to_cook_ref: typing.Union[str, Node] = None,
             force_cook_all: bool = False) -> GraphCookResult:
        if self.is_cooking:
            msg = f"Graph '{self.name}' is already cooking."
            log.warning(msg)
            return GraphCookResult(GraphResult.Error, msg)
        
        cook_start_time = time.perf_counter()

        self._is_cooking = True
        self._stop_cook_requested = False
        self._has_error = False 
        self._cook_progress = 0.0
        self._cook_time = None
        self._cook_control_event.set() 

        self._emit_event(GraphEventType.CookStart)
        self._emit_event(GraphEventType.CookProgress, 0.0)
        
        with self._lock: 
            if not self._sorted_nodes: 
                if not self.sort_nodes(): 
                    self._is_cooking = False
                    err_msg = f"Graph \"{self.name}\" cannot be cooked due to sorting errors."
                    log.error(err_msg)
                    return GraphCookResult(GraphResult.Error, err_msg)
            
            last_node_id = None

            if last_node_to_cook_ref:
                last_node = self.get_node(last_node_to_cook_ref)

                if last_node:
                    last_node_id = last_node.id
                else:
                    msg = f"Last node to cook '{last_node_to_cook_ref}' not found."
                    log.error(msg)
                    self._is_cooking = False
                    self._emit_event(GraphEventType.GraphError, msg)
                    return GraphCookResult(GraphResult.Error, msg)
            
            nodes_to_process = list(self._sorted_nodes) 
            total_nodes_in_plan = len(nodes_to_process)
        
        cooked_count = 0
        final_result = GraphResult.Ok 
        final_message = None

        try:
            for i, node in enumerate(nodes_to_process):
                self._cook_control_event.wait() 

                with self._lock:
                    if self._stop_cook_requested:
                        final_result = GraphResult.Cancelled
                        final_message = "Cook cancelled by user request."
                        break 
                
                if node.is_disabled:
                    log.debug(f"Skipping disabled node '{node.path}'.")
                    
                    if node.id == last_node_id:
                          log.info(f"Reached target node '{node.path}' (disabled). Stopping cook.")
                          break

                    continue 

                if node.state == NodeState.Cooked and not force_cook_all:
                    cooked_count += 1 
                else:
                    node_cook_result = node._cook_node() 
                    
                    if node_cook_result.result == NodeResult.Error:
                        log.error(f"Error cooking node '{node.path}'. Stopping graph cook.")
                        self._has_error = True
                        final_result = GraphResult.Error
                        final_message = node_cook_result.message or f"Error in node '{node.path}'."
                        self._emit_event(GraphEventType.GraphError, final_message)
                        break 
                    
                    cooked_count += 1
                    self._cooked_node_ids.add(node.id) 
                    self._emit_event(GraphEventType.NodeCooked, node)
                
                if total_nodes_in_plan > 0:
                    current_progress = ((i + 1) / total_nodes_in_plan) * 100.0
                    
                    self._cook_progress = current_progress
                    self._emit_event(GraphEventType.CookProgress, self._cook_progress)
                
                if node.id == last_node_id:
                    break 

        except Exception as e:
            log.error(f"Unexpected error during graph cook: {e}\n{traceback.format_exc()}")
            final_result = GraphResult.Error
            final_message = f"Unexpected graph cook error: {e}"
            self._has_error = True
            self._emit_event(GraphEventType.GraphError, final_message)
        finally:
            self._cook_time = time.perf_counter() - cook_start_time
            self._is_cooking = False
            self._stop_cook_requested = False 

            if final_result == GraphResult.Ok:
                log.info(f"Graph \"{self.name}\" cooked successfully in {self._cook_time:.3f} seconds.")
            elif final_result == GraphResult.Cancelled:
                log.warning(f"Graph \"{self.name}\" cook cancelled after {self._cook_time:.3f} seconds.")
            else: 
                log.error(f"Graph \"{self.name}\" cook failed after {self._cook_time:.3f} seconds. Reason: {final_message}")

            self._emit_event(GraphEventType.CookEnd, final_result, final_message, self._cook_time)

        return GraphCookResult(final_result, final_message, self._cook_time)

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        with self._lock: 
            nodes_data = [node.to_dict() for node in self.nodes]
            graph_params_data = {name: plug.to_dict() for name, plug in self.parameters.items()}

            return {
                "graph_version": "1.0", 
                "id": self.id,
                "name": self.name,
                "save_path": self.save_path,
                "nodes": nodes_data,
                "graph_parameters": graph_params_data,
                "cooked_node_ids": list(self._cooked_node_ids), 
            }

    def from_dict(self, data: typing.Dict[str, typing.Any]) -> bool:
        with self._lock:
            try:
                self._nodes.clear()
                self._node_name_to_id.clear()
                self._sorted_nodes = []
                self._cooked_node_ids.clear()
                self._parameters.clear()
                self._has_error = False
                
                self._id = data.get("id", self._id) 
                self.name = data["name"] 
                self.save_path = data.get("save_path") 
                
                nodes_data = data.get("nodes", [])
                node_instances = {} 

                for node_data in nodes_data:
                    node_type = node_data.get("node_type")
                    node_id = node_data.get("id")

                    if not node_type or not node_id:
                         log.error(f"Skipping node data: Missing 'node_type' or 'id'. Data: {node_data}")
                         continue

                    node_instance = NodeLibrary().get_node(node_type)

                    if not node_instance:
                         log.error(f"Failed to create node instance for type '{node_type}' (ID: {node_id}). Skipping.")
                         continue

                    node_instance._id = node_id 
                    node_instance.from_dict(node_data) 
                    node_instance.parent_graph = self 
                    node_instances[node_id] = node_instance
                
                self._nodes = OrderedDict(node_instances)
                self._rebuild_name_lookup() 

                connection_count = 0

                for node_id, node in self._nodes.items():
                    node_data = next((nd for nd in nodes_data if nd.get("id") == node_id), None)

                    if not node_data:
                        continue

                    for input_name, input_plug_data in node_data.get("inputs", {}).items():
                        connections_info = input_plug_data.get("connections", [])
                        input_plug = node.get_input(input_name)

                        if not input_plug:
                            log.warning(f"Input plug '{input_name}' not found on node '{node.path}' during connection restoration.")
                            continue

                        for conn_info in connections_info:
                            target_node_id = conn_info.get("node_id")
                            target_plug_name = conn_info.get("plug_name")

                            target_node = self._nodes.get(target_node_id)

                            if not target_node:
                                log.warning(f"Target node ID '{target_node_id}' not found for connection to '{node.path}.{input_name}'. Skipping connection.")
                                continue

                            target_output_plug = target_node.get_output(target_plug_name)

                            if not target_output_plug:
                                log.warning(f"Target output plug '{target_plug_name}' not found on node '{target_node.path}' for connection to '{node.path}.{input_name}'. Skipping connection.")
                                continue
                            
                            try:
                                input_plug.connect(target_output_plug)
                                connection_count += 1
                            except PlugError as e:
                                log.error(f"Error restoring connection: {target_output_plug.get_path()} >> {input_plug.get_path()}. Error: {e}")

                graph_params_data = data.get("graph_parameters", {})

                for name, plug_data in graph_params_data.items():
                    self._parameters[name] = Plug.from_dict(plug_data, self)
                
                cooked_ids = data.get("cooked_node_ids", [])

                self._cooked_node_ids = set(cooked_ids)

                for node_id in self._cooked_node_ids:
                    node = self._nodes.get(node_id)

                    if node:
                        node._set_state(NodeState.Cooked)
                    else:
                        log.warning(f"Cooked node ID \"{node_id}\" found in data but node does not exist.")

                
                self._invalidate_sort_cache()

                log.info(f"Graph \"{self.name}\" loaded successfully with {len(self._nodes)} nodes.")

                return True

            except Exception as e:
                log.error(f"Failed to load graph from dictionary: {e}\n{traceback.format_exc()}")
                
                self._nodes.clear()
                self._node_name_to_id.clear()
                
                self._has_error = True

                return False

    def save_to_file(self, file_path: typing.Optional[str] = None) -> bool:
        path_to_save = file_path or self.save_path

        if not path_to_save:
            log.error(f"Cannot save graph \"{self.name}\": No file path provided and no save_path set.")
            return False

        try:
            dir_name = os.path.dirname(path_to_save)
            if dir_name: 
                 os.makedirs(dir_name, exist_ok=True)

            graph_data = self.to_dict()

            with open(path_to_save, "w", encoding="utf-8") as f:
                json.dump(graph_data, f, indent=2) 
            
            self.save_path = path_to_save
            log.debug(f"Graph \"{self.name}\" saved successfully.")
            return True

        except IOError as e:
            log.error(f"IOError saving graph to {path_to_save}: {e}")
        except TypeError as e:
             log.error(f"TypeError during JSON serialization for graph \"{self.name}\": {e}. Check data types in nodes/plugs.")
        except Exception as e:
            log.error(f"Unexpected error saving graph to {path_to_save}: {e}\n{traceback.format_exc()}")

        return False

    def load_from_file(self, file_path: str) -> bool:
        if not os.path.exists(file_path):
             log.error(f"Cannot load graph: File not found at \"{file_path}\#")
             return False

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                graph_data = json.load(f)

            success = self.from_dict(graph_data)
            if success:
                 self.save_path = file_path 
            return success

        except json.JSONDecodeError as e:
            log.error(f"JSONDecodeError loading graph from {file_path}: {e}")
        except IOError as e:
            log.error(f"IOError loading graph from {file_path}: {e}")
        except Exception as e:
            log.error(f"Unexpected error loading graph from {file_path}: {e}\n{traceback.format_exc()}")

        return False

    def __repr__(self) -> str:
        state = "Cooking" if self.is_cooking else ("Error" if self.has_error else "Idle")
        return f"<Graph(name='{self.name}', nodes={len(self._nodes)}, state={state})>"

    def __len__(self) -> int:
        return len(self._nodes)