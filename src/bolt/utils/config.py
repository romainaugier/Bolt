import os
import json
import typing
import traceback
import sys

import bolt.utils.log as log
from bolt.utils.singleton import Singleton


class Config(Singleton):

    _data = dict()

    def __init__(self) -> None:
        if self.first_initialization:
            self._data.clear()

            if os.environ.get("BOLT_CONFIG_FILE") is not None:
                self.load_from_file(os.environ.get("BOLT_CONFIG_FILE"))
            else:
                log.critical("BOLT_CONFIG_FILE environment variable is not defined, exiting application")
                sys.exit(1)
            
    def load_from_file(self, file_path: str) -> None:
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                self._data = json.load(file) 
        except Exception:
            log.error(f"Error caught during configuration loading : {traceback.format_exc()}")

    def get(self, key: str) -> typing.Any:
        return self._data.get(key)

    def __getitem__(self, key: str) -> typing.Any:
        return self.get(key)