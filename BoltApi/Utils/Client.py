import BoltApi.Core.FileSystem as FileSystem

"""
This file contains the functions exposed to the client to ease the development 
of node ops
"""

# FileSystem

def GetLastVersionDir(directory : str) -> str:
    """
    """
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