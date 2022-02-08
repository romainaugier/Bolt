import binascii, os, time, threading, json
from FlashApi.Core.Node import Node


class Graph():
    """
    """
    def __init__(self):
        """
        """
        self.nodes : list[Node] = []
        self.sortedNodes : list[Node] = []
        self.nodeCount = 0
        self.cookingThread = threading.Thread(target=Graph.Cook, args=(self,))
        self.cookingThread.start()

    def __del__(self):
        """
        """
        self.cookingThread.join()

    def SetAllDirty(self) -> None:
        """
        """
        for node in self.nodes:
            node.SetDirty()

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

        for output in node.GetOutputs():
            if output.IsConnected():
                self.VisitNode(output.Connection().Node())

        node.SetInTempQueue(False)
        node.SetInQueue()
        self.sortedNodes.insert(0, node)

    def Sort(self) -> None:
        """
        Depth-First search to traverse and sort the nodes to cook
        the graph
        """
        for node in self.nodes:
            node.SetInQueue(False)
            node.SetInTempQueue(False)

        self.sortedNodes.clear()

        while self.HasNodesToSort():
            nodeToSort = self.GetNodeToSort()
            self.VisitNode(nodeToSort)

    def Cook(self) -> None:
        """
        """
        self.Sort()

        for node in self.sortedNodes:
            node.Cook()

    def StartCook(self) -> None:
        """
        """
        self.cookingThread.run()

    def AddNode(self, node : Node) -> None:
        """
        """
        node.SetID(binascii.hexlify(os.urandom(16)).hex())

        self.nodes.append(node)

        self.nodeCount += 1

    def RemoveNode(self, node : Node) -> None:
        """
        """
        self.nodes.remove(node)

        self.nodeCount -= 1

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
            tmpNode = Node()
            tmpNode.FromDict(node)
            self.nodes.append(tmpNode)

        # Connect nodes
        for i, node in enumerate(nodesAsDicts):
            
            j = 0

            for outputName, outputContent in node["outputs"].items():
                nodeToConnect = self.GetNodeWithID(outputContent["connectionNodeId"])
                nodeToConnect.SetInput(self.nodes[i].GetOutput(j), outputContent["connectionIndex"])

                j += 1
