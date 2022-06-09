import sys, time, traceback, colorama, platform
from datetime import datetime


if platform.system() == 'Windows':
    colorama.init()


class Level():
    def __init__(self, levelIndex, levelDesc, levelColor):
        self.index = levelIndex
        self.description = levelDesc
        self.color = levelColor

    def __new__(cls, val, desc, col):
        member = object.__new__(cls)
        member.index = val
        member.description = desc
        member.color = col
        return member

    def GetAsString(self):
        return self.description

    def Get(self):
        return self.index
    
    def GetAsColor(self):
        return self.color


class LogLevel(Level):
    ERROR = Level(0, "ERROR", colorama.Fore.RED)
    WARNING = Level(1, "WARNING", colorama.Fore.YELLOW)
    MESSAGE = Level(2, "MESSAGE", colorama.Fore.WHITE)
    VERBOSE = Level(3, "VERBOSE", colorama.Fore.WHITE)
    DIAGNOSTIC = Level(4, "DIAGNOSTIC", colorama.Fore.GREEN)
    DEBUG = Level(5, "DEBUG", colorama.Fore.WHITE)


class Logger():
    """
    Utility class to log informations to the user
    """
    
    file = None
    
    def __init__(self, level=LogLevel.WARNING, logToConsole=True, logToFile=False, logToCustomConsole=False, file=None):
        self.level = level
        self.logToConsole = logToConsole
        self.logToFile = logToFile
        self.logToCustomConsole = logToCustomConsole
        self.callbackFunction = None
        
        if file:
            self.file = open(file, "w")
            self.LogToFile(self.Log(LogLevel.MESSAGE, "File logging session started"))
            
    def __del__(self):
        if self.file:
            self.file.close()

    def SetCustomConsoleCallback(self, callbackFunction) -> None:
        """
        Callback function called when the user wants the message and level to be sent to a specific function
        """
        self.callbackFunction = callbackFunction
        self.logToCustomConsole = True
    
    def Log(self, level, input, getTraceback=False):
        """
        Main logging method
        """
        if level.Get() <= self.level.Get():
            now = datetime.now()
            current_time = now.strftime("%H:%M:%S")

            traceBack = traceback.format_exc()

            if getTraceback and traceBack is not None:
                tracebackMessage = "{0}\n".format(traceBack)
            else:
                tracebackMessage = ""

            message = "{0}[{1}] {2} : {3}\n{4}".format(level.GetAsColor(), level.GetAsString(), current_time, input, tracebackMessage)
            messageClean = "[{0}] {1} : {2}\n{3}".format(level.GetAsString(), current_time, input, tracebackMessage)
            
            if self.logToConsole: 
                if level == LogLevel.ERROR: 
                    sys.__stderr__.write(message)
                    sys.__stderr__.write(colorama.Fore.RESET)
                else:
                    sys.__stdout__.write(message)
                    sys.__stdout__.write(colorama.Fore.RESET)
            
            self.__LogToFile(messageClean)

            self.__LogToCustomCallback(level, messageClean)

                
            return message

        else:
            return ""
    
    def __LogToFile(self, logMessage):
        """
        Log the message to a file if enabled
        """
        if self.logToFile:
            self.file.write(logMessage)

    def __LogToCustomCallback(self, logLevel, logMessage):
        """
        Log the message and the level to the user callback function
        """
        if self.logToCustomConsole and self.callbackFunction is not None:
            self.callbackFunction(logLevel, logMessage)


class StdOut():
    """
    Simple class with a write function that replace stdout to add a few infos
    """
    def write(text : str):
        """
        Args:
            text (str): text to write to __stdout__
        """
        now =  datetime.now()
        current_time = now.strftime("%H:%M:%S")

        # To keep python 2.7 compatibility we do not use f strings
        message = "[STDOUT] {0} : {1}\n".format(current_time, text)
        
        sys.__stdout__.write(message)
        sys.__stdout__.write(colorama.Fore.RESET)
        
        
class StdErr():
    """
    Simple class with a write function that replace stderr to add a few infos
    """
    def write(text : str):
        """
        Args:
            text (str): text to write to __stderr__
        """
        now =  datetime.now()
        current_time = now.strftime("%H:%M:%S")

        # To keep python 2.7 compatibility we do not use f strings
        message = "{0}[STDERR] {1} : {2}\n".format(LogLevel.ERROR.GetAsColor(), current_time, text)
        
        sys.__stderr__.write(message)
        sys.__stderr__.write(colorama.Fore.RESET)