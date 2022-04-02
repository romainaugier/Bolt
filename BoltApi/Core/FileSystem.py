import sys, pathlib, os, binascii, shutil, subprocess, re

from BoltApi.Utils.String import GetCurrentTimeAsStr, GetRandomStrId


def GetDocumentsFolder() -> str:
    """
    Returns the path to the user documents folder 

    Returns:
        str: path to the user documents folder
    """
    if sys.platform == "win32":
        path = subprocess.check_output(["powershell", "[Environment]::GetFolderPath(\"MyDocuments\")"])
        pathDecoded = path.decode()
        pathClean = pathDecoded.replace("\n", "")
        pathClean = pathClean.replace("\r", "")
        pathClean = pathClean.replace("\\", "/")
        return pathClean
    else:
        return None

def GetRoamingDataDir() -> str:
    """
    Returns a parent directory path
    where persistent application data can be stored.

    linux: ~/.local/share
    macOS: ~/Library/Application Support
    windows: C:/Users/<USER>/AppData/Roaming
    """

    home = pathlib.Path.home()

    boltRoamingDataDirPath = ""

    if sys.platform == "win32":
        boltRoamingDataDirPath = str(home / "AppData/Roaming/Bolt")
    elif sys.platform == "linux":
        boltRoamingDataDirPath = str(home / ".local/share/Bolt")
    elif sys.platform == "darwin":
        boltRoamingDataDirPath = str(home / "Library/Application Support/Bolt")

    if not os.path.exists(boltRoamingDataDirPath):
        os.makedirs(boltRoamingDataDirPath)

    return boltRoamingDataDirPath

def GetNewRandomPyFile() -> str:
    """
    Returns a path to a script file with a randomly generated name
    stored in the Bolt roaming data dir (the file will not be created)

    Returns:
        str: path to the file
    """
    return f"{GetRoamingDataDir()}/{binascii.hexlify(os.urandom(16)).hex()}.py"

def CleanPath(path : str) -> str:
    """
    """
    return path.replace("\\", "/")

def IsExecutable() -> bool:
    """
    Returns True if the program has been built as an executable, and False
    if the program is ran with python

    Returns:
        bool: ^
    """
    if "python.exe" in sys.executable:
        return False
    else:
        return True

def GetCurrentExecPath() -> str:
    """
    Returns the path to the directory of the current executable

    Returns:
        str: path to the directory of the current executable
    """
    return os.path.dirname(sys.executable)

def GetJobsDir() -> str:
    """
    Returns the path to the roaming jobs directory, where
    jobs from the JobSystem are located
    
    Returns:
        str: path to the roaming jobs directory
    """
    jobsDirPath = f"{GetRoamingDataDir()}/jobs"
    
    if not os.path.exists(jobsDirPath):
        os.makedirs(jobsDirPath)
        
    return jobsDirPath

def CopyJob(jobId : str, pathToGraph : str) -> tuple:
    """
    Copies the given graph file to the roaming jobs dir with a random name

    Args:
        pathToGraph (str): path to the graph file to copy
        
    Returns:
        tuple(str): job directory path and copied graph file path
    """
    if not os.path.exists(pathToGraph):
        raise ValueError
    
    graphName, graphExtension = os.path.splitext(os.path.basename(pathToGraph))
    
    jobDirName = jobId
    jobDirPath = f"{GetJobsDir()}/{jobDirName}"
    
    os.makedirs(jobDirPath)
    
    jobName = f"{graphName}_{GetCurrentTimeAsStr()}.{graphExtension}"
    jobPath = f"{jobDirPath}/{jobName}"
    
    shutil.copy(pathToGraph, jobPath)
    
    return jobDirPath, jobPath

def GetLastVersionDir(directory : str) -> str:
    """
    Returns the path to the last version of the directory. For example,
    when you have multiple "0000", "0001", "0002"... directories, 
    it finds the last one and return the full path to it

    Args:
        directory (str): directory containing the multiple directory versions

    Returns:
        str: full path to the last version of the directory
    """
    lastVersionPath = ""
    lastVersionNum = -1
    noNumPattern = re.compile(r"[^\d+]")
    
    for dir in os.listdir(directory):
        fullPath = f"{directory}/{dir}"
        
        if not os.path.isdir(fullPath):
            continue
        else:
            dirAsNum = int(re.sub(noNumPattern, "", dir))
            
            if dirAsNum > lastVersionNum:
                lastVersionPath = fullPath
                lastVersionNum = dirAsNum
                
    assert(len(lastVersionPath) > 0)
                
    return lastVersionPath.replace("\\", "/")
        