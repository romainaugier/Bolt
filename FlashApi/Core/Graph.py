import binascii, os, time, threading, json, copy

from FlashApi.Core.Node import *
from FlashApi.Core.Logger import *
from FlashApi.Core.Environment import *


class Graph():
    """
    """
    def __init__(self, logger : Logger, environment : Environment, name : str = ""):
        """
        """
        self.logger = logger
        self.environment = copy.deepcopy(environment)
        self.name = name
        self.savePath = ""
        self.hasError = False
        self.nodes : list[Node] = []
        self.sortedNodes : list[Node] = []
        self.nodeCount = 0

        self.UpdateEnv()

    def GetName(self) -> str:
        """
        """
        return self.name

    def GetSavePath(self) -> str:
        """
        """
        return self.savePath

    def GetNodes(self) -> list[Node]:
        """
        Returns:
            list[Node]: nodes of the graph
        """
        return self.nodes

    def SetAllDirty(self) -> None:
        """
        """
        for node in self.nodes:
            node.SetDirty()

    def UpdateEnv(self) -> None:
        """
        """
        self.environment.Set("GRAPH_NAME", self.name)
        self.environment.Set("GRAPH_DIR", os.path.dirname(self.savePath))

        for node in self.nodes:
            node.UpdateEnv(self.environment)

    def GetEnv(self) -> Environment:
        """
        """
        return self.environment

    def HasNodesToSort(self) -> bool:
        """
        Search if there are still nodes to sort in the graph

        Returns:
            bool: if there are node to sort
        """
        for node in self.nodes:
            if not node.InQueue():
                return True

        return False

    def GetNodeToSort(self) -> Node:
        """
        """
        for node in self.nodes:
            if not node.InQueue():
                return node

        return None

    def VisitNode(self, node : Node) -> None:
        """
        """
        if node.InQueue():
            return
        elif node.InTempQueue():
            return

        node.SetInTempQueue()

        for outputName, output in node.GetOutputs().items():
            if output.IsConnected():
                for connection in output.GetConnections():
                    self.VisitNode(connection.GetNode())

        node.SetInTempQueue(False)
        node.SetInQueue()
        self.sortedNodes.insert(0, node)

    def Sort(self) -> None:
        """
        Depth-First search to traverse and sort the nodes to cook
        the graph
        """
        self.logger.Log(LogLevel.DIAGNOSTIC, f"(Graph : {self.name}) : Sorting nodes")

        for node in self.nodes:
            node.SetInQueue(False)
            node.SetInTempQueue(False)

        self.sortedNodes.clear()

        while self.HasNodesToSort():
            nodeToSort = self.GetNodeToSort()
            if nodeToSort.HasInputsNotConnected():
                nodeToSort.ReportError()
                self.ReportError()
                self.logger.Log(LogLevel.ERROR, f"(Graph : {self.name}) : Error in node sorting. Node [{nodeToSort.GetName()}] has unconnected input(s)")
                break

            self.VisitNode(nodeToSort)

        if not self.hasError:        
            self.logger.Log(LogLevel.DIAGNOSTIC, f"(Graph : {self.name}) : Nodes sorted")

    def Cook(self) -> None:
        """
        """
        self.hasError = False
        self.SetAllDirty()

        self.logger.Log(LogLevel.DIAGNOSTIC, f"(Graph : {self.name}) : Cooking graph")
        
        self.Sort()

        if not self.hasError:
            for node in self.sortedNodes:
                node.Cook()

                # Check for errors
                if node.hasError:
                    self.ReportError()
                    self.logger.Log(LogLevel.ERROR, f"(Graph : {self.name}) : Error in cooking node [{node.GetName()}]. Check the log for more details")
                    break
                else:
                    self.logger.Log(LogLevel.DIAGNOSTIC, f"(Graph : {self.name}) : Cooked node [{node.GetName()}]")

            if not self.hasError:
                self.logger.Log(LogLevel.DIAGNOSTIC, f"(Graph : {self.name}) : Graph cooked")

    def ReportError(self) -> None:
        """
        Emits an error
        """
        self.hasError = True

    def AddNode(self, node : Node) -> None:
        """
        """
        node.SetID(binascii.hexlify(os.urandom(16)).hex())

        self.nodes.append(node)

        self.nodeCount += 1
        
        self.logger.Log(LogLevel.DIAGNOSTIC, f"(Graph : {self.name}) : Added node [{node.GetName()}]")

    def RemoveNode(self, node : Node) -> None:
        """
        """
        for input in node.GetInputs().values():
            for connection in input.GetConnections():
                input.Disconnect(connection)

        for output in node.GetOutputs().values():
            for connection in output.GetConnections():
                output.Disconnect(connection)

        self.nodes.remove(node)

        self.nodeCount -= 1

        self.logger.Log(LogLevel.DIAGNOSTIC, f"(Graph : {self.name}) : Removed node [{node.GetName()}]")

    def GetNodeWithID(self, id : str) -> Node:
        """
        Returns a node given an id. None if the node can't be found

        Args:
            id (str): node id

        Returns:
            Node: found node
        """
        for node in self.nodes:
            if node.GetID() == id:
                return node
        
        return None

    def GetNodeWithName(self, name : str) -> Node:
        """
        Returns a node given a name. None if te node can't be found

        Args:
            name (str): node name

        Returns:
            Node: found node
        """
        for node in self.nodes:
            if node.GetName() == name:
                return node

        return None

    def Serialize(self) -> str:
        """
        Serializes the graph to a json string

        Returns:
            str: serialized content
        """
        nodesAsDicts = []

        for node in self.nodes:
            nodesAsDicts.append(node.ToDict())

        return json.dumps(nodesAsDicts, indent=2)

    def Deserialize(self, serializedGraph : str) -> None:
        """
        Loads a graph from a serialized one

        Args:
            serializedGraph (str): serialized graph
        """
        self.nodes.clear()
        self.sortedNodes.clear()

        nodesAsDicts = json.loads(serializedGraph)

        for node in nodesAsDicts:
            tmpNode = Node(self.environment)
            tmpNode.SetLogger(self.logger)
            tmpNode.FromDict(node)
            self.nodes.append(tmpNode)

        # Connect nodes
        for i, node in enumerate(nodesAsDicts):
            for outputName, outputContent in node["outputs"].items():
                for connection in outputContent:
                    if connection["connectionNodeId"] is not None:
                        nodeToConnect = self.GetNodeWithID(connection["connectionNodeId"])
                        nodeToConnect.SetInput(self.nodes[i].GetOutput(name=outputName), name=connection["connectionName"])

    def SaveToFile(self, filePath : str, saveAsString : bool = True) -> None:
        """
        Saves the graph to a scene file and sets its name to the given filename

        Args:
            filePath (str): path of the file
        """
        if not os.path.exists(os.path.dirname(filePath)):
            os.makedirs(os.path.dirname(filePath))

        self.name, _ = os.path.splitext(os.path.basename(filePath))
        self.savePath = filePath

        if saveAsString:
            with open(filePath, "w") as file:
                serializedGraph = self.Serialize()
                file.write(serializedGraph)
        else:
            with open(filePath, "wb") as file:
                serializedGraph = self.Serialize().encode("utf-8")
                file.write(serializedGraph)

        self.UpdateEnv()

    def LoadFromFile(self, filePath : str) -> None:
        """
        Loads a graph from a file

        Args:
            filePath (str): file to load the graph from
        """
        if self.environment.SearchInString(filePath):
            filePath = self.environment.ReplaceInString(filePath)

        if not os.path.exists(filePath):
            self.logger.Log(LogLevel.ERROR, f"Can't load graph from file {filePath}, it does not exist")
        else:
            self.savePath = filePath
            self.name, _ = os.path.splitext(os.path.basename(filePath))

            with open(filePath, "r", encoding="utf-8") as file:
                self.Deserialize(file.read())

        self.UpdateEnv()