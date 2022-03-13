from enum import Enum

from BoltApi.Core.Graph import *

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
        
        self.graph = Graph(logger, environment, self.graphPath)
        self.graph.SetProgressCallback(self.UpdateProgress)
        
        self.progress = 0
        self.status = JobStatus.WAITING
        
    def Start(self) -> None:
        """
        """
        self.status = JobStatus.COOKING
        
        self.graph.Cook()
        
        self.status = JobStatus.COMPLETE
    
    def Pause(self) -> None:
        """
        """
        self.status = JobStatus.PAUSED
        
        self.graph.PauseCook()
        
    def Resume(self) -> None:
        """
        """
        self.status = JobStatus.COOKING
        
        self.graph.ResumeCook()
    
    def Stop(self) -> None:
        """
        """
        self.graph.StopCook()
        
        self.status = JobStatus.STOPPED
    
    def UpdateProgress(self, progress : int) -> None:
        """
        """
        self.progress = progress