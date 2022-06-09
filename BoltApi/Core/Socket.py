import socket, errno


def CheckIfPortIsUsed(port : int) -> bool:
    """
    Checks if a port is used or not

    Args:
        port (int) : port to check

    Returns:
        bool: True if the port is used, False otherwise
    """
    if isinstance(port, str):
        port = int(port)
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) == 0