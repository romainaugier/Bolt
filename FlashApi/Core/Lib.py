from re import search
import sys, os, copy

from FlashApi.Core.Node import *
from FlashApi.Core.Logger import *
from FlashApi.Core.Environment import *


class Lib():
    """
    Library that manages the nodes definitions
    """
    def __init__(self, logger : Logger, environment : Environment):
        """
        """
        self.logger = logger
        self.environment = environment

        self.path = [f"{self.environment.Get('FLASH_LIB')}/Nodes"]

        searchPaths = ""

        for path in self.path:
            searchPaths += f"- {path}\n"

        self.logger.Log(LogLevel.DIAGNOSTIC, f"(Node Library) : Initializating library and looking for nodes in :\n{searchPaths}")

        self.nodePaths = {}

    def Load(self) -> None:
        """
        Load the nodes path
        """
        for path in self.path:
            if os.path.exists(path):
                for item in os.listdir(path):
                    if item.endswith(".fnode"):
                        tmpNode = Node(self.environment)
                        tmpNode.Load(f"{path}/{item}")

                        self.nodePaths[tmpNode.GetName()] = f"{path}/{item}"

                        self.logger.Log(LogLevel.DEBUG, f"Loaded {tmpNode.GetName()}")

    def Reload(self) -> None:
        """
        Reload all the nodes
        """
        self.nodePaths.clear()
        self.Load()

    def GetAvailableNodes(self) -> list[str]:
        """
        Returns a list with the available node types

        Returns:
            list[str]: loaded node types
        """
        return [nodeType for nodeType in self.nodePaths]

    def Get(self, nodeName : str) -> Node:
        """
        Returns a deepcopy of the queried node

        Args:
            nodeName (str): node name

        Returns:
            Node: node instance
        """
        if nodeName in self.nodePaths:
            newNode = Node(self.environment)
            newNode.Load(self.nodePaths[nodeName])
            newNode.SetLogger(self.logger)
            return newNode
        else:
            return None
