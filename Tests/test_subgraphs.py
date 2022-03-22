import os, sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from Tests.test import *

if __name__ == "__main__":
    logger = Logger(level=LogLevel.DEBUG)
    
    environment = Environment()
    nodeLibrary = Lib(logger, environment)
    nodeLibrary.Load()

    PrintSeps()
    
    logger.Log(LogLevel.DEBUG, "Testing subgraphs...")
    
    graph = Graph(logger, environment, "test_graph")
    
    fileNode = nodeLibrary.Get("Utility/File")
    fileNode.SetPlugValue("infile", "prout")
    graph.AddNode(fileNode)
    debugNode = nodeLibrary.Get("Debug/Debug")
    graph.AddNode(debugNode)
    
    subGraphNode = SubGraph(environment, logger)
    subGraphNode.Initialize()
    
    subGraphDebugNode = nodeLibrary.Get("Debug/Debug")
    subGraphNode.graph.AddNode(subGraphDebugNode)
    
    subGraphNode.inputNode["input1"] >> subGraphDebugNode["indata"]
    subGraphDebugNode["outdata"] >> subGraphNode.outputNode["output1"]
    
    subGraphNode.graph.Sort()
    
    print(json.dumps([node.GetName() for node in subGraphNode.graph.sortedNodes], indent=2))
    
    graph.AddNode(subGraphNode)
    
    fileNode["outfile"] >> subGraphNode["input1"]
    subGraphNode["output1"] >> debugNode["indata"]
    
    graph.SaveToFile(f"{TESTDIR}/test_subgraphs.bgraph")
    
    graph.Cook()
    
    
    
    
    