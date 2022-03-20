import os, threading, json, copy

from functools import lru_cache

from BoltApi.Core.Node import *
from BoltApi.Core.Logger import *
from BoltApi.Core.Environment import *
from BoltApi.Utils.String import Increment, GetRandomStrId
from BoltApi.Utils.Timer import *


class Graph():
    pass


class Tracker():
    """
    A tracker is a state tracker that saves the graph cooking state each time a node is cooked. This way,
    if a crash happens during the graph cook, it will be automatically saved and if you reopen the file
    you can start the cook from where it was stopped

    Values of each plugs are saved automatically when the graph is serialized and saved, so there is no
    need to track them here
    """
    def __init__(self, graph : Graph):
        """
        """
        self.graph = graph

        self.cookedNodes : list = []

    def Update(self) -> None:
        """
        Updates the state of the Tracker to the latest cooked node
        """
        for node in self.graph.GetNodes():
            if node.IsCooked() and not node.GetID() in self.cookedNodes:
                self.cookedNodes.append(node.GetID())

    def Clean(self) -> None:
        """
        """
        self.cookedNodes.clear()

    def GetNodesState(self) -> list:
        """
        """
        if len(self.cookedNodes) > 0:
            return self.cookedNodes
        else:
            return None


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
        self.isCooked = False
        self.isCooking = False
        self.stopCook = False
        
        self.cookTime = None
        self.cookProgress = None
        self.progressCallbackFunction = None
        
        self.nodes : list[Node] = []
        self.exposedPlugs : list[Plug] = []
        self.sortedNodes : list[Node] = []
        self.ifBlocks : dict = {}
        
        self.nodeCount = 0
        
        self.__lock = threading.Lock()
        self.__flag = threading.Event()
        self.__flag.set()
        
        self.tracker = Tracker(self)

        self.UpdateEnv()

    # GETTERS / SETTERS

    def SetName(self, name : str) -> None:
        """
        """
        self.name = name

    def GetName(self) -> str:
        """
        """
        return self.name

    def SetSavePath(self, path : str) -> None:
        """
        """
        self.savePath = path

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

    def GetLock(self) -> threading.Lock:
        """
        """
        return self.__lock

    def SetAllDirty(self) -> None:
        """
        """
        for node in self.nodes:
            node.SetDirty()

    def GetIfBlocks(self) -> dict:
        """
        """
        return self.ifBlocks

    # ENV

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

    def SetEnv(self, environment : Environment) -> None:
        """
        Sets the environment of the current graph
        """
        self.environment = environment

    # EXPOSED PLUGS

    def UpdateExposedPlugs(self) -> None:
        """
        Finds all the exposed to graph plugs and updates the class list 
        """
        self.exposedPlugs.clear()

        for node in self.nodes:
            for input in node.GetInputs():
                if input.IsExposedToGraph():
                    self.exposedPlugs.append(input)

    def GetExposedPlugs(self) -> list[Plug]:
        """
        Returns the exposed plugs
        """
        return self.exposedPlugs

    def FindExposedPlug(self, nodeName : str, plugName : str, updateExposedPlugsList : bool = False) -> Plug:
        """
        Finds a plug given the name of its parent node and its name

        Args:
            nodeName (str): name of the parent node
            plugName (str): name of the plug (shortName)
            updateExposedPlugsList (bool): update the exposed plugs list (defaults to False)

        Returns:
            Plug: plug if the plug was found, else None 
        """
        if updateExposedPlugsList:
            self.UpdateExposedPlugs()

        for plug in self.exposedPlugs: 
            if plugName == plug.GetShortName() and nodeName == plug.GetNodeName():
                return plug

        return None

    # GRAPH SORTING

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
        
    # @lru_cache(maxsize=10)
    def FindIfBeginBlock(self, node : Node, beginBlock : Node, endBlock : Node, comingFromNoOutput : bool = False) -> bool:
        """
        """
        foundBeginBlock = False
        
        for inputName, input in node.GetInputs().items():
            if input.IsConnected():
                for connection in input.GetConnections():
                    connectedNode = connection.GetNode()
                    
                    if connectedNode == beginBlock:
                        return True
                    elif connectedNode == endBlock:
                        return False
                    elif connectedNode.IsIfBeginBlock():
                        if node.IsIfEndBlock() and connectedNode.GetID() == node.GetAssociatedBlockBegin():
                            continue
                        return False
                    elif connectedNode.HasNoInputsConnected():
                        if comingFromNoOutput: return False
                        
                        return self.FindIfEndBlock(connectedNode, beginBlock, endBlock, True)
                    else:
                        foundBeginBlock = self.FindIfBeginBlock(connectedNode, beginBlock, endBlock, comingFromNoOutput)
                        
                        if foundBeginBlock:
                            return True
        
        return foundBeginBlock
    
    # @lru_cache(maxsize=10)
    def FindIfEndBlock(self, node : Node, beginBlock : Node, endBlock : Node, comingFromNoInput : bool = False) -> bool:
        """
        """
        foundEndBlock = False
        
        for outputName, output in node.GetOutputs().items():
            if output.IsConnected():
                for connection in output.GetConnections():
                    connectedNode = connection.GetNode()
                    
                    if connectedNode == endBlock:
                        return True
                    elif connectedNode == beginBlock:
                        return False
                    elif connectedNode.IsIfEndBlock():
                        if node.IsIfBeginBlock():
                            continue
                        else:
                            return False
                    elif connectedNode.HasNoOutputsConnected():
                        if comingFromNoInput: return False
                        
                        return self.FindIfBeginBlock(connectedNode, beginBlock, endBlock, True)
                    else:
                        foundEndBlock = self.FindIfEndBlock(connectedNode, beginBlock, endBlock, comingFromNoInput)
                        
                        if foundEndBlock:
                            return True
        
        return foundEndBlock        
        
    def FindNodesInIfBlock(self, silent : bool = False) -> None:
        """
        Finds which nodes are in a if block if there are any
        """
        self.logger.Log(LogLevel.DIAGNOSTIC,  f"(Graph : {self.name}) : Looking for if blocks")
        
        findStart = Timer.Start()
                
        if not silent:
            for block in self.ifBlocks:
                beginBlock = self.GetNodeWithID(block)
                endBlock = self.GetNodeWithID(beginBlock.GetAssociatedBlockEnd())
                
                if beginBlock.HasNoOutputsConnected():
                    self.ReportError()
                    self.logger.Log(LogLevel.ERROR, f"(Graph : {self.name}) : Error in if block sorting. Node [{beginBlock.GetName()}] has no output connections.")
                    return
                
                if endBlock.HasNoInputsConnected():
                    self.ReportError()
                    self.logger.Log(LogLevel.ERROR, f"(Graph : {self.name}) : Error in if block sorting. Node [{endBlock.GetName()}] has no input connections.")
                    return
                        
        for node in self.nodes:
            if node.IsInsideIfBlock():
                continue
            
            for block in self.ifBlocks:     
                beginBlock = self.GetNodeWithID(block)
                endBlock = self.GetNodeWithID(beginBlock.GetAssociatedBlockEnd())
                
                if node == beginBlock or node == endBlock:
                    continue
                else:
                    foundBegin = self.FindIfBeginBlock(node, beginBlock, endBlock)
                    foundEnd = self.FindIfEndBlock(node, beginBlock, endBlock)
                    
                    if foundBegin and node.HasNoOutputsConnected():
                        self.ifBlocks[block].append(node.GetID())
                        node.SetInsideIfBlock()
                        break
                    elif foundEnd and node.HasNoInputsConnected() and not foundBegin:
                        self.ifBlocks[block].append(node.GetID())
                        node.SetInsideIfBlock()
                        break
                    elif foundBegin and foundEnd and not node.HasNoInputsConnected():
                        self.ifBlocks[block].append(node.GetID())
                        node.SetInsideIfBlock()
                        break
                
                    if not silent:
                        if foundEnd and not foundBegin:
                            self.ReportError()
                            self.logger.Log(LogLevel.ERROR, 
                                            (f"(Graph : {self.name}) : Error in if block sorting. "
                                             f"Node [{node.GetName()}] is connected to an end block "
                                             f"but not to a begin block [{endBlock.GetName()}]."))
                            return
                        elif foundBegin and not foundEnd:
                            self.ReportError()
                            self.logger.Log(LogLevel.ERROR, 
                                            f"(Graph : {self.name}) : Error in if block sorting. "
                                            f"Node [{node.GetName()}] is connected to a begin block "
                                            f"but not to an end block [{beginBlock.GetName()}].")
                            return
                        elif foundBegin and foundEnd and node.HasNoInputsConnected():
                            self.ReportError()
                            self.logger.Log(LogLevel.ERROR, f"(Graph : {self.name}) : Error in if block sorting. Node [{node.GetName()}] has no inputs.")
                            return

        findEnd = Timer.Stop()
        
        self.logger.Log(LogLevel.DIAGNOSTIC, f"(Graph : {self.name}) : If blocks sorted in {Timer.Time(findStart, findEnd):.3f} seconds")

    def ArrangeIfBlocksAfterGlobalSorting(self) -> None:
        """
        """
        
        if len(self.ifBlocks) > 0:
        
            self.logger.Log(LogLevel.DIAGNOSTIC, f"(Graph : {self.name}) : Rearranging sorted node order for if blocks")
            
            newSortedNodes = []
            
            for node in self.sortedNodes: 
                if not node.IsInsideIfBlock():
                    newSortedNodes.append(node)
                    
            for node in self.sortedNodes: 
                if node.IsInsideIfBlock():
                    
                    ifBlock = None
                    
                    for block, blockNodes in self.ifBlocks.items():
                        if node.GetID() in blockNodes:
                            ifBlock = block
                            
                    beginBlockNode = self.GetNodeWithID(ifBlock)
                    endBlockNode = self.GetNodeWithID(beginBlockNode.GetAssociatedBlockEnd())
                    
                    beginBlockSortedIndex = newSortedNodes.index(endBlockNode)
                    
                    newSortedNodes.insert(beginBlockSortedIndex, node)
                    
            self.sortedNodes = newSortedNodes

    def Sort(self) -> None:
        """
        Depth-First search to traverse and sort the nodes to cook
        the graph
        """
        self.logger.Log(LogLevel.DIAGNOSTIC, f"(Graph : {self.name}) : Sorting nodes")
        
        self.FindNodesInIfBlock()
        
        if not self.HasError():
            for node in self.nodes:
                node.SetInQueue(False)
                node.SetInTempQueue(False)

            self.sortedNodes.clear()

            while self.HasNodesToSort():
                nodeToSort = self.GetNodeToSort()
                if nodeToSort.HasInputsNotConnected() and not nodeToSort.IsDisabled():
                    nodeToSort.ReportError()
                    self.ReportError()
                    self.logger.Log(LogLevel.ERROR, f"(Graph : {self.name}) : Error in node sorting. Node [{nodeToSort.GetName()}] has unconnected input(s)")
                    break

                self.VisitNode(nodeToSort)

            if not self.hasError:        
                self.logger.Log(LogLevel.DIAGNOSTIC, f"(Graph : {self.name}) : Nodes sorted")
                
                self.ArrangeIfBlocksAfterGlobalSorting()

    # Cooking

    def SetProgressCallback(self, callback) -> None:
        """
        Sets the progress output callback function

        The callback function must accept an int argument (the current progress) like
        the following function :

        function(progress : int = 0):
            print(f"PROGRESS : {progress}%%")

        Args:
            callback (function): function to call when outputing progress
        """
        self.progressCallbackFunction = callback

    def GetProgress(self) -> float:
        """
        Returns the progress of the current graph cooking

        Returns:
            float: cooking progress
        """
        return self.cookProgress

    def UpdateProgress(self, progressStep : float) -> None:
        """
        Update the cook progress and calls the callback function

        Args:
            progressStep (float): progress step to add to the current progress
        """
        if self.cookProgress is None:
            self.cookProgress = progressStep
        else:
            self.cookProgress += progressStep

        if self.progressCallbackFunction is not None:
            self.progressCallbackFunction(round(self.cookProgress))
                
    def HandleIfBlock(self, node : Node) -> None:
        """
        Handles an if block, i.e when the graph is being cooked and an if block is encountered, test the condition and if it is true,
        cook the if block, else jump to the end of the block
        """
        node.GetInput(name="incondition").UpdateInputs()
        condition = node.GetInput(name="incondition").GetData()
        
        if condition:
            return
        else:
            for blockNode in self.ifBlocks[node.GetID()]:
                nodeToRemove = self.GetNodeWithID(blockNode)
                
                if nodeToRemove in self.sortedNodes:
                    self.sortedNodes.pop(self.sortedNodes.index(nodeToRemove))

    def Cook(self, lastNodeToCook : str = None, skipCookedNodes : bool = True) -> None:
        """
        Cooks the graphs, i.e all nodes in the graph. If lastNodeToCook is given, the graph will be cooked up to this node.

        Args:
            lastNodeToCook (str, optional): node id to cook up to. Defaults to None.
            
            skipCookedNodes (bool, optional): skips the node if they are already cooked. Defaults to True.
        """
        if self.GetSavePath() == "":
            self.ReportError()
            self.logger.Log(LogLevel.ERROR, f"(Graph : {self.name}) : Graph needs to be saved before cooking it")
            return
        
        self.SaveToFile(self.GetSavePath())
        
        cookStart = Timer.Start()
        self.UpdateProgress(0.0)
        
        self.hasError = False
        self.isCooked = False
        self.isCooking = True
        self.__flag.set()
        
        if not skipCookedNodes:
            self.SetAllDirty()

        self.logger.Log(LogLevel.DIAGNOSTIC, f"(Graph : {self.name}) : Cooking graph")
        
        self.Sort()
        
        progressStep = 100.0 / float(len(self.sortedNodes))

        if not self.hasError:
            for node in self.sortedNodes:
                self.__flag.wait()
                
                with self.GetLock():
                    if self.stopCook:
                        self.stopCook = False
                        self.isCooking = False
                        self.ReportError()
                        self.logger.Log(LogLevel.ERROR, f"(Graph : {self.name} : Cooking interrupted")
                        self.tracker.Update()
                        self.SaveToFile(self.GetSavePath())
                        return

                if skipCookedNodes:
                    if node.IsCooked():
                        continue
                    
                if node.IsIfBeginBlock():
                    self.HandleIfBlock(node)

                node.Cook()

                self.tracker.Update()
                self.SaveToFile(self.GetSavePath())


                # Check for errors
                if node.hasError:
                    self.ReportError()
                    self.isCooking = False
                    self.logger.Log(LogLevel.ERROR, f"(Graph : {self.name}) : Error in cooking node [{node.GetName()}]. Check the log for more details")
                    break
                else:
                    self.UpdateProgress(progressStep)
                    self.logger.Log(LogLevel.DIAGNOSTIC, f"(Graph : {self.name}) : Cooked node [{node.GetName()}]")

                if lastNodeToCook is not None:
                    if node.GetID() == lastNodeToCook:
                        self.logger.Log(LogLevel.DIAGNOSTIC, f"(Graph : {self.name}) : Graph cooked up to node {node.GetName()}")

                        with self.GetLock():
                            self.isCooking = False
                            self.isCooked = True
                            self.tracker.Clean()
                        break

            if not self.hasError:
                cookEnd = Timer.Stop()
                
                self.cookTime = Timer.Time(cookStart, cookEnd)
                
                self.logger.Log(LogLevel.DIAGNOSTIC, f"(Graph : {self.name}) : Graph cooked in {self.cookTime:.3f} seconds")
                
                with self.GetLock():
                    self.isCooking = False
                    self.isCooked = True
                    self.tracker.Clean()

    def StopCook(self) -> None:
        """
        Forces the graph cooking to stop
        """
        if self.isCooking:
            with self.GetLock():
                self.stopCook = True
                
    def PauseCook(self) -> None:
        """
        Pauses the graph cooking
        """
        self.__flag.clear()
            
    def ResumeCook(self) -> None:
        """
        Resume the graph cooking
        """
        self.__flag.set()

    def ReportError(self) -> None:
        """
        Emits an error
        """
        self.hasError = True

    def HasError(self) -> bool:
        """
        """
        return self.hasError

    def IsCooked(self) -> bool:
        """
        """
        return self.isCooked

    # Nodes

    def AddNode(self, node : Node) -> None:
        """
        """
        node.SetID(GetRandomStrId())

        while self.GetNodeWithName(node.GetName()) is not None:
            node.SetName(Increment(node.GetName()))

        self.nodes.append(node)

        self.nodeCount += 1
        
        if node.IsIfBeginBlock():   
            self.ifBlocks[node.GetID()] = []
            self.logger.Log(LogLevel.DIAGNOSTIC, f"(Graph : {self.name}) : New If Block [{node.GetName()}]")
        
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
                
        if node.IsInsideIfBlock():
            for blockName, blockNodes in self.ifBlocks.items():
                if node.GetID() in blockNodes:
                    blockNodes.remove(node.GetID())
                    break

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

    # I/O

    def Serialize(self) -> str:
        """
        Serializes the graph to a json string

        Returns:
            str: serialized content
        """
        graphDict = {}
        nodesAsDicts = []

        for node in self.nodes:
            nodesAsDicts.append(node.ToDict())

        graphDict["nodes"] = nodesAsDicts

        if self.tracker is not None:
            graphDict["tracker"] = self.tracker.GetNodesState()
        else:            
            graphDict["tracker"] = None

        return json.dumps(graphDict, indent=2)

    def Deserialize(self, serializedGraph : str) -> None:
        """
        Loads a graph from a serialized one (in json format)

        Args:
            serializedGraph (str): serialized graph
        """
        self.nodes.clear()
        self.sortedNodes.clear()

        graphDict = json.loads(serializedGraph)
        nodesAsDicts = graphDict["nodes"]

        for node in nodesAsDicts:
            tmpNode = Node(self.environment)
            tmpNode.SetLogger(self.logger)
            tmpNode.FromDict(node)
            
            if tmpNode.IsIfBeginBlock():   
                self.ifBlocks[tmpNode.GetID()] = []
            
            self.nodes.append(tmpNode)

        for i, node in enumerate(nodesAsDicts):
            for outputName, outputContent in node["outputs"].items():
                for connection in outputContent:
                    if connection["connectionNodeId"] is not None:
                        nodeToConnect = self.GetNodeWithID(connection["connectionNodeId"])
                        nodeToConnect.SetInput(self.nodes[i].GetOutput(name=outputName), name=connection["connectionName"])

        if "tracker" in graphDict:
            self.tracker = graphDict["tracker"]
        else:
            self.tracker = Tracker(self)

        if self.tracker is not None:
            for nodeID in self.tracker:
                node = self.GetNodeWithID(nodeID)
                if node is not None:
                    node.SetCooked()
            self.tracker = Tracker(self)
            self.tracker.cookedNodes = graphDict["tracker"]
        else:
            self.tracker = Tracker(self)

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
        
        with open(filePath, "r") as file:
            oldFileContent = file.read()
            oldFileData = json.loads(oldFileContent)
            
        if saveAsString:
            with open(filePath, "w") as file:
                serializedGraph = self.Serialize()
                
                jsonGraph = json.loads(serializedGraph)
                
                if "positions" in oldFileData:
                    jsonGraph["positions"] = oldFileData["positions"]
                
                serializedGraph = json.dumps(jsonGraph, indent=2)
                
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
            return
        else:
            self.savePath = filePath
            self.name, _ = os.path.splitext(os.path.basename(filePath))

            with open(filePath, "r", encoding="utf-8") as file:
                self.Deserialize(file.read())

        self.UpdateEnv()