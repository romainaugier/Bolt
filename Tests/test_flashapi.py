import sys, os, copy, json

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from FlashApi.Core.Node import *
from FlashApi.Core.Graph import *
from FlashApi.Core.Lib import *

if __name__ == "__main__":
    print("Testing Flash Graph API...")

    print("Initializing node library...")
    nodeLib = Lib()
    nodeLib.Load()

    print("Available nodes : ")
    print(json.dumps(nodeLib.GetAvailableNodes(), indent=4))

    graph = Graph()

    print("Setting up nodes...")

    hythonNode1 = nodeLib.Get("Hython")
    printNode1 = nodeLib.Get("Print")

    fileNode1 = nodeLib.Get("File")
    fileNode1.SetParm("filepath", "Z:/OEUF/assets/props/Volcan/modeling/main/Houdini/export/water_plane.abc")

    hou_loadalembicNode1 = nodeLib.Get("Hou_LoadAlembic")
    hou_loadalembicNode1.SetParm("file", "D:/test.hip")


    print("Adding nodes to graph...")

    graph.AddNode(hythonNode1)
    graph.AddNode(printNode1)
    graph.AddNode(hou_loadalembicNode1)
    graph.AddNode(fileNode1)

    print("Nodes in graph : ")
    print(json.dumps([node.GetName()for node in graph.nodes], indent=4))

    print("Connecting nodes...")

    hou_loadalembicNode1.SetInput(fileNode1.GetOutput(0), 0)
    printNode1.SetInput(hou_loadalembicNode1.GetOutput(0), 0)
    hythonNode1.SetInput(printNode1.GetOutput(0), 0)

    print("Cooking Graph...")

    graph.Cook()

    print("Sorted nodes : ")
    print(json.dumps([node.GetName() for node in graph.sortedNodes], indent=4))

    print("Serializing Graph...")

    serializedGraph = graph.Serialize()

    print("Deserializing Graph...")

    graph.Deserialize(serializedGraph)

    print("Cooking Graph...")

    graph.Cook()

    print("Sorted nodes : ")
    print(json.dumps([node.GetName() for node in graph.sortedNodes], indent=4))