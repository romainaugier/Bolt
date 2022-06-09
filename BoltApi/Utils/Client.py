import subprocess, os

import BoltApi.Core.FileSystem as FileSystem
import BoltApi.Core.Logger as Logger

"""
This file contains the functions exposed to the client to ease the development 
of node ops
"""

# FileSystem

def GetLastVersionDir(directory : str) -> str:
    """
    """
    assert os.path.exists(directory), f"Directory ({directory}) does not exist"
    
    return FileSystem.GetLastVersionDir(directory)

def CleanPath(path : str) -> str: 
    """
    """
    return FileSystem.CleanPath(path)

def GetNewRandomPyFile() -> str:
    """
    """
    return FileSystem.GetNewRandomPyFile()

def GetRoamingDataDir() -> str:
    """
    """
    return FileSystem.GetRoamingDataDir()

def GetDocumentsFolder() -> str:
    """
    """
    return FileSystem.GetDocumentsFolder()

def SafeCopy(src : str, dst : str) -> None:
    """
    """
    assert os.path.exists(src), f"File or directory ({src}) does not exist"
    
    return FileSystem.SafeCopy(src, dst)

# Subprocesses

class Process():
    """
    Simple class to manage a process
    """
    def __init__(self, execPath : str, args = None):
        assert os.path.exists(execPath), f"Executable path ({execPath}) does not exist"
        self.execPath = execPath
        
        if args is not None:
            assert isinstance(args, list), f"Process arguments must be a list of strings"
        
        self.args = args
        
        self.command = [self.execPath]
        self.command.extend(self.args)
        
    def Launch(self):
        """
        Launches the process
        """
        self.__process = subprocess.Popen(self.command, stdout=StdOut, stderr=StdErr)