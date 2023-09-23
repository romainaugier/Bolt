import os
import json
import typing

from bolt.utils.singleton import Singleton


class Config(Singleton):

    _data = dict()

    def __init__(self) -> None:
        if self.first_initialization:
            self._data.clear()

            if os.environ.get("BOLT_CONFIG_FILE") is not None:
                self.load_from_file(os.environ.get("BOLT_CONFIG_FILE"))
            
    def load_from_file(self, file_path: str) -> None:
        with open(file_path, "r", encoding="utf-8") as file:
            self._data = json.load(file) 

    def get(self, key: str) -> typing.Any:
        return self._data.get(key)