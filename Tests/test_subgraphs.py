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
    
    subGraphNode = SubGraph(environment, logger, Graph(logger, environment), initialize=True)
    
    subGraphDebugNode = nodeLibrary.Get("Debug/Debug")
    subGraphNode.graph.AddNode(subGraphDebugNode)
    
    subGraphFileNode = nodeLibrary.Get("Utility/File")
    subGraphFileNode.SetPlugValue("infile", "hello from subgraph")
    subGraphNode.graph.AddNode(subGraphFileNode)
    
    subGraphMergeNode = nodeLibrary.Get("Utility/Merge")
    subGraphNode.GetGraph().AddNode(subGraphMergeNode)
    
    logger.Log(LogLevel.DEBUG, "Connecting subgraph nodes...")
    
    subGraphNode.inputNode["input1"] >> subGraphMergeNode["input1"]
    subGraphFileNode["outfile"] >> subGraphMergeNode["input2"]
    subGraphMergeNode["output"] >> subGraphDebugNode["indata"]
    subGraphDebugNode["outdata"] >> subGraphNode.outputNode["output1"]
    
    graph.AddNode(subGraphNode)
    
    logger.Log(LogLevel.DEBUG, "Connecting graph nodes...")
    
    fileNode["outfile"] >> subGraphNode["input1"]
    subGraphNode["output1"] >> debugNode["indata"]
    
    PrintSeps()
    
    logger.Log(LogLevel.DEBUG, "Saving graph to file...")
    
    graph.SaveToFile(f"{TESTDIR}/test_subgraphs.bgraph")
    
    logger.Log(LogLevel.DEBUG, "Cooking graph...")
    
    graph.Cook()
    
    logger.Log(LogLevel.DEBUG, "Loading graph from file...")
    
    graph.LoadFromFile(f"{TESTDIR}/test_subgraphs.bgraph")
    
    logger.Log(LogLevel.DEBUG, "Cooking graph...")
    
    graph.Cook()
    
    
    
    
    