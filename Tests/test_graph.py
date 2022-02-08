import sys, os, copy

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from FlashApi.Core.Node import *
from FlashApi.Core.Graph import *

if __name__ == "__main__":
    print("Testing Flash Graph API...")

    graph = Graph()

    fileNode = Node()
    fileNode.Load("D:/dev/Flash/Library/Nodes/file.fnode")

    printNode = Node()
    printNode.Load("D:/dev/Flash/Library/Nodes/print.fnode")

    hou_autoPlumeNode = Node()
    hou_autoPlumeNode.Load("D:/dev/Flash/Library/Nodes/hou_autoplume.fnode")

    hou_loadalembicNode = Node()
    hou_loadalembicNode.Load("D:/dev/Flash/Library/Nodes/hou_loadalembic.fnode")

    hythonNode = Node()
    hythonNode.Load("D:/dev/Flash/Library/Nodes/hython.fnode")

    fileNode1 = copy.deepcopy(fileNode)
    fileNode1.SetParm("filepath", "Z:/OEUF/assets/props/Volcan/modeling/main/Houdini/export/water_plane.abc")

    hou_loadalembicNode1 = copy.deepcopy(hou_loadalembicNode)
    hou_loadalembicNode1.SetParm("file", "D:/test.hip")

    printNode1 = copy.deepcopy(printNode)

    hythonNode1 = copy.deepcopy(hythonNode)

    graph.AddNode(fileNode1)
    graph.AddNode(hou_loadalembicNode1)
    graph.AddNode(printNode1)
    graph.AddNode(hythonNode1)

    hou_loadalembicNode1.SetInput(fileNode1.GetOutput(0), 0)
    printNode1.SetInput(hou_loadalembicNode1.GetOutput(0), 0)
    hythonNode1.SetInput(printNode1.GetOutput(0), 0)

    serializedGraph = graph.Serialize()

    graph.Deserialize(serializedGraph)

    graph.Sort()

    for node in graph.sortedNodes:
        print(node.GetName())