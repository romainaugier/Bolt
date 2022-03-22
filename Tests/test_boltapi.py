from Tests.test import *

if __name__ == "__main__":
    logger = Logger(level=LogLevel.DEBUG)
    
    logger.Log(LogLevel.DEBUG, "Testing Bolt API...") 
    
    PrintSeps()

    logger.Log(LogLevel.DEBUG, "Testing node library...")

    environment = Environment()
    nodeLibrary = Lib(logger, environment)
    nodeLibrary.Load()

    PrintSeps()
    
    logger.Log(LogLevel.DEBUG, "Testing node to file...")
    
    templateNode = nodeLibrary.Get("Debug/Template")
    
    print(templateNode.ToFile())
    
    PrintSeps()

    logger.Log(LogLevel.DEBUG, "Testing graph...")

    graph = Graph(logger, environment, "new")

    fileNode = nodeLibrary.Get("Utility/File")
    fileNode.SetPlugValue("infile", f"{TESTDIR}/test_script.py")

    debugNode = nodeLibrary.Get("Debug/Debug")

    pythonNode = nodeLibrary.Get("Python/Python")

    logger.Log(LogLevel.DEBUG, "Adding nodes...")

    graph.AddNode(debugNode)
    graph.AddNode(pythonNode)
    graph.AddNode(fileNode)
    
    logger.Log(LogLevel.DEBUG, "Connecting Nodes...")

    fileNode["outfile"] >> debugNode["indata"]
    debugNode["outdata"] >> pythonNode["inscript"]

    for node in graph.GetNodes():
        PrintSeps()
        print(node.GetName())

        for inputName, input in node.GetInputs().items():
            print(input.GetLongName(), input.IsExposed(), input.GetData())

    PrintSeps()

    logger.Log(LogLevel.DEBUG, "Cooking graph...")

    # graph.Cook()

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

    graphSavePath = f"{TESTDIR}/tmp_graph.bgraph"

    graph.SaveToFile(graphSavePath)

    PrintSeps()

    logger.Log(LogLevel.DEBUG, "Loading from file...")

    graph.LoadFromFile(graphSavePath)

    PrintSeps()

    logger.Log(LogLevel.DEBUG, "Cooking graph after loading...")

    graph.Cook()

    PrintSeps()
    
    logger.Log(LogLevel.DEBUG, "Loading if block graph...")
    
    ibgraph = f"{TESTDIR}/if_block_test.bgraph"
    
    graph.LoadFromFile(ibgraph)
    
    graph.Sort()
    
    PrintSeps()