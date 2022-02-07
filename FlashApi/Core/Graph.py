import binascii, os, copy
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
        self.sortedNodes.clear()

        while self.HasNodesToSort():
            nodeToSort = self.GetNodeToSort()
            self.VisitNode(nodeToSort)

    def Cook(self) -> None:
        """
        """
        pass

    def AddNode(self, node : Node) -> None:
        """
        """
        node.SetID(binascii.hexlify(os.urandom(16)))

        self.nodes.append(node)

    def RemoveNode(self, node : Node) -> None:
        """
        """
        self.nodes.remove(node)