import os
import importlib
import sys

from bolt.utils.singleton import Singleton
from bolt.utils.environment import Environment
from bolt.utils.config import Config


class NodeLibrary(Singleton):
    
    def __init__(self) -> None:
        app_name = Config().get("app_name")
        app_name_env_var = app_name.upper()

        self._stdlib_path = Environment().get(f"{app_name_env_var}_LIB") + "/nodes"

        self._other_paths = Environment().get(f"{app_name_env_var}_NODES_PATH")

        
        