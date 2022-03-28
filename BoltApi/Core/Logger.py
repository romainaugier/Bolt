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

            tracebackMessage = traceback.format_exc() + "\n" if getTraceback else ""

            message = "{0}[{1}] {2} : {3}\n{4}".format(level.GetAsColor(), level.GetAsString(), current_time, input, tracebackMessage)
            messageClean = "[{0}] {1} : {2}\n{3}".format(level.GetAsString(), current_time, input, tracebackMessage)
            
            if self.logToConsole: 
                if level == LogLevel.ERROR: 
                    sys.stderr.write(message)
                    sys.stdout.write(colorama.Fore.RESET)
                else:
                    sys.stdout.write(message)
                    sys.stdout.write(colorama.Fore.RESET)
            
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
