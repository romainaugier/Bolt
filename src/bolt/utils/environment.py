import os
import re
import json

import bolt.utils.log as log
import bolt.utils.filesystem as filesys
import bolt.utils.config as conf

from bolt.utils.singleton import Singleton


class Environment(Singleton):
    """
    Contains all the environment variables and the utils to find and replace them
    in a string
    
    To ease environment settings, you can provide files that can be located in the $APP_NAME_LIB/env or
    HOME/Documents/App Name/env folders. 
    Those files should be named "whatever_you_want.env" and be formatted as json files like the following :
    
    [
        { 
            "VARIABLE_NAME" : "VARIABLE_VALUE",
            "mode" : "append"
        },
        {
            "VARIABLE_NAME" : "VARIABLE_VALUE",
            "mode" : "replace"
        },
        {
            "VARIABLE_NAME" : ["VARIABLE_VALUE", "ANOTHER_VARIABLE_VALUE"],
            "mode" : "append"
        }
    ]
    
    2 modes are available: append and replace, doing what they mean.
    """
    
    _variables = {}
    _var_regex = None

    def __init__(self):
        """
        """
        for var, value in os.environ.items():
            self._variables[var] = filesys.clean_path(value)

        app_name = conf.Config().get("app_name")
        app_root = filesys.clean_path(conf.Config().get("app_root"))

        self._variables[f"{app_name.upper()}_ROOT"] = conf.Config().get("app_root")
        self._variables[f"{app_name.upper()}_LIB"] = f"{app_root}/library"
        self._variables[f"{app_name.upper()}_ICONS"] = f"{app_root}/library/icons"
        self._variables[f"{app_name.upper()}_PREFS"] = f"{filesys.get_documents_folder()}/{app_name}"
        self._variables[f"{app_name.upper()}_PORT"] = 45678
        
        if not os.path.exists(self.get("BOLT_PREFS")):
            os.makedirs(self.get("BOLT_PREFS"))
        
    def get(self, key : str) -> str:
        """
        """
        if key in self._variables:
            return self._variables[key]
        else:
            return ""

    def set(self, key : str, value : str) -> None:
        """
        """
        self._variables[key] = value
        
    def build_environment_from_files(self) -> None:
        """
        Go through all files found in /env folders and parse them to add to
        update the environment
        """
        app_name = conf.Config().get("app_name")
        app_root = self.get(f"{app_name.uppper()}_ROOT")

        bolt_envs = self.get(f"{app_name.upper()}_ENVS")
        
        if len(bolt_envs) == 0:
            bolt_envs = f"{app_root}/env"
        else:
            bolt_envs += f"{os.pathsep}{app_root}/env"
        
        prefs_dir = self.get(f"{app_name.upper()}_PREFS")
        
        if os.path.exists(f"{prefs_dir}/env"):
            bolt_envs += f"{os.pathsep}{prefs_dir}/env"
            
        for path in bolt_envs.split(os.pathsep):
            eval_path = self.expand_string(path)
            
            if os.path.exists(eval_path):
                for file in os.listdir(eval_path):
                    if ".env" in file:
                        with open(f"{eval_path}/{file}") as f:
                            try:
                                data = json.load(f)
                                
                                for env in data:
                                    for key, value in env.items():
                                        if key == "mode":
                                            continue
                                        else:
                                            old_env_value = ""
                                            
                                            if env["mode"] == "append":
                                                old_env_value = self.get(key)
                                                
                                                if old_env_value == "":
                                                    if isinstance(value, list):
                                                        for i, env_val in enumerate(value):
                                                            if i == 0:
                                                                old_env_value += f"{env_val}"
                                                            else:
                                                                old_env_value += f";{env_val}"
                                                    else:
                                                        old_env_value = value
                                                else:
                                                    if isinstance(value, list):
                                                        for env_val in value:
                                                            old_env_value += f";{env_val}"
                                                    else:
                                                        old_env_value += f";{value}"
                                            else:
                                                if isinstance(value, list):
                                                    for i, env_val in enumerate(value):
                                                        if i == 0:
                                                            old_env_value = f"{env_val}"
                                                        else:
                                                            old_env_value += f";{env_val}"
                                                else:
                                                    old_env_value = value
                                                    
                                            self.set(key, old_env_value)
                                                
                            except ValueError:
                                log.error(f"Error during json decoding, file \"{eval_path}/{file}\" will be discarded")
            else:
                log.error(f"Error during environment building, directory \"{eval_path}\" does not exist")
                        
    def build_regex(self) -> re.Pattern:
        """
        """
        var_regex = r""

        for i, var in enumerate(self._variables):
            if i == 0:
                var_regex += fr"\$\({var}\)"
            else:
                var_regex += fr"|\$\({var}\)"

        return re.compile(var_regex)

    def search_in_string(self, string: str) -> bool:
        """
        """
        var_pattern = self.build_regex()

        return re.search(var_pattern, string) is not None

    def expand_string(self, string: str) -> str:
        """
        """
        varPattern = self.build_regex()

        for match in re.finditer(varPattern, string):
            varName = match.group().replace("$", "")
            string = string.replace(match.group(), self.get(varName))

        return string


def setenv(key: str, value: str) -> None:
    Environment().set(key, value)


def getenv(key: str) -> str:
    return Environment().get(key)