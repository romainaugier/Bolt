from re import search
import sys, os, copy

from BoltApi.Core.Node import *
from BoltApi.Core.Logger import *
from BoltApi.Core.Environment import *


class Lib():
    """
    Library that manages the nodes definitions
    """
    def __init__(self, logger : Logger, environment : Environment):
        """
        """
        self.logger = logger
        self.environment = environment

        self.path = [f"$BOLT_LIB/Nodes"]

        searchPaths = ""

        for path in self.path:
            searchPaths += f"- {path}\n"

        self.logger.Log(LogLevel.DIAGNOSTIC, f"(Node Library) : Initializating library and looking for nodes in :\n{searchPaths}\n")

        self.nodePaths = {}

    def Load(self) -> None:
        """
        Load the nodes path
        """
        foundIfNode = False
        foundForNode = False
        
        for path in self.path:
            rawPath = path
            path = self.environment.ReplaceInString(path)
            
            if os.path.exists(path):
                for item in os.listdir(path):
                    if item.endswith(".bnode"):
                        if item.startswith("if"):
                            if not foundIfNode:
                                foundIfNode = True
                                
                                self.nodePaths[f"Utility/If_Block"] = [f"{path}/ifbegin.bnode", f"{path}/ifend.bnode"]
                                
                            continue
                        
                        if item.startswith("for"):
                            if not foundForNode:
                                foundForNode = True
                                
                                self.nodePaths[f"Utility/For_Block"] = [f"{path}/forbegin.bnode", f"{path}/forend.bnode"]
                                
                            continue
                        
                        tmpNode = Node(self.environment)
                        tmpNode.Load(f"{path}/{item}")

                        self.nodePaths[f"{tmpNode.GetCategory()}/{tmpNode.GetName()}"] = f"{rawPath}/{item}"

                        self.logger.Log(LogLevel.DEBUG, f"Loaded node : {tmpNode.GetCategory()}/{tmpNode.GetName()}")

    def Reload(self) -> None:
        """
        Reload all the nodes
        """
        self.nodePaths.clear()
        self.Load()

    def GetAvailableNodes(self) -> list:
        """
        Returns a list with the available node types

        Returns:
            list[str]: loaded node types
        """
        return [nodeType for nodeType in self.nodePaths]

    def Get(self, nodeName : str) -> Node:
        """
        Returns a new node of the queried type

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

    def GetPath(self, nodeName : str) -> str:
        """
        """
        if nodeName in self.nodePaths:
            return self.nodePaths[nodeName]
        else:
            return None
