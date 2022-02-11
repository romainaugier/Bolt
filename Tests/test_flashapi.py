import sys, os, copy, json

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from FlashApi.Core.Node import *
from FlashApi.Core.Graph import *
from FlashApi.Core.Lib import *
from FlashApi.Core.Logger import *

TESTDIR = os.path.dirname(__file__)

def PrintSeps():
    print(f"\n{'#' * 30}\n")

if __name__ == "__main__":
    logger = Logger(level=LogLevel.DEBUG)
    
    logger.Log(LogLevel.DEBUG, "Testing Flash API...")

    logger.Log(LogLevel.DEBUG, "Testing template node...")
    
    PrintSeps()

    node = Node()
    node.Load("D:/dev/Flash/Library/Nodes/template.fnode")
    node.SetLogger(logger)

    for inputName, input in node.GetInputs().items():
        print(inputName, input.GetLongName(), input.GetData(), input.GetType())
    
    for outputName, output in node.GetOutputs().items():
        print(outputName, output.GetLongName(), output.GetData(), output.GetType())

    PrintSeps()

    logger.Log(LogLevel.DEBUG, "Cooking template node...")

    node.Cook()
    
    PrintSeps()

    logger.Log(LogLevel.DEBUG, "Setting plug values in template node and re cooking it...")

    node.SetPlugValue("inint", 10)
    node.SetPlugValue("infloat", 58.0)
    node.SetPlugValue("instring", "Flash Test")
    node.SetPlugValue("inbool", False)
    node.SetPlugValue("incustom", node)
    node.SetPlugValue("indict", { "newdict" : True })

    node.Cook()

    PrintSeps()

    logger.Log(LogLevel.DEBUG, "Testing node library...")

    nodeLibrary = Lib(logger)
    nodeLibrary.Load()

    PrintSeps()

    logger.Log(LogLevel.DEBUG, "Testing graph...")

    graph = Graph(logger, "new")

    fileNode = nodeLibrary.Get("File")
    fileNode.SetPlugValue("infile", f"{TESTDIR}/test_script.py")

    debugNode = nodeLibrary.Get("Debug")

    pythonNode = nodeLibrary.Get("Python")

    logger.Log(LogLevel.DEBUG, "Adding nodes...")

    graph.AddNode(debugNode)
    graph.AddNode(pythonNode)
    graph.AddNode(fileNode)
    
    logger.Log(LogLevel.DEBUG, "Connecting Nodes...")

    debugNode.SetInput(fileNode.GetOutput(name="outfile"), name="indata")
    pythonNode.SetInput(debugNode.GetOutput(name="outdata"), name="inscript")

    for node in graph.GetNodes():
        PrintSeps()
        print(node.GetName())

        for inputName, input in node.GetInputs().items():
            print(input.GetLongName(), input.IsExposed(), input.GetData())

    PrintSeps()

    logger.Log(LogLevel.DEBUG, "Cooking graph...")

    graph.Cook()

    PrintSeps()

    logger.Log(LogLevel.DEBUG, "Serializing graph...")

    serializedGraph = graph.Serialize()

    print("\n", serializedGraph, "\n")

    PrintSeps()

    logger.Log(LogLevel.DEBUG, "Deserializing graph...")

    graph.Deserialize(serializedGraph)

    for node in graph.GetNodes():
        PrintSeps()
        print(node.GetName())

        for inputName, input in node.GetInputs().items():
            print(input.GetLongName(), input.IsExposed(), input.GetData())

    PrintSeps()

    logger.Log(LogLevel.DEBUG, "Cooking graph after deserialization...")

    graph.Cook()

    PrintSeps()

    logger.Log(LogLevel.DEBUG, "Saving to file...")

    graphSavePath = f"{TESTDIR}/tmp_graph.fgraph"

    graph.SaveToFile(graphSavePath)

    PrintSeps()

    logger.Log(LogLevel.DEBUG, "Loading from file...")

    graph.LoadFromFile(graphSavePath)

    PrintSeps()

    logger.Log(LogLevel.DEBUG, "Cooking graph after loading...")

    graph.Cook()

    PrintSeps()