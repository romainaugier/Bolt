import sys, pathlib, os, binascii

def GetRoamingDataDir() -> str:
    """
    Returns a parent directory path
    where persistent application data can be stored.

    linux: ~/.local/share
    macOS: ~/Library/Application Support
    windows: C:/Users/<USER>/AppData/Roaming
    """

    home = pathlib.Path.home()

    flashRoamingDataDirPath = ""

    if sys.platform == "win32":
        flashRoamingDataDirPath = str(home / "AppData/Roaming/Flash")
    elif sys.platform == "linux":
        flashRoamingDataDirPath = str(home / ".local/share/Flash")
    elif sys.platform == "darwin":
        flashRoamingDataDirPath = str(home / "Library/Application Support/Flash")

    if not os.path.exists(flashRoamingDataDirPath):
        os.makedirs(flashRoamingDataDirPath)

    return flashRoamingDataDirPath


def GetNewRandomPyFile() -> str:
    """
    Returns a path to a script file with a randomly generated name
    stored in the flash roaming data dir (the file will not be created)

    Returns:
        str: path to the file
    """
    return "{}/{}.py".format(GetRoamingDataDir(), binascii.hexlify(os.urandom(16)).hex())


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