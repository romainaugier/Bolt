import os, re

from FlashApi import FLASHROOT
from FlashApi.Core.FileSystem import CleanPath

class Environment():
    """
    Contains all the environment variables and the utils to find and replace them
    in a string
    All environment variables written in a string should begin with $ and be capital letters,
    with underscores for separation

    For example : $FLASH_ROOT, $CGDIR, $CGNAME
    """

    Variables = {}

    def __init__(self):
        """
        """
        for var, value in os.environ.items():
            self.Variables[var] = CleanPath(value)

        self.Variables["FLASH_ROOT"] = CleanPath(FLASHROOT)
        self.Variables["FLASH_LIB"] = f"{CleanPath(FLASHROOT)}/Library"
        self.Variables["FLASH_ICONS"] = f"{CleanPath(FLASHROOT)}/Library/Icons"

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