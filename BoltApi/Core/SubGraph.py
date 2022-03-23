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
        
        self.graph = graph
        self.SetName("SubGraph")
            
        self.graph.SetSubGraph(True)
        
        if initialize:
            self.Initialize()
            
    def SetName(self, name : str) -> None:
        """
        Sets the name of the node
        """
        super().SetName(name)
        
        self.graph.SetName(self.GetName())
        
    def SetGraph(self, graph : Graph) -> None:
        """
        Sets the graph of this subgraph node
        
        Args:
            graph (Graph): graph to set 
        """
        self.graph = graph
        
    def GetGraph(self) -> Graph:
        """
        Returns:
            Graph: graph contained in the subgraph node
        """
        return self.graph
    
    def Initialize(self) -> None:
        """
        Initializes the node and its graph by adding the input and output node
        """
        self.inputNode = Inputs(self.environment)
        self.outputNode = Outputs(self.environment)
        
        self.AddInput(Plug("input1", "Input 1", self))
        self.AddOutput(Plug("output1", "Output 1", self))
        
        self.graph.AddNode(self.inputNode)
        self.graph.AddNode(self.outputNode)
        
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
        
        inputNodePlug = Plug(plug.GetShortName(), plug.GetLongName(), self.inputNode)
        
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
        
        outputNodePlug = Plug(plug.GetShortName(), plug.GetLongName(), self.outputNode)
        
        self.outputNode.AddInput(outputNodePlug)
        
    def Cook(self) -> None:
        """
        """
        self.UpdateInputs()
        
        self.graph.Cook(skipCookedNodes=False)
        
        self.UpdateOutputs()
        
    # I/O

    def ToDict(self) -> dict:
        """
        """
        nodeAsDict = super().ToDict()
        
        nodeAsDict["isSubGraph"] = True
        
        nodeAsDict["subgraph"] = self.graph.Serialize()
        
        return nodeAsDict
    
    def FromDict(self, nodeAsDict : dict) -> None:
        """
        """
        super().FromDict(nodeAsDict)
        
        self.graph.Deserialize(nodeAsDict["subgraph"])
        
        self.inputNode = self.graph.GetNodeWithName("Inputs")
        self.outputNode = self.graph.GetNodeWithName("Outputs")
        
        
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
        
        self.AddInput(Plug("incondition", "Condition", self))
        
    def Cook(self) -> None:
        """
        """
        self.UpdateInputs()
        
        if self.GetInput(name="incondition").GetData():
            self.graph.Cook(skipCookedNodes=False)
            self.UpdateOutputs()
            
        else:
            pass
        
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
        
    def Cook(self) -> None:
        """
        """
        self.UpdateInputs()
        
        self.graph.Cook(skipCookedNodes=False)
        
        self.UpdateOutputs()
        
    # I/O

    def ToDict(self) -> dict:
        """
        """
        nodeAsDict = super().ToDict()
        
        nodeAsDict["isForBlock"] = True
        
        return nodeAsDict