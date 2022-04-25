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
    FAILED = 4

class Job():
    """
    The Job class holds the representation of a job and the functions
    needed to run, pause and kill it
    """
    def __init__(self, logger : Logger, environment : Environment, pathToGraphToRun : str = "") -> None:
        """
        """
        self.logger = logger
        self.environment = copy.deepcopy(environment)
        
        self.id = GetRandomStrId(8)
        
        self.dirPath, self.graphPath = self.Copy(pathToGraphToRun)
        
        self.progress = 0
        self.status = JobStatus.WAITING
        
        self.process = None
        self.progressThread = None

    def Copy(self, pathToGraph : str) -> tuple:
        """
        Copies the given graph file to the roaming jobs dir with a random name

        Args:
            pathToGraph (str): path to the graph file to copy
            
        Returns:
            tuple(str): job directory path and copied graph file path
        """
        if not os.path.exists(pathToGraph):
            self.logger.Log(LogLevel.ERROR, f"Graph {pathToGraph} does not exist")

            self.status = JobStatus.FAILED
            
            return None, None
        
        graphName, graphExtension = os.path.splitext(os.path.basename(pathToGraph))
        
        jobDirName = self.id
        jobDirPath = f"{GetJobsDir()}/{jobDirName}"
        
        os.makedirs(jobDirPath)
        
        jobName = f"{graphName}_{GetCurrentTimeAsStr()}.{graphExtension}"
        jobPath = f"{jobDirPath}/{jobName}"
        
        shutil.copy(pathToGraph, jobPath)
        
        return jobDirPath, jobPath
        
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
            

class JobSystem():
    """
    """
    def __init__(self, environment : Environment, logger : Logger) -> None:
        """
        """
        self.environment = copy.deepcopy(environment)
        self.logger = logger