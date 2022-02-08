import sys, os, copy

from FlashApi.Core.Node import *


class Lib():
    """
    Library that manages the nodes definitions
    """
    def __init__(self):
        """
        """
        self.path = [f"{os.path.dirname(sys.executable)}/Library/Nodes", "D:/dev/Flash/Library/Nodes"]

        self.nodes = {}

    def Load(self) -> None:
        """
        Load the nodes
        """
        for path in self.path:
            if os.path.exists(path):
                for item in os.listdir(path):
                    if item.endswith(".fnode"):
                        tmpNode = Node()
                        tmpNode.Load(f"{path}/{item}")

                        self.nodes[tmpNode.GetName()] = tmpNode

    def Reload(self) -> None:
        """
        Reload all the nodes
        """
        self.nodes.clear()
        self.Load()

    def GetAvailableNodes(self) -> list[str]:
        """
        Returns a list with the available node types

        Returns:
            list[str]: loaded node types
        """
        return [nodeType for nodeType in self.nodes]

    def Get(self, nodeName : str) -> Node:
        """
        Returns a deepcopy of the queried node

        Args:
            nodeName (str): node name

        Returns:
            Node: node instance
        """
        if nodeName in self.nodes:
            return copy.deepcopy(self.nodes[nodeName])
        else:
            return None
