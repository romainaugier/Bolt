import os, re, json

from BoltApi import BOLTROOT
from BoltApi.Core.FileSystem import *
from BoltApi.Core.Logger import *


class Environment():
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
    
    Variables = {}

    def __init__(self):
        """
        """
        for var, value in os.environ.items():
            self.Variables[var] = CleanPath(value)

        if IsExecutable():
            boltRoot = GetCurrentExecPath()
        else:
            boltRoot = BOLTROOT

        self.Variables["BOLT_ROOT"] = CleanPath(boltRoot)
        self.Variables["BOLT_LIB"] = f"{CleanPath(boltRoot)}/Library"
        self.Variables["BOLT_ICONS"] = f"{CleanPath(boltRoot)}/Library/Icons"
        self.Variables["BOLT_PREFS"] = f"{GetDocumentsFolder()}/Bolt"
        
        if not os.path.exists(self.Get("BOLT_PREFS")):
            os.makedirs(self.Get("BOLT_PREFS"))
        
        if IsExecutable():
            self.Variables["BOLT_COMMAND"] = f"{CleanPath(boltRoot)}/bin/BoltCommand.exe"
        else:
            self.Variables["BOLT_COMMAND"] = f"{CleanPath(boltRoot)}/BoltCommand/Command.py"

    def Get(self, varName : str) -> str:
        """
        """
        if varName in self.Variables:
            return self.Variables[varName]
        else:
            return ""

    def Set(self, varName : str, varValue : str) -> None:
        """
        """
        self.Variables[varName] = varValue
        
    def BuildEnvironmentFromFiles(self, logger : Logger) -> None:
        """
        Go through all files found in /env folders and parse them to add to
        update the environment
        """
        boltEnvs = self.Get("BOLT_ENVS")
        
        if len(boltEnvs) == 0:
            boltEnvs = f"{self.Get('BOLT_ROOT')}/env"
        else:
            boltEnvs += f"{os.pathsep}{self.Get('BOLT_ROOT')}/env"
        
        prefsDir = self.Get("BOLT_PREFS")
        
        if os.path.exists(f"{prefsDir}/env"):
            boltEnvs += f"{os.pathsep}{prefsDir}/env"
            
        for path in boltEnvs.split(os.pathsep):
            evalPath = self.ReplaceInString(path)
            
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
                                                oldEnvValue = self.Get(key)
                                                
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
                                                    
                                            self.Set(key, oldEnvValue)
                                                
                            except ValueError:
                                logger.Log(LogLevel.ERROR, f"Error during json decoding, file ({evalPath}/{file}) will be discarded")
            else:
                logger.Log(LogLevel.ERROR, f"Error during environment building, directory ({evalPath}) does not exist")
                        
    def BuildRegex(self) -> re.Pattern:
        """
        """
        varRegex = r""

        for i, var in enumerate(self.Variables):
            if i == 0:
                varRegex += fr"\${var}"
            else:
                varRegex += fr"|\${var}"

        return re.compile(varRegex)

    def SearchInString(self, string : str) -> bool:
        """
        """
        varPattern = self.BuildRegex()

        return re.search(varPattern, string) is not None

    def ReplaceInString(self, string : str) -> str:
        """
        """
        varPattern = self.BuildRegex()

        for match in re.finditer(varPattern, string):
            varName = match.group().replace("$", "")
            string = string.replace(match.group(), self.Get(varName))

        return string
