from ast import literal_eval
import re, json, copy, os

import FlashApi.Core.FileSystem as FileSystem
from FlashApi.Core.Logger import *

# Pre declaration of classes

class Node():
    pass

class Plug():
    pass


# Definitions of classes

class Parser():
    """
    Utility class to parse node definitions from files
    """
    def __init__(self):
        """
        """
        self.name = None
        self.inputCount = 0
        self.outputCount = 0
        self.parameters : list[Parameter] = []
        self.color = None
        self.iconPath = ""
        self.opCode = ""
        
    @staticmethod
    def CleanBrackets(text) -> list[str]:
        """
        """
        clean1 = text.replace("[", "")
        clean2 = clean1.replace("]", "")

        return clean2

    @staticmethod
    def SplitEqual(text) -> list[str]:
        """
        """
        return text.split("=")

    def PreProcess(self, text) -> str:
        """
        Preprocesses the file to check if there are any error to return
        and removes comment
        """
        commentPattern = re.compile(r"\s+\/\/.+|\/\/.+")

        textWithoutComments = re.sub(commentPattern, "", text)

        return textWithoutComments

    def GetAttributes(self, lines, lineIndex) -> int:
        """
        """
        while True:
            line = lines[lineIndex]

            if line.startswith("name"):
                lineSplit = self.SplitEqual(line)
                self.name = lineSplit[1].strip()

            elif line.startswith("inputs"):
                lineSplit = self.SplitEqual(line)
                self.inputCount = int(lineSplit[1])

            elif line.startswith("outputs"):
                lineSplit = self.SplitEqual(line)
                self.outputCount = int(lineSplit[1])

            elif line.startswith("color"):
                lineSplit = self.SplitEqual(line)

                self.color = []

                colorsListStr = self.CleanBrackets(lineSplit[1]).split(",")

                for colorStr in colorsListStr:
                    self.color.append(int(colorStr))

            elif line.startswith("icon"):
                lineSplit = self.SplitEqual(line)
                iconPath = lineSplit[1].strip()
                if os.path.exists(iconPath):
                    self.iconPath = iconPath
                else:
                    self.iconPath = ""
                
            elif line.startswith("# EndAttr"):
                return lineIndex + 1
            
            lineIndex += 1

    def GetParameters(self, lines, lineIndex) -> int:
        """
        """
        tmpShortName = ""
        tmpLongName = ""
        tmpValue = None

        while True:
            parmLine = lines[lineIndex]

            if parmLine.startswith("# EndParms"):
                return lineIndex + 1
            else:
                if parmLine.startswith("# BeginParm"):
                    while True:
                        parmLine = lines[lineIndex]

                        if parmLine.startswith("# EndParm"):
                            newParm = Parameter(tmpShortName, tmpLongName, tmpValue)
                            self.parameters.append(newParm)

                            tmpShortName = ""
                            tmpLongName = ""
                            tmpValue = None

                            lineIndex += 1
                        
                            break

                        elif parmLine.startswith("shortName"):
                            lineSplit = self.SplitEqual(parmLine)
                            tmpShortName = lineSplit[1].strip()
                        
                        elif parmLine.startswith("longName"):
                            lineSplit = self.SplitEqual(parmLine)
                            tmpLongName = lineSplit[1].strip()
                        
                        elif parmLine.startswith("defaultValue"):
                            lineSplit = self.SplitEqual(parmLine)
                            tmpValue = literal_eval(lineSplit[1].strip())
                        
                        lineIndex += 1

            lineIndex += 1

    def GetOpCode(self, lines, lineIndex) -> int:
        """
        """
        while True:
            opLine = lines[lineIndex]

            if opLine.startswith("# EndOp"):
                return lineIndex + 1
            else:
                self.opCode += opLine + "\n"
                lineIndex += 1

    def Parse(self, nodeFile) -> dict:
        """
        """
        definition = {}

        index = 0

        with open(nodeFile, "r") as file:
            filePreProcessed = self.PreProcess(file.read())
            lines = filePreProcessed.split("\n")
            lineCount = len(lines)   

            while index < lineCount:
                line = lines[index]

                if line.startswith("# BeginAttr"):
                    index = self.GetAttributes(lines, index)

                elif line.startswith("# BeginParms"):
                    index = self.GetParameters(lines, index)

                elif line.startswith("# BeginOp"):
                    index = self.GetOpCode(lines, index)

                else:
                    index += 1

        definition["name"] = self.name
        definition["inputCount"] = self.inputCount
        definition["outputCount"] = self.outputCount
        definition["color"] = self.color
        definition["iconPath"] = self.iconPath
        definition["opCode"] = self.opCode
        definition["parameters"] = self.parameters

        return definition

class Plug():
    """
    A Plug represents a node input or output
    """
    def __init__(self, name : str, parentNode : Node, index : int = 0, connectedPlug : Plug = None):
        """
        """
        self.name = name
        self.parentNode = parentNode
        self.index = index
        self.connectedPlug : Plug = connectedPlug
        self.data = None

    def GetName(self) -> str:
        """
        Returns:
            str: name of the plug
        """
        return self.name
    
    def GetNode(self) -> Node:
        """
        Returns:
            Node: parent node of the plug
        """
        return self.parentNode

    def GetIndex(self) -> int:
        """
        Returns:
            int: index of the plug (depending on the node)
        """
        return self.index

    def IsConnected(self) -> bool:
        """
        Returns:
            bool: if the plug is connected to another plug
        """
        if self.connectedPlug is not None:
            return True
        else:
            return False
    
    def GetConnection(self) -> Plug:
        """
        Returns:
            Plug: plug that the current plug is connected to (on another node)
        """
        return self.connectedPlug

    def UpdateInputs(self) -> None:
        """
        Updates the data coming from the input connection
        """
        if self.connectedPlug is not None:
            self.data = self.GetConnection().Data()
    
    def Data(self):
        """
        Returns:
            Any: data of the plug
        """
        return self.data

    def SetData(self, data) -> None:
        """
        Set the data of the plug

        Args:
            data (any): data to set
        """
        self.data = data
    
    def Connect(self, plug : Plug) -> None:
        """
        Connects this plug to another plug

        Args:
            plug (Plug): plug to connect the current plug to
        """
        if plug.GetNode().GetID() == self.GetNode().GetID():
            return
        else:
            self.connectedPlug = plug
            plug.connectedPlug = self
            
    def Disconnect(self) -> None:
        """
        Disconnects a plug from its connected plug (if it has any)
        """
        if self.connectedPlug is not None:
            self.connectedPlug.connectedPlug = None
            self.connectedPlug = None

class Parameter():
    """
    A parameter represents a node parameter
    """
    def __init__(self, shortName : str, longName : str, value = None):
        """
        Args:
            shortName (str): short name of the parameter than can be called in the op code
            longName (str): long name of the parameter to describe it
            value ([type], optional): value of the parameter (can be of any type). Defaults to None.
        """
        self.shortName = shortName
        self.longName = longName
        self.value = value
        
    def ShortName(self) -> str:
        """
        Returns:
            str: short name of the parameter
        """
        return self.shortName

    def LongName(self) -> str:
        """
        Returns:
            str: long name of the parameter
        """
        return self.longName
    
    def Value(self):
        """
        Returns:
            any: value of the parameter
        """
        return self.value

    def SetValue(self, value) -> None:
        """
        Sets the parameter value

        Args:
            value (any): value to set
        """
        self.value = value

class Node():
    """
    """
    def __init__(self):
        """
        """
        self.logger = None
        self.isDirty = True
        self.hasError = False
        self.errorMessage = ""
        self.hasWarning = False
        self.warningMessage = ""
        self.inQueue = False
        self.inTempQueue = False
        self.name = ""
        self.parameters : list[Parameter] = []
        self.inputs : list[Plug] = []
        self.outputs : list[Plug] = []
        self.color : list[float] = []
        self.iconPath = ""
        
        # The id is not set here as we will set a unique one for each node in the graph
        self.id = 0 
        
        self.inputCount = 0
        self.outputCount = 0
        
        self.opCode = ""
        self.opCompiledCode = ""

    def SetName(self, name : str) -> None:
        """
        Sets the name of the node
        """
        self.name = name

    def GetName(self) -> str:
        """
        Returns:
            str: name of the node
        """
        return self.name

    def SetLogger(self, logger : Logger) -> None:
        """
        """
        self.logger = logger

    def SetInputCount(self, inputCount : int) -> None:
        """
        Sets the number of input of the node

        Args:
            inputCount (int): input count of the node
        """
        assert(inputCount >= 0)
        self.inputCount = inputCount

    def GetInputCount(self) -> int:
        """
        Returns:
            int: number of inputs
        """
        return self.inputCount
    
    def SetOutputCount(self, outputCount : int) -> None:
        """
        Sets the number of output of the node

        Args:
            outputCount (int): output count of the node
        """
        assert(outputCount >= 0)
        self.outputCount = outputCount
    
    def GetOutputCount(self) -> int:
        """
        Returns:
            int: number of outputs
        """
        return self.outputCount

    def SetOpCode(self, code : str) -> None:
        """
        Sets the op code of the node

        Args:
            code (str): python code as a string
        """
        self.opCode = code

    def GetOpCode(self) -> str:
        """
        Returns:
            str: opcode of the node
        """
        return self.opCode

    def SetID(self, id : str) -> None:
        """
        Sets the id of the node
        """
        self.id = id

    def GetID(self) -> str:
        """
        Returns:
            hex: node unique id
        """
        return self.id

    def SetColor(self, color : list[float]) -> None:
        """
        Set the node rgb color (for interface)

        Args:
            color (list[float]): r, g, and v values of the node color
        """
        assert(len(color) == 3)
        self.color = color

    def GetColor(self) -> list[float]:
        """
        Returns:
            list[float]: node rgb color
        """
        return self.color

    def SetIconPath(self, path : str) -> None:
        """
        Sets the icon path
        """
        self.iconPath = path

    def GetIconPath(self) -> str:
        """
        Returns:
            str: path to the node icon
        """
        return self.iconPath

    def SetDirty(self, isDirty : bool = True) -> None:
        """
        Sets the node dirty state (cooked or not)

        Args:
            isDirty (bool): dirty state
        """
        self.isDirty = isDirty
        
    def IsDirty(self) -> bool:
        """
        Returns:
            bool: dirty state of the node
        """
        return self.isDirty

    def SetInQueue(self, inQueue : bool = True) -> None:
        """
        Sets the node to be in queue (ready to be computed)
        Used when the graph is sorted

        Args:
            inQueue (bool): queue state
        """
        self.inQueue = inQueue

    def InQueue(self) -> bool:
        """
        Returns:
            bool: queue state of the node
        """
        return self.inQueue
    
    def SetInTempQueue(self, inTempQueue : bool = True) -> None:
        """
        Sets the node to be in temp queue (when sorting graph)
        Used when the graph is sorted

        Args:
            inTempQueue (bool): temp queue state
        """
        self.inTempQueue = inTempQueue

    def InTempQueue(self) -> bool:
        """
        Returns:
            bool: temp queue state of the node
        """
        return self.inTempQueue
    
    def GetInput(self, index : int) -> Plug:
        """
        Args:
            index (int): index of the input plug to return
        Returns:
            Plug: input plug at the given index
        """
        if index >= self.inputCount:
            return None
        else:
            return self.inputs[index]
    
    def GetInputs(self) -> list[Plug]:
        """
        Returns:
            list of Plug: inputs of the node
        """
        return self.inputs

    def HasInputsNotConnected(self) -> bool:
        """
        Checks if the node has some inputs that are not connected

        Returns:
            bool: 
        """ 
        for input in self.inputs:
            if not input.IsConnected():
                return True

        return False
    
    def SetInput(self, plug : Plug, index : int) -> None:
        """
        Set the input of the node at the given index
        (connects the plug)

        Args:
            plug (Plug): plug to connect
            index (int): index of the input to set
        """
        if index >= self.inputCount:
            return
        else:
            self.inputs[index].Connect(plug)

    def SetInputFromPlugName(self, plug : Plug, name : str) -> None:
        """
        Set the input of the node with the given name

        Args:
            plug (Plug): plug to connect
            name (str): name of the input to set
        """
        for input in self.inputs:
            if input.GetName() == name:
                input.Connect(plug)
            
    def GetOutput(self, index : int) -> Plug:
        """
        Args:
            index (int): index of the output plug to return
        Returns:
            Plug: output plug at the given index
        """
        if index >= self.outputCount:
            return None
        else:
            return self.outputs[index]
        
    def GetOutputs(self) -> list[Plug]:
        """
        Returns:
            list: list of the output plugs
        """
        return self.outputs

    def SetParm(self, parmName : str, parmValue) -> None:
        """
        Set a parameter value using the shortName

        Args:
            parmName (str): name of the parameter
            parmValue ([type]): value of the parameter
        """
        parmExists = False

        for parm in self.parameters:
            if parm.ShortName() == parmName:
                parm.SetValue(parmValue)
                parmExists = True
                break

    def GetParm(self, parmName : str) -> Parameter:
        """
        Returns a parameter specified by the parmName

        Args:
            parmName (str): shortName of the queried parameter

        Returns:
            Parameter: parameter
        """
        parmExists = False

        for parm in self.parameters:
            if parm.ShortName() == parmName:
                parmExists = True
                return parm

        return None

    def GetParms(self) -> list[Parameter]:
        """
        Returns:
            list[Parameter]: list of the node parameters
        """
        return self.parameters
        
    def Cook(self) -> None:
        """
        Executes the node operation
        """
        self.hasError = False
        self.errorMessage = ""

        locals = {}
        
        # Setup locals with inputs and parameters
        for parameter in self.parameters:
            locals[parameter.ShortName()] = parameter.Value()
            
        for i, input in enumerate(self.inputs):
            input.UpdateInputs()
            locals[f"input{i}"] = input.Data()
            
        globals = { "FlashTempDir" : FileSystem.GetRoamingDataDir,
                    "FlashTempScript" : FileSystem.GetNewRandomPyFile,
                    "FlashLogError" : self.LogError,
                    "FlashLogWarning" : self.LogWarning,
                    "FlashLogMessage" : self.LogMessage,
                    "FlashError" : self.ReportError,
                    "FlashWarning" : self.ReportWarning }
        
        exec(self.opCompiledCode, globals, locals)

        # Get outputs         
        for i in range(self.outputCount):
            self.outputs[i].SetData(locals[f"output{i}"])

        self.isDirty = False

    def ReportError(self) -> None:
        """
        Emit an error signal
        """
        self.hasError = True

    def HasError(self) -> bool:
        """
        Returns if the node has an error
        """
        return self.hasError

    def GetErrorMessage(self) -> str:
        """
        Returns:
            str: Error message
        """
        return self.errorMessage

    def ReportWarning(self) -> None:
        """
        Emits a warning signal
        """
        self.hasWarning = True

    def LogError(self, message) -> None:
        """
        Log an error to the passed logger. This function is made to be 
        used in the user code
        """
        self.logger.Log(LogLevel.ERROR, f"(Node : {self.GetName()}) : {message}")
        self.errorMessage = message

        self.ReportError()
    
    def LogWarning(self, message) -> None:
        """
        Log a warning to the passed logger. This function is made to be 
        used in the user code
        """
        self.logger.Log(LogLevel.WARNING, f"(Node : {self.GetName()}) : {message}")
        self.warningMessage = message

        self.ReportWarning()
    
    def LogMessage(self, message) -> None:
        """
        Log a message to the passed logger. This function is made to be 
        used in the user code
        """
        self.logger.Log(LogLevel.MESSAGE, f"(Node : {self.GetName()}) : {message}")
        
    def Load(self, nodeDefinitionPath : str) -> None:
        """
        Loads a node definition and compiles the op code

        Args:
            nodeDefinitionPath (str): path to the node definition file
        """
        parser = Parser()

        nodeDefinition = parser.Parse(nodeDefinitionPath)

        self.name = nodeDefinition["name"]
        self.inputCount = nodeDefinition["inputCount"]
        self.outputCount = nodeDefinition["outputCount"]
        self.color = nodeDefinition["color"]
        self.iconPath = nodeDefinition["iconPath"]
        self.opCode = nodeDefinition["opCode"]
        self.parameters = nodeDefinition["parameters"]

        for i in range(self.inputCount):
            self.inputs.append(Plug(f"input{i}", self, i))
        
        for i in range(self.outputCount):
            self.outputs.append(Plug(f"output{i}", self, i))

        self.Compile()

    def ToDict(self) -> dict:
        """
        Translates the node to a dict representation

        Returns:
            dict: node as a dictionnary
        """
        nodeAsDict = {}

        nodeAsDict["name"] = self.GetName()
        nodeAsDict["id"] = self.GetID()
        nodeAsDict["color"] = self.GetColor()
        nodeAsDict["inputCount"] = self.GetInputCount()
        nodeAsDict["outputCount"] = self.GetOutputCount()
        nodeAsDict["opCode"] = self.GetOpCode()

        nodeAsDict["inputs"] = {}
        nodeAsDict["outputs"] = {}
        nodeAsDict["parms"] = {}

        for i, input in enumerate(self.GetInputs()):
            nodeAsDict["inputs"][input.GetName()] = { "connectionIndex" : input.GetIndex(), "connectionNodeId" : input.GetConnection().GetNode().GetID() }
        
        for i, output in enumerate(self.GetOutputs()):
            if output.IsConnected():
                nodeAsDict["outputs"][output.GetName()] = { "connectionIndex" : output.GetIndex(), "connectionNodeId" : output.GetConnection().GetNode().GetID() }
            else:
                nodeAsDict["outputs"][output.GetName()] = { "connectionIndex" : i, "connectionNodeId" : None }

        for parm in self.GetParms():
            nodeAsDict["parms"][parm.ShortName()] = { "longName" : parm.LongName(), "value" : parm.Value() }

        return nodeAsDict

    def FromDict(self, nodeAsDict : dict) -> None:
        """
        Load a node from a node dict representation

        Args:
            nodeAsDict (dict): dict representation of the node
        """
        self.inputs.clear()
        self.outputs.clear()
        self.parameters.clear()
        
        self.SetDirty()

        self.SetName(nodeAsDict["name"])
        self.SetID(nodeAsDict["id"])
        self.SetColor(nodeAsDict["color"])
        self.SetInputCount(nodeAsDict["inputCount"])
        self.SetOutputCount(nodeAsDict["outputCount"])
        self.SetOpCode(nodeAsDict["opCode"])

        for input in nodeAsDict["inputs"]:
            self.inputs.append(Plug(input, self))

        for output in nodeAsDict["outputs"]:
            self.outputs.append(Plug(output, self))

        for parmName, parm in nodeAsDict["parms"].items():
            self.parameters.append(Parameter(parmName, parm["longName"], parm["value"]))

        self.Compile()
        
    def Compile(self) -> None:
        """
        Compiles the node code to fasten the code execution
        """
        self.opCompiledCode = compile(self.opCode, "compiledCode", "exec")