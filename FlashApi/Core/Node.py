from ast import literal_eval
from enum import IntEnum
from pickle import NONE
import re, json, copy, os

import FlashApi.Core.FileSystem as FileSystem
from FlashApi.Core.Logger import *
from FlashApi.Core.Environment import *

# Pre declaration of classes

class Node():
    pass

class Plug():
    pass

# Plug type enumeration

class PlugType(IntEnum):
    """
    Plug types available
    """
    INT = 1
    INT2 = 2
    INT3 = 3
    FLOAT = 4
    FLOAT2 = 5
    FLOAT3 = 6
    STR = 7
    BOOL = 8
    LIST = 9
    DICT = 10
    CUSTOM = 11

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
        self.plugs : list[Plug] = []
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

    def GetPlugType(self, plugTypeStr : str) -> PlugType:
        """
        """
        if plugTypeStr == "int":
            return PlugType.INT
        elif plugTypeStr == "int2":
            return PlugType.INT2
        elif plugTypeStr == "int3":
            return PlugType.INT3
        elif plugTypeStr == "float":
            return PlugType.FLOAT
        elif plugTypeStr == "float2":
            return PlugType.FLOAT2
        elif plugTypeStr == "float3":
            return PlugType.FLOAT3
        elif plugTypeStr == "str":
            return PlugType.STR
        elif plugTypeStr == "bool":
            return PlugType.BOOL
        elif plugTypeStr == "list":
            return PlugType.LIST
        elif plugTypeStr == "dict":
            return PlugType.DICT
        elif plugTypeStr == "custom":
            return PlugType.CUSTOM

    def GetAttributes(self, lines, lineIndex) -> int:
        """
        """
        while True:
            line = lines[lineIndex]

            if line.startswith("name"):
                lineSplit = self.SplitEqual(line)
                self.name = lineSplit[1].strip()

            elif line.startswith("color"):
                lineSplit = self.SplitEqual(line)

                self.color = []

                colorsListStr = self.CleanBrackets(lineSplit[1]).split(",")

                for colorStr in colorsListStr:
                    self.color.append(int(colorStr))

            elif line.startswith("icon"):
                lineSplit = self.SplitEqual(line)
                iconPath = lineSplit[1].strip()
                self.iconPath = iconPath
                
            elif line.startswith("# EndAttr"):
                return lineIndex + 1
            
            lineIndex += 1

    def GetPlugs(self, lines, lineIndex) -> int:
        """
        """
        tmpShortName = ""
        tmpLongName = ""
        tmpValue = None
        tmpType = None
        tmpExposed = False

        while True:
            parmLine = lines[lineIndex]

            if parmLine.startswith("# EndPlugs"):
                return lineIndex + 1
            else:
                if parmLine.startswith("# BeginPlug"):
                    while True:
                        parmLine = lines[lineIndex]

                        if parmLine.startswith("# EndPlug"):
                            newPlug = Plug(tmpShortName, tmpLongName, None, tmpValue, tmpType)
                            newPlug.SetExposed(tmpExposed)
                            self.plugs.append(newPlug)

                            tmpShortName = ""
                            tmpLongName = ""
                            tmpValue = None
                            tmpType = None
                            tmpExposed = False

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

                        elif parmLine.startswith("type"):
                            lineSplit = self.SplitEqual(parmLine)
                            tmpType = self.GetPlugType(lineSplit[1].strip())

                        elif parmLine.startswith("exposed"):
                            lineSplit = self.SplitEqual(parmLine)
                            tmpExposed = True if "True" in lineSplit[1].strip() else False
                        
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

                elif line.startswith("# BeginPlugs"):
                    index = self.GetPlugs(lines, index)

                elif line.startswith("# BeginOp"):
                    index = self.GetOpCode(lines, index)

                else:
                    index += 1

        definition["name"] = self.name
        definition["color"] = self.color
        definition["iconPath"] = self.iconPath
        definition["opCode"] = self.opCode
        definition["plugs"] = self.plugs

        return definition

class Plug():
    """
    A Plug represents a node input or output
    """
    def __init__(self, shortName : str, longName : str, parentNode : Node, data = None, dataType : PlugType = None, index : int = 0, connectedPlug : Plug = None):
        """
        """
        self.shortName : str = shortName
        self.longName : str = longName
        self.parentNode : Node = parentNode
        self.index : int = index
        self.connectedPlugs : list[Plug] = []

        if connectedPlug is not None:
            self.connectedPlugs.append(connectedPlug)

        self.data = data
        self.type : PlugType = dataType
        self.isExposed = False

    def GetShortName(self) -> str:
        """
        Returns:
            str: short name of the plug
        """
        return self.shortName
    
    def GetLongName(self) -> str:
        """
        Returns:
            str: long name of the plug
        """
        return self.longName

    def SetNode(self, node : Node) -> None:
        """
        """
        self.parentNode = node
    
    def GetNode(self) -> Node:
        """
        Returns:
            Node: parent node of the plug
        """
        return self.parentNode

    def SetIndex(self, index : int) -> None:
        """
        """
        self.index = index

    def GetIndex(self) -> int:
        """
        Returns:
            int: index of the plug (depending on the node)
        """
        return self.index

    def GetType(self) -> PlugType:
        """
        Returns:
            PlugType: data type of the plug
        """
        return self.type

    def IsExposed(self) -> None:
        """
        Tells if a plug is exposed (as a parameter)
        """
        return self.isExposed

    def SetExposed(self, isExposed : bool) -> None:
        """
        """
        self.isExposed = isExposed

    def IsConnected(self) -> bool:
        """
        Returns:
            bool: if the plug is connected to another plug
        """
        if len(self.connectedPlugs) > 0:
            return True
        else:
            return False
    
    def GetConnections(self) -> list[Plug]:
        """
        Returns:
            Plug: plug that the current plug is connected to (on another node)
        """
        return self.connectedPlugs

    def UpdateInputs(self) -> None:
        """
        Updates the data coming from the input connection
        """
        if len(self.connectedPlugs) > 0:
            self.data = self.GetConnections()[0].GetData()
    
    def GetData(self):
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
        if plug is not None:
            if self.IsExposed() or plug.IsExposed():
                return
            elif plug.GetNode().GetID() == self.GetNode().GetID():
                return
            else:
                self.connectedPlugs.append(plug)
                plug.connectedPlugs.append(self)
            
    def Disconnect(self, plug : Plug) -> None:
        """
        Disconnects the plug from the given plug
        """
        if self.connectedPlugs is not None:
            plug.connectedPlugs.remove(self)
            self.connectedPlugs.remove(plug)

class Node():
    """
    """
    def __init__(self, environment : Environment):
        """
        """
        self.environment = copy.deepcopy(environment)
        self.logger = None
        self.isDirty = True
        self.hasError = False
        self.errorMessage = ""
        self.hasWarning = False
        self.warningMessage = ""
        self.inQueue = False
        self.inTempQueue = False
        self.name = ""
        self.inputs : dict = {}
        self.outputs : dict = {}
        self.color : list[float] = []
        self.iconPath = ""
        
        # The id is not set here as we will set a unique one for each node in the graph
        self.id = 0 
        
        self.opCode = ""
        self.opCompiledCode = ""

    def SetName(self, name : str) -> None:
        """
        Sets the name of the node
        """
        self.name = name

        self.UpdateEnv()

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

    def GetInputCount(self) -> int:
        """
        Returns:
            int: number of inputs
        """
        count = 0

        for inputName, input in self.inputs.items():
            if not input.IsExposed():
                count += 1

        return count
    
    def GetOutputCount(self) -> int:
        """
        Returns:
            int: number of outputs
        """
        return len(self.outputs.keys())

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
        if self.environment.SearchInString(self.iconPath):
            return self.environment.ReplaceInString(self.iconPath)
        else:
            return self.iconPath

    def GetIconPathRaw(self) -> str:
        """
        Returns:
            str: raw path to the node icon (environment variables won't be evaluated)
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
    
    def GetInput(self, name : str = None, index : int = None) -> Plug:
        """
        Args:
            index (int): index of the input plug to return
        Returns:
            Plug: input plug at the given index
        """
        if name is not None:
            if not name in self.inputs:
                return None
            else:
                return self.inputs[name]
        elif index is not None:
            return list(self.inputs.values())[index]
        else:
            return None
    
    def GetInputs(self) -> dict:
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
        for name, input in self.inputs.items():
            if not input.IsConnected() and not input.IsExposed():
                return True

        return False
    
    def SetInput(self, plug : Plug, name : str = None, index : int = None) -> None:
        """
        Set the input of the node at the given plug
        (connects the plug)

        Args:
            plug (Plug): plug to connect
            index (int): index of the input to set
        """
        if name is not None:
            if not name in self.inputs:
                return
            else:
                self.inputs[name].Connect(plug)
                return
        elif index is not None:
            return list(self.inputs.values())[index].Connect(plug)
        else:
            return None
            
    def GetOutput(self, name : str = None, index : int = None) -> Plug:
        """
        Args:
            index (int): index of the output plug to return
        Returns:
            Plug: output plug at the given index
        """
        if name is not None:
            if not name in self.outputs:
                return None
            else:
                return self.outputs[name]
        elif index is not None:
            return list(self.outputs.values())[index]
        else:
            return None
        
    def GetOutputs(self) -> dict:
        """
        Returns:
            list: list of the output plugs
        """
        return self.outputs

    def SetPlugValue(self, plugName : str, value) -> None:
        """
        """
        if plugName in self.inputs:
            self.inputs[plugName].SetData(value)
        
    def Cook(self) -> None:
        """
        Executes the node operation
        """
        self.hasError = False
        self.errorMessage = ""

        locals = {}
            
        for inputName, input in self.inputs.items():
            input.UpdateInputs()
            locals[inputName] = input.GetData()
            
        globals = { "FlashTempDir" : FileSystem.GetRoamingDataDir,
                    "FlashTempScript" : FileSystem.GetNewRandomPyFile,
                    "FlashLogError" : self.LogError,
                    "FlashLogWarning" : self.LogWarning,
                    "FlashLogMessage" : self.LogMessage,
                    "FlashError" : self.ReportError,
                    "FlashWarning" : self.ReportWarning }
        
        exec(self.opCompiledCode, globals, locals)

        # Get outputs         
        for outputName, output in self.outputs.items():
            if outputName in locals:
                output.SetData(locals[outputName])

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
        self.color = nodeDefinition["color"]
        self.iconPath = nodeDefinition["iconPath"]
        self.opCode = nodeDefinition["opCode"]

        if not os.path.exists(self.GetIconPath()):
            self.iconPath = ""

        for plug in nodeDefinition["plugs"]:
            if "in" in plug.GetShortName():
                plug.SetNode(self)
                self.inputs[plug.GetShortName()] = plug
            elif "out" in plug.GetShortName():
                plug.SetNode(self)
                self.outputs[plug.GetShortName()] = plug

        self.UpdateEnv()

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
        nodeAsDict["iconPath"] = self.GetIconPathRaw()
        nodeAsDict["opCode"] = self.GetOpCode()

        nodeAsDict["inputs"] = {}
        nodeAsDict["outputs"] = {}

        for inputName, input in self.GetInputs().items():
            if input.IsConnected():

                nodeAsDict["inputs"][input.GetShortName()] = []

                for connection in input.GetConnections():
                    nodeAsDict["inputs"][input.GetShortName()].append({ "shortName" : input.GetShortName(),
                                                                        "longName" : input.GetLongName(),
                                                                        "index" : input.GetIndex(),
                                                                        "isExposed" : input.IsExposed(),
                                                                        "data" : input.GetData(), 
                                                                        "type" : input.GetType(),
                                                                        "connectionName" : connection.GetShortName(), 
                                                                        "connectionNodeId" : connection.GetNode().GetID() })
            else:
                nodeAsDict["inputs"][input.GetShortName()] = [{ "shortName" : input.GetShortName(),
                                                               "longName" : input.GetLongName(),
                                                               "index" : input.GetIndex(),
                                                               "isExposed" : input.IsExposed(),
                                                               "data" : input.GetData(), 
                                                               "type" : input.GetType(),
                                                               "connectionName" : None,
                                                               "connectionNodeId" : None }]
        
        for outputName, output in self.GetOutputs().items():
            if output.IsConnected():

                nodeAsDict["outputs"][output.GetShortName()] = []

                for connection in output.GetConnections():
                    nodeAsDict["outputs"][output.GetShortName()].append({ "shortName" : output.GetShortName(),
                                                                    "longName" : output.GetLongName(),
                                                                    "index" : output.GetIndex(),
                                                                    "isExposed" : output.IsExposed(),
                                                                    "data" : output.GetData(), 
                                                                    "type" : output.GetType(),
                                                                    "connectionName" : connection.GetShortName(), 
                                                                    "connectionNodeId" : connection.GetNode().GetID() })
            else:
                nodeAsDict["outputs"][output.GetShortName()] = [{ "shortName" : output.GetShortName(),
                                                                 "longName" : output.GetLongName(),
                                                                 "index" : output.GetIndex(),
                                                                 "isExposed" : output.IsExposed(),
                                                                 "data" : output.GetData(), 
                                                                 "type" : output.GetType(),
                                                                 "connectionName" : None, 
                                                                 "connectionNodeId" : None }]
        return nodeAsDict

    def FromDict(self, nodeAsDict : dict) -> None:
        """
        Load a node from a node dict representation

        Args:
            nodeAsDict (dict): dict representation of the node
        """
        self.inputs.clear()
        self.outputs.clear()
        
        self.SetDirty()

        self.SetName(nodeAsDict["name"])
        self.SetID(nodeAsDict["id"])
        self.SetColor(nodeAsDict["color"])
        self.SetIconPath(nodeAsDict["iconPath"])
        self.SetOpCode(nodeAsDict["opCode"])

        for inputName, input in nodeAsDict["inputs"].items():
            input = input[0]
            tmpPlug = Plug(input["shortName"], input["longName"], self, input["data"], input["type"])
            tmpPlug.SetExposed(input["isExposed"])
            tmpPlug.SetIndex(input["index"])
            self.inputs[inputName] = tmpPlug

        for outputName, output in nodeAsDict["outputs"].items():
            output = output[0]
            tmpPlug = Plug(output["shortName"], output["longName"], self, output["data"], output["type"])
            tmpPlug.SetExposed(output["isExposed"])
            tmpPlug.SetIndex(output["index"])
            self.outputs[outputName] = tmpPlug

        self.Compile()
        
    def Compile(self) -> None:
        """
        Compiles the node code to fasten the code execution
        """
        self.opCompiledCode = compile(self.opCode, "compiledCode", "exec")

    def UpdateEnv(self, environment : Environment = None) -> None:
        """
        """
        if environment is not None:
            self.environment.Variables.update(environment.Variables)

        self.environment.Set("NODE_NAME", self.GetName())

    def SetEnv(self, environment : Environment) -> None:
        """
        """
        self.environment = environment