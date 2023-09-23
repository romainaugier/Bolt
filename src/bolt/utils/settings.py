# Library containing an utility class for settings

# name of a setting should always be <namespace>_<setting_name>
# for example : "launcher_last_project_used"
#               "ndb_opened_projects"

import json
import os
import typing

import bolt.utils.filesystem as fs
import bolt.log as log

from bolt.utils.singleton import Singleton

USER_SETTINGS_FILE = f"{fs.get_documents_folder()}/bolt/settings.json"
USER_SETTINGS_DIR = os.path.dirname(USER_SETTINGS_FILE)

class Settings(Singleton):
    """
    """
    
    _data = dict()
    
    def __init__(self,
                 settings_file: str = None) -> None:
        """
        """
        if self.first_initialization:
            self._data.clear()
            self.from_file(USER_SETTINGS_FILE)
            
    def as_bool(self,
                setting_key: str) -> bool:
        """
        """
        if setting_key in self._data:
            try:
                return bool(self._data[setting_key])
            except:
                return False
        else:
            return None
            
    def as_int(self,
               setting_key: str) -> int:
        """
        """
        if setting_key in self._data:
            try:
                return int(self._data[setting_key])
            except:
                return 0
        else:
            return None
            
    def as_float(self,
                 setting_key: str) -> float:
        """
        """
        if setting_key in self._data:
            try:
                return float(self._data[setting_key])
            except:
                return 0.0
        else:
            return None
            
    def as_string(self,
                  setting_key: str) -> str:
        """
        """
        if setting_key in self._data:
            try:
                return str(self._data[setting_key])
            except:
                return ""
        else:
            return None
            
    def get(self,
            setting_key: str,
            default: typing.Any = None) -> typing.Any:
        """
        """
        if setting_key in self._data:
            data = self._data[setting_key]
            return data if data is not None else default
        else:
            return default
        
    def __getitem__(self,
                    key: str) -> typing.Any:
        """
        """
        return self.get(key)
        
    def set(self,
            setting_key: str,
            setting_value: typing.Any) -> None:
        """
        """
        self._data[setting_key] = setting_value

    def from_file(self,
                  settings_file_path: str) -> None:
        """
        """
        if os.path.exists(settings_file_path):
            try:
                with open(settings_file_path, 'r') as file:
                    self._data.update(json.load(file))

                    log.debug("Loaded settings from file : \"{}\"".format(settings_file_path))
            except:
                log.error("Error during preference loading, check your preferences file. Default preferences will be used.")

    def to_file(self,
                settings_file_path: str) -> None:
        """
        """
        if not os.path.exists(os.path.dirname(settings_file_path)):
            os.makedirs(os.path.dirname(settings_file_path))

        with open(settings_file_path, 'w') as file:
            json.dump(self._data, file, indent=2)

        log.debug("Saved settings to file : \"{}\"".format(settings_file_path))

    def save(self) -> None:
        """
        """
        self.to_file(USER_SETTINGS_FILE)

    def reload(self,
               settings_file_path: str) -> None:
        """
        """
        self.from_file(settings_file_path)