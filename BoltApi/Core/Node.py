from ast import literal_eval
from enum import IntEnum
import re, copy, os, threading, io

import BoltApi.Core.FileSystem as FileSystem
from BoltApi.Core.Logger import *
from BoltApi.Core.Environment import *
from BoltApi.Utils.Timer import Timer

# Pre declaration of classes

class Node():
    pass

class Plug():
    pass

# Plug type enumeration

class PlugType(IntEnum):
    """
    Plug types available
    
    Plugs corresponds to both input and output of a node
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

def GetPlugTypeAsStr(plugType : PlugType) -> str:
    """
    Returns the plug type as a string
    """
    if plugType == PlugType.INT:
        return "int"
    elif plugType == PlugType.INT2:
        return "int2"
    elif plugType == PlugType.INT3:
        return "int3"
    elif plugType == PlugType.FLOAT:
        return "float"
    elif plugType == PlugType.FLOAT2:
        return "float2"
    elif plugType == PlugType.FLOAT3:
        return "float3"
    elif plugType == PlugType.STR:
        return "str"
    elif plugType == PlugType.BOOL:
        return "bool"
    elif plugType == PlugType.LIST:
        return "list"
    elif plugType == PlugType.DICT:
        return "dict"
    elif plugType == PlugType.CUSTOM:
        return "custom"
    else:
        return "custom"

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
        self.plugs : list = []
        self.color = [0, 0, 0]
        self.iconPath = ""
        self.category = ""
        self.opCode = ""
        
    @staticmethod
    def CleanBrackets(text : str) -> str:
        """
        Removes brackets [] from a string
        Mostly used to ease the parsing process
        
        Args:
            text (str) : text to remove brackets from
            
        Returns:
            str: clean text
        """
        clean1 = text.replace("[", "")
        clean2 = clean1.replace("]", "")

        return clean2

    @staticmethod
    def SplitEqual(text : str) -> list:
        """
        Split a string with the '=' sign
        Mostly used to ease the parsing process
        
        Args: 
            text (str): text to split
            
        Returns:
            list: list containing the string before and after the '=' sign
        """
        return text.split("=")

    def PreProcess(self, text : str) -> str:
        """
        Preprocesses the file to check if there are any error to return
        and removes comment
        
        Args:
            text (str): text to preprocess
            
        Returns:
            str: preprocessed text
        """
        commentPattern = re.compile(r"\s+\/\/.+|\/\/.+")

        textWithoutComments = re.sub(commentPattern, "", text)

        return textWithoutComments

    def GetPlugType(self, plugTypeStr : str) -> PlugType:
        """
        Returns the plugtype given a string that

        Args:
            plugTypeStr (str): string containing the plugType

        Returns:
            PlugType: PlugType enumeration corresponding to the given string
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
        else:
            return PlugType.CUSTOM

    def GetAttributes(self, lines : list[str], lineIndex : int) -> int:
        """
        Parse the attributes of the node definition
        
        Args:
            lines (str): list containing the lines of the node definition file
            lineIndex (int): current line index to start the parsing from
        
        Returns:
            int : last line index of the attributes block
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
                
            elif line.startswith("category"):
                lineSplit = self.SplitEqual(line)
                category = lineSplit[1].strip()
                self.category = category

            elif line.startswith("# EndAttr"):
                return lineIndex + 1
            
            lineIndex += 1

    def GetPlugs(self, lines : list[str], lineIndex : int) -> int:
        """
        Parse the plugs of the node definition
        
        Args:
            lines (str): list containing the lines of the node definition file
            lineIndex (int): current line index to start the parsing from
        
        Returns:
            int : last line index of the plugs block
        """
        tmpShortName = ""
        tmpLongName = ""
        tmpValue = None
        tmpType = None
        tmpExposed = False
        tmpHidden = False
        tmpExposedToGraph = False

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
                            newPlug.SetHidden(tmpHidden)
                            newPlug.SetExposedToGraph(tmpExposedToGraph)

                            if tmpShortName.startswith("out"):
                                newPlug.SetExposed(False)
                                newPlug.SetHidden(False)
                                newPlug.SetExposedToGraph(False)

                            self.plugs.append(newPlug)

                            tmpShortName = ""
                            tmpLongName = ""
                            tmpValue = None
                            tmpType = None
                            tmpExposed = False
                            tmpExposedToGraph = False
                            tmpHidden = False

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

                        elif parmLine.startswith("exposed "):
                            lineSplit = self.SplitEqual(parmLine)
                            tmpExposed = True if "True" in lineSplit[1] else False
                        
                        elif parmLine.startswith("exposedToGraph"):
                            lineSplit = self.SplitEqual(parmLine)
                            tmpExposedToGraph = True if "True" in lineSplit[1] else False
                        
                        elif parmLine.startswith("hidden"):
                            lineSplit = self.SplitEqual(parmLine)
                            tmpHidden = True if "True" in lineSplit[1] else False
                        
                        lineIndex += 1

            lineIndex += 1

    def GetOpCode(self, lines : list[str], lineIndex : int) -> int:
        """
        Parse the op code of the node definition
        
        Args:
            lines (str): list containing the lines of the node definition file
            lineIndex (int): current line index to start the parsing from
        
        Returns:
            int : last line index of the opcode block
        """
        while True:
            opLine = lines[lineIndex]

            if opLine.startswith("# EndOp"):
                return lineIndex + 1
            else:
                self.opCode += opLine + "\n"
                lineIndex += 1

    def Parse(self, nodeFile : str) -> dict:
        """
        Parse the node definition and returns it as a dictionnary
        
        Args: 
            nodeFile (str): path to the node definition file
        
        Returns:
            dict : node content as dictionnary
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
                    index = self.GetOpCode(lines, index + 1)

                else:
                    index += 1

        definition["name"] = self.name
        definition["color"] = self.color
        definition["iconPath"] = self.iconPath
        definition["category"] = self.category
        definition["opCode"] = self.opCode
        definition["plugs"] = self.plugs

        return definition

class Plug():
    """
    A Plug represents a node input or output

    A Plug has multiple attributes that defines how it can behave in the graph :
    - Exposed = The plug is not connectable to other plugs but can be set as a parameter. Exposed plugs must be input plugs
    - Hidden = The plug is not connectable to other plugs and does not appear in the interface, but can be set as a parameter 
               and will be exposed
    - Exposed To Graph = The plug is not connectable to other plugs but can be set as a parameter and also as a parameter of the graph.
                         It can be useful when you have to deal with large graphs to expose the few important parameters of the nodes
    """
    
    isExposed = False
    isExposedToGraph = False
    isHidden = False
    
    def __init__(self, shortName : str, longName : str, parentNode : Node, data = None, dataType : PlugType = None, index : int = 0, connectedPlug : Plug = None):
        """
        """
        self.shortName : str = shortName
        self.longName : str = longName
        self.parentNode : Node = parentNode
        self.index : int = index
        self.connectedPlugs : list = []

        if connectedPlug is not None:
            self.connectedPlugs.append(connectedPlug)

        self.data = data
        self.defaultData = data
        self.type : PlugType = dataType
        self.isExposed = False
        self.isExposedToGraph = False
        self.isHidden = False

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

    def GetNodeName(self) -> str:
        """
        Returns:
            str: name of the parent node
        """
        return self.parentNode.GetName()

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

    def IsExposedToGraph(self) -> bool:
        """
        Returns:
            bool: True if the plug is exposed to graph
        """
        return self.isExposedToGraph

    def SetExposedToGraph(self, exposedToGraph : bool = True) -> None:
        """
        Sets the plug graph exposition state

        Args:
            exposedToGraph (bool, optional): state of graph exposition. Defaults to True.
        """
        if exposedToGraph and not self.isExposed:
            self.SetExposed(True)

        self.isExposedToGraph = exposedToGraph

    def IsHidden(self) -> bool:
        """
        Returns:
            bool: True if the plug is hidden
        """
        return self.isHidden

    def SetHidden(self, isHidden : bool = True) -> None:
        """
        Sets the plug to be hidden or not

        Args:
            isHidden (bool, optional): hidden state of the plug. Defaults to True.
        """
        if isHidden and not self.isExposed:
            self.SetExposed(True)

        self.isHidden = isHidden

    def IsConnected(self) -> bool:
        """
        Returns:
            bool: if the plug is connected to another plug
        """
        if len(self.connectedPlugs) > 0:
            return True
        else:
            return False
    
    def GetConnections(self) -> list:
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
    
    def GetDefaultData(self):
        """
        Returns:
            Any: default data of the plug
        """
        return self.defaultData

    def SetData(self, data) -> None:
        """
        Set the data of the plug

        Args:
            data (any): data to set
        """
        self.data = data
        
    def SetDefaultData(self, data) -> None:
        """
        Sets the default data of this plug
        """
        self.defaultData = data
    
    def Connect(self, plug : Plug) -> None:
        """
        Connects this plug to another plug

        Args:
            plug (Plug): plug to connect the current plug to
        """
        if plug is not None:
            if (self.IsExposed() or plug.IsExposed() or 
                self.IsExposedToGraph() or plug.IsExposedToGraph() or
                self.IsHidden() or plug.IsHidden()):
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
        self.isCooking = False
        self.isCooked = False

        # Nodes can be disabled so the graph will bypass them
        # If a node is disabled, all its outputs will have the value
        # of the input 1
        self.isDisabled = False
        
        # Special case for if begin/end nodes
        self.isIfBegin = False
        self.isIfEnd = False
        self.isInsideIfBlock = False
        
        # Special case for forloop begin/end nodes
        self.isForBegin = False
        self.isForEnd = False

        self.cookTime = None
        self.hasError = False
        self.errorMessage = ""
        self.hasWarning = False
        self.warningMessage = ""
        self.inQueue = False
        self.inTempQueue = False
        self.lock = threading.Lock()
        self.name = ""
        self.inputs : dict = {}
        self.outputs : dict = {}
        self.color : list = []
        self.iconPath = ""
        self.category = ""
        self.nodeType = ""
        self.definitionPath = ""
        
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

    def GetLock(self) -> threading.Lock:
        """
        """
        return self.lock

    def GetInputCount(self) -> int:
        """
        Returns:
            int: number of inputs
        """
        return len(self.inputs.keys())
    
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
    
    def ReloadOpCode(self) -> None:
        """
        Reloads the opcode from the definition file
        """
        tmpNode = Node(self.environment)
        tmpNode.Load(self.definitionPath)
        
        self.SetOpCode(tmpNode.GetOpCode())
        self.Compile()
    
    def Compile(self) -> None:
        """
        Compiles the node code to fasten the code execution
        """
        self.opCompiledCode = compile(self.opCode, "compiledCode", "exec")

    def SetID(self, id : str) -> None:
        """
        Sets the id of the node
        """
        self.id = id

    def GetID(self) -> str:
        """
        Returns:
            str: node unique id
        """
        return self.id

    def SetColor(self, color : list) -> None:
        """
        Set the node rgb color (for interface)

        Args:
            color (list[float]): r, g, and v values of the node color
        """
        assert(len(color) == 3)
        self.color = color

    def GetColor(self) -> list:
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

    def SetCategory(self, category : str) -> None:
        """
        """
        self.category = category

    def GetCategory(self) -> str:
        """
        Returns:
            str: node category
        """
        return self.category
    
    def SetNodeType(self, type : str) -> None:
        """
        """
        self.nodeType = type
    
    def GetNodeType(self) -> str:
        """
        Returns:
            str: node type
        """
        return self.nodeType

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
        self.isCooked = not isDirty
        
    def IsDirty(self) -> bool:
        """
        Returns:
            bool: dirty state of the node
        """
        return self.isDirty

    def IsCooked(self) -> bool:
        """
        Returns:
            bool: cooked state of the node
        """
        return self.isCooked

    def SetCooked(self, isCooked : bool = True) -> None:
        """
        """
        self.isCooked = isCooked

    def IsCooking(self) -> bool:
        """
        Returns:
            bool: cooking state of the node
        """
        return self.isCooking

    def IsDisabled(self) -> bool:
        """
        Returns:
            bool: disabled state of the node
        """ 
        return self.isDisabled

    def SetDisabled(self, isDisabled : bool = True) -> None:
        """
        """
        self.isDisabled = not self.isDisabled

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
    
    def HasNoInputsConnected(self) -> bool:
        """
        Checks if the node has no inputs connectedPlugs

        Returns:
            bool:
        """
        for name, input in self.inputs.items():
            if input.IsConnected() and not input.IsExposed():
                return False

        return True
    
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
    
    def HasNoOutputsConnected(self) -> bool:
        """
        Checks if the node has no outputs connected

        Returns:
            bool:
        """
        for name, output in self.outputs.items():
            if output.IsConnected() and not output.IsExposed():
                return False

        return True

    def SetPlugValue(self, plugName : str, value) -> None:
        """
        """
        if plugName in self.inputs:
            self.inputs[plugName].SetData(value)
        
    def Cook(self) -> None:
        """
        Executes the node operation
        If the node is disabled, we just pass the first input value to all the outputs
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

            locals = {}
                
            for inputName, input in self.inputs.items():
                input.UpdateInputs()
                locals[inputName] = input.GetData()
                
            globals = { "BoltTempDir" : FileSystem.GetRoamingDataDir,
                        "BoltTempScript" : FileSystem.GetNewRandomPyFile,
                        "BoltLogError" : self.LogError,
                        "BoltLogWarning" : self.LogWarning,
                        "BoltLogMessage" : self.LogMessage,
                        "BoltError" : self.ReportError,
                        "BoltWarning" : self.ReportWarning }
            
            try:
                exec(self.opCompiledCode, globals, locals)
            except Exception as err:
                self.ReportError()
                self.LogError(f"Error cooking node {self.GetName()}")
                self.errorMessage = err
                self.cookTime = None
                self.isCooking = False
                self.isCooked = False
                return

            # Get outputs         
            for outputName, output in self.outputs.items():
                if outputName in locals:
                    output.SetData(locals[outputName])

            with self.GetLock():
                self.isDirty = False
                self.isCooking = False
                self.isCooked = True

            endTime = Timer.Stop()

            self.cookTime = Timer.Time(startTime, endTime)
        else:
            firstInput = self.GetInput(index=0)
            firstInput.UpdateInputs()

            for outputName, output in self.outputs.items():
                output.SetData(firstInput.GetData())

    def ReportError(self) -> None:
        """
        Emit an error signal
        """
        self.hasError = True
        self.isCooked = False

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

    def HasWarning(self) -> bool:
        """
        Returns if the node has a warning
        """
        return self.hasWarning

    def GetWarningMessage(self) -> str:
        """
        Returns:
            str: Warning message
        """
        return self.warningMessage

    def LogError(self, message) -> None:
        """
        Log an error to the passed logger. This function is made to be 
        used in the user code
        """
        self.logger.Log(LogLevel.ERROR, f"(Node : {self.GetName()}) : {message}", getTraceback=True)
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
        
    # Special functions for blocks (if/for)
    
    def IsInsideIfBlock(self) -> bool:
        """
        """
        return self.isInsideIfBlock
    
    def SetInsideIfBlock(self) -> None:
        """
        """
        self.isInsideIfBlock = True
    
    def IsIfBeginBlock(self) -> bool:
        """
        """
        return self.isIfBegin
    
    def SetIfBeginBlock(self) -> None:
        """
        """
        self.isIfBegin = True
    
    def IsIfEndBlock(self) -> bool:
        """
        """
        return self.isIfEnd
    
    def SetIfEndBlock(self) -> None:
        """
        """
        self.isIfEnd = True
    
    def IsForBeginBlock(self) -> bool:
        """
        """
        return self.isForBegin
    
    def IsForEndBlock(self) -> bool:
        """
        """
        return self.isForEnd
    
    def SetAssociatedBlockBegin(self, nodeId : str) -> None:
        """
        If this node is an end block, sets the associated begin block id

        Args:
            nodeId (str): associated if block begin node id
        """
        self.associatedBlockBeginId = nodeId
        
    def GetAssociatedBlockBegin(self) -> str:
        """
        """
        return self.associatedBlockBeginId
        
    def SetAssociatedBlockEnd(self, nodeId : str) -> None:
        """
        If this node is an begin block, sets the associated end blocks

        Args:
            nodeId (str): associated if block end node if
        """
        self.associatedBlockEndId = nodeId
        
    def GetAssociatedBlockEnd(self) -> str:
        """
        """
        return self.associatedBlockEndId
    
    # I/O Functions
        
    def Load(self, nodeDefinitionPath : str) -> None:
        """
        Loads a node definition and compiles the op code

        Args:
            nodeDefinitionPath (str): path to the node definition file
        """
        self.definitionPath = nodeDefinitionPath
        
        nodeDefinitionPath = self.environment.ReplaceInString(nodeDefinitionPath)
        
        parser = Parser()

        nodeDefinition = parser.Parse(nodeDefinitionPath)

        self.name = nodeDefinition["name"]
        self.color = nodeDefinition["color"]
        self.iconPath = nodeDefinition["iconPath"]
        self.category = nodeDefinition["category"]
        self.opCode = nodeDefinition["opCode"]
        self.nodeType = f"{self.category}/{self.name}"

        if not os.path.exists(self.GetIconPath()):
            self.iconPath = ""

        for plug in nodeDefinition["plugs"]:
            if plug.GetShortName().startswith("in"):
                plug.SetNode(self)
                self.inputs[plug.GetShortName()] = plug
            elif plug.GetShortName().startswith("out"):
                plug.SetNode(self)
                self.outputs[plug.GetShortName()] = plug

        self.UpdateEnv()

        self.Compile()
        
    def GetDefinitionPath(self) -> str:
        """
        """
        return self.definitionPath
    
    def SetDefinitionPath(self, path : str) -> None:
        """
        """
        self.definitionPath = path

    def ToDict(self) -> dict:
        """
        Translates the node to a dict representation

        Returns:
            dict: node as a dictionnary
        """
        nodeAsDict = {}

        nodeAsDict["name"] = self.GetName()
        nodeAsDict["category"] = self.GetCategory()
        nodeAsDict["id"] = self.GetID()
        nodeAsDict["color"] = self.GetColor()
        nodeAsDict["iconPath"] = self.GetIconPathRaw()
        nodeAsDict["definitionPath"] = self.GetDefinitionPath()
        nodeAsDict["nodeType"] = self.GetNodeType()
        nodeAsDict["opCode"] = self.GetOpCode()
        nodeAsDict["disabled"] = self.IsDisabled()
        
        if self.IsIfBeginBlock():
            nodeAsDict["isIfBegin"] = True
            nodeAsDict["associatedEndBlockId"] = self.GetAssociatedBlockEnd()
        else:
            nodeAsDict["isIfBegin"] = False
            nodeAsDict["associatedEndBlockId"] = None
            
        if self.IsIfEndBlock():
            nodeAsDict["isIfEnd"] = True
            nodeAsDict["associatedBeginBlockId"] = self.GetAssociatedBlockBegin()
        else:
            nodeAsDict["isIfEnd"] = False
            nodeAsDict["associatedBeginBlockId"] = None

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
                                                                        "isHidden" : input.IsHidden(),
                                                                        "isExposedToGraph" : input.IsExposedToGraph(),
                                                                        "data" : input.GetData(), 
                                                                        "defaultData" : input.GetDefaultData(),
                                                                        "type" : input.GetType(),
                                                                        "connectionName" : connection.GetShortName(), 
                                                                        "connectionNodeId" : connection.GetNode().GetID() })
            else:
                nodeAsDict["inputs"][input.GetShortName()] = [{ "shortName" : input.GetShortName(),
                                                               "longName" : input.GetLongName(),
                                                               "index" : input.GetIndex(),
                                                               "isExposed" : input.IsExposed(),
                                                               "isHidden" : input.IsHidden(),
                                                               "isExposedToGraph" : input.IsExposedToGraph(),
                                                               "data" : input.GetData(), 
                                                               "defaultData" : input.GetDefaultData(),
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
                                                                    "isHidden" : output.IsHidden(),
                                                                    "isExposedToGraph" : output.IsExposedToGraph(),
                                                                    "data" : output.GetData(), 
                                                                    "defaultData" : output.GetDefaultData(),
                                                                    "type" : output.GetType(),
                                                                    "connectionName" : connection.GetShortName(), 
                                                                    "connectionNodeId" : connection.GetNode().GetID() })
            else:
                nodeAsDict["outputs"][output.GetShortName()] = [{ "shortName" : output.GetShortName(),
                                                                 "longName" : output.GetLongName(),
                                                                 "index" : output.GetIndex(),
                                                                 "isExposed" : output.IsExposed(),
                                                                 "isHidden" : output.IsHidden(),
                                                                 "isExposedToGraph" : output.IsExposedToGraph(),
                                                                 "data" : output.GetData(), 
                                                                 "defaultData" : output.GetDefaultData(),
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
        self.SetCategory(nodeAsDict["category"])
        self.SetID(nodeAsDict["id"])
        self.SetColor(nodeAsDict["color"])
        self.SetIconPath(nodeAsDict["iconPath"])
        self.SetNodeType(nodeAsDict["nodeType"])
        self.SetOpCode(nodeAsDict["opCode"])
        
        if "definitionPath" in nodeAsDict:
            self.SetDefinitionPath(nodeAsDict["definitionPath"])
        
        if "disabled" in nodeAsDict:
            self.isDisabled = nodeAsDict["disabled"]
        
        if "isIfBegin" in nodeAsDict or "isIfEnd" in nodeAsDict:
            if nodeAsDict["isIfBegin"]: 
                self.SetIfBeginBlock()
                self.SetAssociatedBlockEnd(nodeAsDict["associatedEndBlockId"])
            elif nodeAsDict["isIfEnd"]: 
                self.SetIfEndBlock()
                self.SetAssociatedBlockBegin(nodeAsDict["associatedBeginBlockId"])

        for inputName, input in nodeAsDict["inputs"].items():
            input = input[0]
            tmpPlug = Plug(input["shortName"], input["longName"], self, input["defaultData"], input["type"])
            tmpPlug.SetData(input["data"])
            tmpPlug.SetExposed(input["isExposed"])
            tmpPlug.SetHidden(input["isHidden"])
            tmpPlug.SetExposedToGraph(input["isExposedToGraph"])
            tmpPlug.SetIndex(input["index"])
            self.inputs[inputName] = tmpPlug

        for outputName, output in nodeAsDict["outputs"].items():
            output = output[0]
            tmpPlug = Plug(output["shortName"], output["longName"], self, output["defaultData"], output["type"])
            tmpPlug.SetData(output["data"])
            tmpPlug.SetExposed(output["isExposed"])
            tmpPlug.SetHidden(output["isHidden"])
            tmpPlug.SetExposedToGraph(output["isExposedToGraph"])
            tmpPlug.SetIndex(output["index"])
            self.outputs[outputName] = tmpPlug

        self.Compile()
        
    def ToFile(self) -> str:
        """
        Returns the node content as a string definition used in node files

        Returns:
            str: node content as file
        """
        nodeAsDict = self.ToDict()
        
        stream = io.StringIO("")
        
        stream.write("// Node Definition automatically generated by Bolt\n\n")
        
        # Attributes
        stream.write("# BeginAttr\n\n")
        stream.write(f"name = {nodeAsDict['name']}\n")
        stream.write(f"category = {nodeAsDict['category']}\n")
        stream.write(f"color = {nodeAsDict['color']}\n")
        stream.write(f"icon = {nodeAsDict['iconPath']}\n")
        stream.write("\n# EndAttr\n\n")
        
        # Plugs
        stream.write("# BeginPlugs\n")
        
        for inputName, input in nodeAsDict["inputs"].items():
            input = input[0]
            
            if input["type"] == 7:
                input["data"] = f"\"{input['data']}\""
            
            stream.write("\n# BeginPlug\n\n")
            stream.write(f"shortName = {input['shortName']}\n")
            stream.write(f"longName = {input['longName']}\n")
            stream.write(f"defaultValue = {input['data']}\n")
            stream.write(f"type = {GetPlugTypeAsStr(input['type'])}\n")
            stream.write(f"exposed = {input['isExposed']}\n")
            stream.write(f"hidden = {input['isHidden']}\n")
            stream.write(f"exposedToGraph = {input['isExposedToGraph']}\n")
            stream.write("\n# EndPlug\n")

        for outputName, output in nodeAsDict["outputs"].items():
            output = output[0]
            
            if output["type"] == 7:
                output["data"] = f"\"{output['data']}\""
            
            stream.write("\n# BeginPlug\n\n")
            stream.write(f"shortName = {output['shortName']}\n")
            stream.write(f"longName = {output['longName']}\n")
            stream.write(f"defaultValue = {output['data']}\n")
            stream.write(f"type = {GetPlugTypeAsStr(output['type'])}\n")
            stream.write(f"exposed = {output['isExposed']}\n")
            stream.write(f"hidden = {output['isHidden']}\n")
            stream.write(f"exposedToGraph = {output['isExposedToGraph']}\n")
            stream.write("\n# EndPlug\n")
        
        stream.write("\n# EndPlugs\n\n")
        
        # OpCode
        stream.write("# BeginOp\n\n")
        stream.write(nodeAsDict["opCode"])
        stream.write("\n# EndOp\n")
        
        return stream.getvalue()
        
    # Env Functions

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