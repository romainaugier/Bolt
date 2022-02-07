
# Pre declaration of classes

class Node():
    pass

class Plug():
    pass


# Definitions of classes

class Parser():
    """
    Utility class to parse node definition files
    """
    def __init__(self):
        """
        """
        self.name = None
        self.inputCount = 0
        self.outputCount = 0
        self.parameters = []
        self.color = None
        self.opCode = None
        
    @staticmethod
    def CleanBrackets(text):
        """
        """
        clean1 = text.replace("[", "")
        clean2 = clean1.replace("]", "")

        return clean2

    @staticmethod
    def SplitEqual(text):
        """
        """
        return text.split("=")

    def Parse(self, nodeFile):
        """
        """
        definition = {}

        index = 0

        with open(nodeFile, "r") as file:
            lines = file.readlines()
            lineCount = len(lines)   

            while index < lineCount:
                line = lines[index]

                if line.startswith("name"):
                    lineSplit = self.SplitEqual(line)
                    self.name = lineSplit[1]
                    
                    index += 1

                elif line.startswith("inputs"):
                    lineSplit = self.SplitEqual(line)
                    self.inputs = int(lineSplit[1])
                    
                    index += 1

                elif line.startswith("outputs"):
                    lineSplit = self.SplitEqual(line)
                    self.outputs = int(lineSplit[1])

                    index += 1

                elif line.startswith("color"):
                    lineSplit = self.SplitEqual(line)

                    self.color = []

                    colorsListStr = self.CleanBrackets(lineSplit[1]).split(",")

                    for colorStr in colorsListStr:
                        self.color.append(int(colorStr))
                    
                    index += 1

                elif line.startswith("longOp"):
                    lineSplit = self.SplitEqual(line)
                    if "False" in lineSplit[1]:
                        self.longOp = False
                    else:
                        self.longOp = True
                    
                    index += 1

                elif line.startswith("# Data"):
                    endData = False

                    while endData is False:
                        dataLine = lines[index]

                        if dataLine.startswith("# EndData"):
                            endData = True
                            break
                        elif dataLine.startswith("in"):
                            lineSplit = self.SplitEqual(dataLine)
                            data = None

                            if lineSplit[1].isdigit():
                                data = int(data)
                            elif lineSplit[1].isdecimal():
                                data = float(data)
                            elif "[" in lineSplit[1] or "]" in lineSplit[1]:
                                listItems = lineSplit[1].replace("[", "")
                                listItems = listItems.replace("]", "")
                                listItems = listItems.split(",")

                                data = []

                                for item in listItems:
                                    if item.isdigit():
                                        data.append(int(item))
                                    elif item.isdecimal():
                                        data.append(float(item))
                                    else:
                                        data.append(item)
                            elif "False" in lineSplit[1]:
                                data = False
                            elif "True" in lineSplit[1]:
                                data = True
                            
                            self.inData[lineSplit[0]] = data
                        elif dataLine.startswith("out"):
                            lineSplit = self.SplitEqual(dataLine)
                        else:
                            index += 1

                elif line.startswith("# BeginOp"):
                    endOp = False

                    self.op = ""
                    
                    while endOp is False:
                        opLine = lines[index]

                        if opLine.startswith("# EndOp"):
                            endOp = True
                            self.op += opLine
                            break
                        else:
                            self.op += opLine
                            index += 1

                else:
                    index += 1

        definition["name"] = self.name
        definition["inputs"] = self.inputs
        definition["color"] = self.color
        definition["longOp"] = self.longOp
        definition["op"] = self.op

        return definition

class Plug():
    """
    A Plug represents a node input or output
    """
    def __init__(self, name : str, parentNode : Node, connectedPlug : Plug = None):
        """
        """
        self.name = name
        self.parentNode = parentNode
        self.connectedPlug = connectedPlug
        self.data = None

    def Name(self):
        """
        Returns:
            str: name of the plug
        """
        return self.name
    
    def Node(self):
        """
        Returns:
            Node: parent node of the plug
        """
        return self.parentNode
    
    def Connection(self):
        """
        Returns:
            Plug: plug that the current plug is connected to (on another node)
        """
        return self.connectedPlug
    
    def Data(self):
        """
        Returns:
            Any: data of the plug
        """
        return self.data
    
    def Connect(self, plug : Plug):
        """
        Connects this plug to another plug

        Args:
            plug (Plug): plug to connect the current plug to
        """
        if plug.Node() == self.Node():
            return
        else:
            self.connectedPlug = plug
            
    def Disconnect(self):
        """
        Disconnects a plug from its connected plug (if it has any)
        """
        if self.connectedPlug is not None:
            self.connectedPlug.Disconnect()
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
        
    def ShortName(self):
        """
        Returns:
            str: short name of the parameter
        """
        return self.shortName

    def LongName(self):
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


class Node():
    """
    """
    def __init__(self):
        """
        """
        self.isDirty = True
        self.parameters = []
        self.inputs = []
        self.outputs = []
        
        self.inputCount = 0
        self.outputCount = 0
        
        self.opCode = ""
        self.opCompiledCode = ""
        
    def SetDirty(self):
        """
        Sets the node to be dirty (not cooked)
        """
        self.isDirty = True
        
    def IsDirty(self):
        """
        Returns:
            bool: dirty state of the node
        """
        return self.isDirty
    
    def GetInput(self, index : int):
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
    
    def GetInputs(self):
        """
        Returns:
            list of Plug: inputs of the node
        """
        return self.inputs
    
    def SetInput(self, plug : Plug, index : int):
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
            
    def GetOutput(self, index : int):
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
        
    def GetOutputs(self):
        """
        Returns:
            list: list of the output plugs
        """
        return self.outputs
        
    def Cook(self):
        """
        Executes the node operation
        """
        locals = {}
        
        for parameter in self.parameters:
            locals[parameter.ShortName()] = parameter.Value()
            
        for i, input in enumerate(self.inputs):
            locals[f"input{i}"] = input.Data()
            
        globals = {}
        
        exec(self.opCompiledCode, globals, locals)
        
        self.isDirty = False
        
    def Load(self, nodeDefinitionPath : str):
        """
        Loads a node definition and compiles the op code

        Args:
            nodeDefinitionPath (str): path to the node definition file
        """
        
    def Compile(self):
        """
        Compiles the node code to fasten the code execution
        """
        self.opCompiledCode = compile(self.opCode, "compiledCode", "exec")