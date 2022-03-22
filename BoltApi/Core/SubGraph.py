from BoltApi.Core.Graph import *
from BoltApi.Core.Node import *


class Inputs(Node):
    """
    Input of the subgraph 
    """
    def __init__(self, environment : Environment) -> None:
        """
        """
        super().__init__(environment)
        
        self.SetName("Inputs")
    

class Outputs(Node): 
    """
    Output of the subgraph
    """
    def __init__(self, environment : Environment) -> None:
        """
        """
        super().__init__(environment)
        
        self.SetName("Outputs")


class SubGraph(Node): 
    """
    A subgraph is a node encapsulating a graph with inputs and outputs that can be used
    in that graph
    """
    def __init__(self, environment : Environment, logger : Logger, graph : Graph = None) -> None:
        """
        """
        super().__init__(environment)
        
        self.SetLogger(logger)
        
        self.SetName("SubGraph")
        
        if graph is None:
            self.graph = Graph(self.logger, self.environment, self.name)
        else:
            self.graph = graph
            
        self.graph.SetSubGraph(True)
        
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
            self.inputNode.GetOutput(inputName).SetData(input.GetData())
            
    def AddInput(self, plug : Plug) -> None:
        """
        Adds an input plug to the node and the corresponding output
        to the inputs node
        
        Args:
            plug (Plug): input plug to add
        """
        self.inputs[plug.GetShortName()] = plug
        self.inputNode.AddOutput(plug)
            
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
        self.outputNode.AddInput(plug)
        
    def Cook(self) -> None:
        """
        """
        self.UpdateInputs()
        
        self.graph.Cook(skipCookedNodes=False)
        
        self.UpdateOutputs()