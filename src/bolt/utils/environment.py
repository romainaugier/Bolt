import os
import re
import json

import bolt.log as log
import bolt.utils.filesystem as fs

from bolt.utils.singleton import Singleton



class Environment(Singleton):
    """
    Contains all the environment variables and the utils to find and replace them
    in a string
    All environment variables written in a string should begin with $ and be capital letters,
    with underscores for separation
    
    For example : $BOLT_ROOT, $GRAPH_DIR, $GRAPH_NAME
    
    To ease environment settings, you can provide files that can be located in the $BOLT_LIB/env or
    HOME/Documents/Bolt/env folders. 
    Those files should be named "whatever_you_want.benv" and be formatted as json files like the following :
    
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

    def __init__(self):
        """
        """
        for var, value in os.environ.items():
            self._variables[var] = fs.clean_path(value)

        self._variables["BOLT_ROOT"] = CleanPath(boltRoot)
        self._variables["BOLT_LIB"] = f"{CleanPath(boltRoot)}/Library"
        self._variables["BOLT_ICONS"] = f"{CleanPath(boltRoot)}/Library/Icons"
        self._variables["BOLT_PREFS"] = f"{fs.get_documents_folder()}/Bolt"
        self._variables["BOLT_PORT"] = 1
        
        if not os.path.exists(self.get("BOLT_PREFS")):
            os.makedirs(self.get("BOLT_PREFS"))
        
        if IsExecutable():
            self._variables["BOLT_COMMAND"] = f"{CleanPath(boltRoot)}/bin/BoltCommand.exe"
        else:
            self._variables["BOLT_COMMAND"] = f"{CleanPath(boltRoot)}/BoltCommand/Command.py"

    def get(self, varName : str) -> str:
        """
        """
        if varName in self._variables:
            return self._variables[varName]
        else:
            return ""

    def set(self, varName : str, varValue : str) -> None:
        """
        """
        self._variables[varName] = varValue
        
    def build_environment_from_files(self) -> None:
        """
        Go through all files found in /env folders and parse them to add to
        update the environment
        """
        boltEnvs = self.get("BOLT_ENVS")
        
        if len(boltEnvs) == 0:
            boltEnvs = f"{self.get('BOLT_ROOT')}/env"
        else:
            boltEnvs += f"{os.pathsep}{self.get('BOLT_ROOT')}/env"
        
        prefsDir = self.get("BOLT_PREFS")
        
        if os.path.exists(f"{prefsDir}/env"):
            boltEnvs += f"{os.pathsep}{prefsDir}/env"
            
        for path in boltEnvs.split(os.pathsep):
            evalPath = self.replace_in_string(path)
            
            if os.path.exists(evalPath):
                for file in os.listdir(evalPath):
                    if ".benv" in file:
                        with open(f"{evalPath}/{file}") as f:
                            try:
                                data = json.load(f)
                                
                                for env in data:
                                    for key, value in env.items():
                                        if key == "mode":
                                            continue
                                        else:
                                            oldEnvValue = ""
                                            
                                            if env["mode"] == "append":
                                                oldEnvValue = self.get(key)
                                                
                                                if oldEnvValue == "":
                                                    if isinstance(value, list):
                                                        for i, envVal in enumerate(value):
                                                            if i == 0:
                                                                oldEnvValue += f"{envVal}"
                                                            else:
                                                                oldEnvValue += f";{envVal}"
                                                    else:
                                                        oldEnvValue = value
                                                else:
                                                    if isinstance(value, list):
                                                        for envVal in value:
                                                            oldEnvValue += f";{envVal}"
                                                    else:
                                                        oldEnvValue += f";{value}"
                                            else:
                                                if isinstance(value, list):
                                                    for i, envVal in enumerate(value):
                                                        if i == 0:
                                                            oldEnvValue = f"{envVal}"
                                                        else:
                                                            oldEnvValue += f";{envVal}"
                                                else:
                                                    oldEnvValue = value
                                                    
                                            self.set(key, oldEnvValue)
                                                
                            except ValueError:
                                log.error("Error during json decoding, file ({evalPath}/{file}) will be discarded")
            else:
                log.error(f"Error during environment building, directory ({evalPath}) does not exist")
                        
    def build_regex(self) -> re.Pattern:
        """
        """
        varRegex = r""

        for i, var in enumerate(self._variables):
            if i == 0:
                varRegex += fr"\${var}"
            else:
                varRegex += fr"|\${var}"

        return re.compile(varRegex)

    def search_in_string(self, string: str) -> bool:
        """
        """
        varPattern = self.build_regex()

        return re.search(varPattern, string) is not None

    def replace_in_string(self, string: str) -> str:
        """
        """
        varPattern = self.build_regex()

        for match in re.finditer(varPattern, string):
            varName = match.group().replace("$", "")
            string = string.replace(match.group(), self.get(varName))

        return string
