import re, os, binascii
from datetime import datetime

def Increment(string : str) -> str:
    """
    Increments the value in a string

    For example, node1 will be node2. If no value to increment is found,
    adds 1 at the end of the string

    Args:
        string (str): string to increment

    Returns:
        str: string incremented
    """
    numPattern = r"\d+"

    hasValue = False

    for match in re.finditer(numPattern, string):
        value = int(match.group())

        value += 1

        string = string.replace(match.group(), f"{value}")

        hasValue = True

    if not hasValue:
        string = f"{string}1"

    return string

def GetCurrentTimeAsStr(format : str = "%m%d%Y_%H%M%S") -> str:
    """
    Returns the current date and time as a string

    Args:
        format (str): format of the date and time. Defaults to "%m%d%Y_%H%M%S"

    Returns:
        str: current date and time
    """
    now = datetime.now()

    currentTimeStr = now.strftime(format)

    return currentTimeStr

def GetRandomStrId(bytes : int = 16) -> str:
    """
    Returns a random id as a string
    
    Args:
        bytes (int): number of bytes to generate the id
    """
    return binascii.hexlify(os.urandom(bytes)).hex()