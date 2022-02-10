import sys, time, traceback
from datetime import datetime

class Level():
    def __init__(self, val, desc):
        self.value = val
        self.description = desc

    def __new__(cls, val, desc):
        member = object.__new__(cls)
        member.value = val
        member.description = desc
        return member

    def GetAsString(self):
        return self.description

    def Get(self):
        return self.value


class LogLevel(Level):
    ERROR = Level(0, "ERROR")
    WARNING = Level(1, "WARNING")
    MESSAGE = Level(2, "MESSAGE")
    VERBOSE = Level(3, "VERBOSE")
    DIAGNOSTIC = Level(4, "DIAGNOSTIC")
    DEBUG = Level(5, "DEBUG")


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

            message = "[{0}] {1} : {2}\n{3}".format(level.GetAsString(), current_time, input, tracebackMessage)
            
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