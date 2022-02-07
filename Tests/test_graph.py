import sys, os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from FlashApi.Core.Node import *
from FlashApi.Core.Graph import *

if __name__ == "__main__":
    print("Testing Flash Graph API...")

    graph = Graph()

    for i in range(5):
        tempNode = Node()
        tempNode.inputCount = 2
        tempNode.inputs = [Plug("input1", tempNode), Plug("input2", tempNode)]
        tempNode.outputCount = 1
        tempNode.outputs = [Plug("output1", tempNode)]
        tempNode.SetName(f"node{i}")

        graph.AddNode(tempNode)

    graph.nodes[3].SetInput(graph.nodes[1].GetOutput(0), 0)
    graph.nodes[1].SetInput(graph.nodes[2].GetOutput(0), 0)
    graph.nodes[2].SetInput(graph.nodes[0].GetOutput(0), 0)
    graph.nodes[2].SetInput(graph.nodes[4].GetOutput(0), 1)
    graph.nodes[4].SetInput(graph.nodes[0].GetOutput(0), 0)

    graph.Sort()

    for node in graph.sortedNodes:
        print(node.name)