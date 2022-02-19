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
    def __init__(self, level=LogLevel.WARNING, logToConsole=True, logToFile=False, file=None):
        self.level = level
        self.logToConsole = logToConsole
        self.logToFile = logToFile
        
        if file:
            self.file = open(file, "w")
            self.LogToFile(self.Log(LogLevel.MESSAGE, "File logging session started"))
        else:
            self.file = None
            
    def __del__(self):
        if self.file:
            self.file.close()
    
    def Log(self, level, input, getTraceback=False):
        """
        Main logging method
        """
        if level.Get() <= self.level.Get():
            now = datetime.now()
            current_time = now.strftime("%H:%M:%S")

            tracebackMessage = traceback.format_exc() + "\n" if getTraceback else ""

            message = "{0}[{1}] {2} : {3}\n{4}".format(level.GetAsColor(), level.GetAsString(), current_time, input, tracebackMessage)
            
            if self.logToConsole: 
                sys.stdout.write(message)
            
            self.LogToFile(message)
                
            return message

        else:
            return ""
    

    def LogToFile(self, input):
        """
        Log the message to a file if enabled
        """
        if self.logToFile:
            self.file.write(input)