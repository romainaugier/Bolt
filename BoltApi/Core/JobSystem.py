from enum import Enum

import subprocess, signal, os, threading, re

from BoltApi.Core.Graph import *
from BoltCommand.Command import *

class JobStatus(Enum):
    """
    """
    WAITING = 0
    COOKING = 1
    PAUSED = 2
    COMPLETE = 3
    STOPPED = 4

class Job():
    """
    The Job class holds the representation of a job and the functions
    needed to run, pause and kill it
    """
    def __init__(self, logger : Logger, environment : Environment, pathToGraphToRun : str = "") -> None:
        """
        """
        self.logger = logger
        self.environment = environment
        
        self.id = GetRandomStrId(8)
        
        self.dirPath, self.graphPath = CopyJob(self.id, pathToGraphToRun)
        
        self.progress = 0
        self.status = JobStatus.WAITING
        
        self.process = None
        self.progressThread = None
        
    def Start(self) -> None:
        """
        Starts the job process
        """
        if self.process is not None:
            self.logger.Log(LogLevel.ERROR, f"Job ({self.id}) is already running")
            return
        
        self.status = JobStatus.COOKING
        
        command = []
        
        if IsExecutable():
            command.append(self.environment.Get("BOLT_COMMAND"))
        else:
            command.append(self.environment.Get("BOLT_PYTHON_EXEC"))
            command.append(self.environment.Get("BOLT_COMMAND"))
            
        command.append("-m")
        command.append("Cook")
        
        command.append("-g")
        command.append(self.graphPath)
        
        self.process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        self.progressThread = threading.Thread(target=self.UpdateProgress)
        self.progressThread.start()
    
    def Pause(self) -> None:
        """
        """
        if self.process is not None:
            self.process.send_signal(signal.SIGSTOP)
            
            self.status = JobStatus.PAUSED
        
    def Resume(self) -> None:
        """
        """
        if self.process is not None:
            self.process.send_signal(signal.SIGCONT)
            
            self.status = JobStatus.COOKING
    
    def Stop(self) -> None:
        """
        """
        if self.process is not None:
            self.process.terminate()
        
            self.status = JobStatus.STOPPED
    
    def UpdateProgress(self) -> None:
        """
        """
        if self.process is not None:
            progressPattern = re.compile(r".*(\d+)%")
            
            stdout = self.process.stdout
            stderr = self.process.stderr
            
            while True:
                stdoutOutput = stdout.readline()
                stderrOutput = stderr.readline()

                if self.process.poll() is not None:
                    break
                
                if stdoutOutput:
                    match = re.search(progressPattern, stdoutOutput) 
                    
                    if match is not None:
                        progress = int(match.group(0))
                        self.progress = progress
                    else:
                        self.logger.Log(LogLevel.MESSAGE, f"Job ({self.id}) : STDOUT : {stdoutOutput}")
                if stderrOutput:
                    self.logger.Log(LogLevel.ERROR, f"Job ({self.id}) : STDERR : {stderrOutput}")
            