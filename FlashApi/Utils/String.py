import re


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