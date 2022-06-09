from BoltApi.Core.Node import *


class Graph():
    pass


class Inputs(Node):
    """
    Input of the subgraph 
    """
    def __init__(self, environment : Environment) -> None:
        """
        """
        super().__init__(environment)
        
        self.SetName("Inputs")
        
        self.SetColor([137, 221, 255])
        self.SetDefinitionPath("")
        self.SetIconPath("$BOLT_ICONS/inputs.png")
        self.SetCategory("Utility")
        self.SetNodeType("Inputs")
    

class Outputs(Node): 
    """
    Output of the subgraph
    """
    def __init__(self, environment : Environment) -> None:
        """
        """
        super().__init__(environment)
        
        self.SetName("Outputs")
        
        self.SetColor([137, 221, 255])
        self.SetDefinitionPath("")
        self.SetIconPath("$BOLT_ICONS/outputs.png")
        self.SetCategory("Utility")
        self.SetNodeType("Outputs")


class SubGraph(Node): 
    """
    A subgraph is a node encapsulating a graph with inputs and outputs that can be used
    in that graph
    """
    def __init__(self, environment : Environment, logger : Logger, graph : Graph, initialize : bool = False) -> None:
        """
        """
        super().__init__(environment)
        
        self.SetLogger(logger)
        self.SetColor([137, 221, 255])
        self.SetDefinitionPath("")
        self.SetIconPath("$BOLT_ICONS/subgraph.png")
        self.SetCategory("Utility")
        self.SetNodeType("SubGraph")
        
        self.subgraph = graph
        self.SetName("SubGraph")
            
        self.subgraph.SetSubGraph(True)
        
        if initialize:
            self.Initialize()
            
    def SetName(self, name : str) -> None:
        """
        Sets the name of the node
        """
        super().SetName(name)
        
        self.subgraph.SetName(self.GetName())
        
    def SetSubGraph(self, graph : Graph) -> None:
        """
        Sets the graph of this subgraph node
        
        Args:
            graph (Graph): graph to set 
        """
        self.subgraph = graph
        
    def GetSubGraph(self) -> Graph:
        """
        Returns:
            Graph: graph contained in the subgraph node
        """
        return self.subgraph
    
    def Initialize(self) -> None:
        """
        Initializes the node and its graph by adding the input and output node
        """
        self.inputNode = Inputs(self.environment)
        self.outputNode = Outputs(self.environment)
        
        self.AddInput(Plug("input0", "Input0", self))
        self.AddOutput(Plug("output0", "Output0", self))
        
        self.subgraph.AddNode(self.inputNode)
        self.subgraph.AddNode(self.outputNode)
        
    def UpdateInputs(self) -> None:
        """
        Updates the input values of the subgraph Input node
        """
        for inputName, input in self.inputs.items():
            input.UpdateInputs()
            self.inputNode.GetOutput(inputName).SetData(input.GetData())
            
    def AddInput(self, plug : Plug) -> None:
        """
        Adds an input plug to the node and the corresponding output
        to the inputs node
        
        Args:
            plug (Plug): input plug to add
        """
        self.inputs[plug.GetShortName()] = plug
        
        inputNodePlug = Plug(plug.GetShortName(), plug.GetLongName(), self.inputNode, dataType=plug.GetType())
        
        self.inputNode.AddOutput(inputNodePlug)
            
    def UpdateOutputs(self) -> None:
        """
        Updates the outputs values from the plugs of the subgraph Ouput node 
        """
        for outputName, output in self.outputNode.GetInputs().items():
            self.GetOutput(outputName).SetData(output.GetData())
            
    def AddOutput(self, plug : Plug) -> None:
        """
        Adds an output plug to the node and the corresponding input
        to the outputs node
        
        Args:
            plug (Plug): output plug to add
        """
        self.outputs[plug.GetShortName()] = plug
        
        outputNodePlug = Plug(plug.GetShortName(), plug.GetLongName(), self.outputNode, dataType=plug.GetType())
        
        self.outputNode.AddInput(outputNodePlug)
        
    def Cook(self) -> None:
        """
        """
        self.UpdateInputs()
        
        if not self.IsDisabled():
            startTime = Timer.Start()

            with self.GetLock():
                self.isCooking = True
                self.isCooked = False

                self.hasError = False
                self.errorMessage = ""
                self.hasWarning = False
                self.warningMessage = ""
            
            self.subgraph.Cook(skipCookedNodes=False)
            
            if self.subgraph.HasError():
                self.ReportError()
                self.LogError(f"Error cooking node {self.GetName()}")
                self.cookTime = None
                self.isCooking = False
                self.isCooked = False
                return

            with self.GetLock():
                self.isDirty = False
                self.isCooking = False
                self.isCooked = True

            endTime = Timer.Stop()
            
            self.UpdateOutputs()

            self.cookTime = Timer.Time(startTime, endTime)
        else:
            firstInput = self.GetInput(index=0)
            firstInput.UpdateInputs()

            for outputName, output in self.outputs.items():
                output.SetData(firstInput.GetData())
           
    # I/O

    def ToDict(self) -> dict:
        """
        """
        nodeAsDict = super().ToDict()
        
        nodeAsDict["isSubGraph"] = True
        
        nodeAsDict["subgraph"] = self.subgraph.Serialize()
        
        return nodeAsDict
    
    def FromDict(self, nodeAsDict : dict) -> None:
        """
        """
        super().FromDict(nodeAsDict)
        
        self.subgraph.Deserialize(nodeAsDict["subgraph"])
        
        self.inputNode = self.subgraph.GetNodeWithName("Inputs")
        self.outputNode = self.subgraph.GetNodeWithName("Outputs")
        
        
class IfSubGraph(SubGraph):
    """
    SubGraph encapsulating an if block, i.e a graph that will be executed only
    if some condition is True
    """
    def __init__(self, environment : Environment, logger : Logger, graph : Graph, initialize : bool = False) -> None:
        """
        """
        super().__init__(environment, logger, graph, initialize=initialize)
        
        self.SetLogger(logger)
        
        self.SetName("IfBlock")
        self.SetColor([104, 240, 222])
        self.SetDefinitionPath("")
        self.SetIconPath("$BOLT_ICONS/if-block.png")
        self.SetCategory("Utility")
        self.SetNodeType("IfBlock")
        
    def Initialize(self) -> None:
        """
        Initializes the node and its graph by adding the input and output node,
        and the condition input
        """
        super().Initialize()
        
        self.AddInput(Plug("incondition", "Condition", self, dataType=PlugType.BOOL))
        self.SetPlugValue("incondition", False)
        
    def Cook(self) -> None:
        """
        """
        self.UpdateInputs()
        
        if not self.IsDisabled():
            if self.GetInput(name="incondition").GetData():
                startTime = Timer.Start()

                with self.GetLock():
                    self.isCooking = True
                    self.isCooked = False

                    self.hasError = False
                    self.errorMessage = ""
                    self.hasWarning = False
                    self.warningMessage = ""
                
                self.subgraph.Cook(skipCookedNodes=False)
                
                if self.subgraph.HasError():
                    self.ReportError()
                    self.LogError(f"Error cooking node {self.GetName()}")
                    self.cookTime = None
                    self.isCooking = False
                    self.isCooked = False
                    return

                with self.GetLock():
                    self.isDirty = False
                    self.isCooking = False
                    self.isCooked = True

                endTime = Timer.Stop()
                
                self.UpdateOutputs()

                self.cookTime = Timer.Time(startTime, endTime)
                
                return
            
        firstInput = self.GetInput(index=0)
        firstInput.UpdateInputs()

        for outputName, output in self.outputs.items():
            output.SetData(firstInput.GetData())
        
    # I/O

    def ToDict(self) -> dict:
        """
        """
        nodeAsDict = super().ToDict()
        
        nodeAsDict["isIfBlock"] = True
        
        return nodeAsDict


class ForSubGraph(SubGraph):
    """
    SubGraph encapsulating a For block, i.e a graph that will be executed on a list
    of item, one by one
    """
    def __init__(self, environment : Environment, logger : Logger, graph : Graph, initialize : bool = False) -> None:
        """
        """
        super().__init__(environment, logger, graph, initialize=initialize)
        
        self.SetLogger(logger)
        
        self.SetName("ForBlock")
        self.SetColor([247, 140, 108])
        self.SetDefinitionPath("")
        self.SetIconPath("$BOLT_ICONS/for-block.png")
        self.SetCategory("Utility")
        self.SetNodeType("ForBlock")
        
    def Initialize(self) -> None:
        """
        Initializes the node and its graph by adding the input and output node, 
        and specifies the type of the plugs (list)
        """
        self.inputNode = Inputs(self.environment)
        self.outputNode = Outputs(self.environment)
        
        self.AddInput(Plug("input0", "Input0", self, dataType=PlugType.LIST))
        self.AddOutput(Plug("output0", "Output0", self, dataType=PlugType.LIST))
        
        self.subgraph.AddNode(self.inputNode)
        self.subgraph.AddNode(self.outputNode)
        
        
    def Cook(self) -> None:
        """
        """
        if not self.IsDisabled():
            startTime = Timer.Start()

            with self.GetLock():
                self.isCooking = True
                self.isCooked = False

                self.hasError = False
                self.errorMessage = ""
                self.hasWarning = False
                self.warningMessage = ""

            self.UpdateInputs()
            
            listToIterate = self.GetInput(name="input0").GetData()
            
            if isinstance(listToIterate, list):
                
                results = []
                
                for i, item in enumerate(listToIterate):
                    self.logger.Log(LogLevel.MESSAGE, f"Node ({self.GetName()}) : Cooking iteration {i}")
                    
                    self.inputNode.GetOutput(index=0).SetData(item)
            
                    self.subgraph.Cook(skipCookedNodes=False)
                    
                    results.append(self.outputNode.GetInput(index=0).GetData())
                    
                self.outputNode.GetInput(index=0).SetData(results)
            elif isinstance(listToIterate, dict):
                
                results = []
                
                for i, item in enumerate(listToIterate.values()):
                    self.logger.Log(LogLevel.MESSAGE, f"Node ({self.GetName()}) : Cooking iteration {i}")
                    
                    self.inputNode.GetOutput(index=0).SetData(item)
            
                    self.subgraph.Cook(skipCookedNodes=False)
                    
                    results.append(self.outputNode.GetInput(index=0).GetData())
                    
                self.outputNode.GetInput(index=0).SetData(results)
            else:
                self.logger.Log(LogLevel.ERROR, f"Node ({self.GetName()}) : Invalid input type, it must be a list or a dictionnary")
                self.ReportError()
                return
            
            self.UpdateOutputs()
            
        
            with self.GetLock():
                self.isDirty = False
                self.isCooking = False
                self.isCooked = True

            endTime = Timer.Stop()

            self.cookTime = Timer.Time(startTime, endTime)
        else:
           output = self.GetOutput(name="output0")
           output.SetData(self.GetInput(name="input0").GetData())

    # I/O

    def ToDict(self) -> dict:
        """
        """
        nodeAsDict = super().ToDict()
        
        nodeAsDict["isForBlock"] = True
        
        return nodeAsDict
