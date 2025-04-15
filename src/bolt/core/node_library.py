import os
import importlib
import sys
import traceback
import typing

import bolt.utils.log as log

from bolt.utils.singleton import Singleton
from bolt.utils.environment import Environment
from bolt.utils.config import Config, ConfigConstants
from bolt.core.node import Node

class NodeLibrary(Singleton):
    
    _nodes = dict()
    
    def __init__(self) -> None:
        if self.first_initialization:
            app_name = Config().get(ConfigConstants.AppName)
            app_name_env_var = app_name.upper()

            self._stdlib_path = Environment().get(f"{app_name_env_var}_LIB") + "/nodes"

            self._other_paths = Environment().get(f"{app_name_env_var}_NODES_PATH")

            self._nodes.clear()

            
    def load_all(self) -> None:
        paths = [self._stdlib_path]
        paths.extend(self._other_paths)

        for path in paths:
            if not os.path.isdir(path):
                continue

            for entry in os.scandir(path):
                if not entry.is_file():
                    continue

                if not entry.name.endswith(".py"):
                    continue

                parent_dir = os.path.dirname(entry.path)
                node_type , _ = os.path.splitext(entry.name)
        
                try:
                    sys.path.append(parent_dir)
                    mod = importlib.import_module(node_type)
                    sys.path.remove(parent_dir)

                    self._nodes[node_type] = mod.get_node
                except Exception:
                    log.error(f"Error during node type loading : {node_type}")
                    log.error(traceback.format_exc())

    def get_node(self, type_name: str) -> typing.Optional[Node]:
        """
        Get a node instance by its type name.
        
        Args:
            type_name: The name of the node type to instantiate
            
        Returns:
            An instance of the requested node or None if the type is not found
        """
        if type_name not in self._nodes:
            log.error(f"Node type not found: {type_name}")
            return None
            
        try:
            node_instance = self._nodes[type_name]()
            return node_instance
        except Exception:
            log.error(f"Error instantiating node of type: \"{type_name}\"")
            log.error(traceback.format_exc())
            return None