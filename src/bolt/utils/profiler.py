import time, os
from contextlib import ContextDecorator

import bolt.utils.log as log

class Timer():
    """
    Simple timer with static functions
    """
    @staticmethod
    def start() -> float:
        """
        """
        return time.perf_counter()
    
    @staticmethod
    def stop() -> float:
        """
        """
        return time.perf_counter()
    
    def time(start : float,
             end : float) -> float:
        """
        """
        return end - start
    
class Profiler(ContextDecorator):
    """
    Simple profiler for scoped/function profiling
    """
    def __init__(self,
                 scope_name : str = None) -> None:
        """
        """
        self.scope_name = scope_name
    
    def __enter__(self):
        """
        """
        self.start = time.perf_counter()
        
    def __exit__(self,
                 *args):
        """
        """
        self.end = time.perf_counter()
        
        elapsed = self.end - self.start
        
        if self.scope_name is None:
            msg = f"Scoped profiler : Elapsed time {elapsed:.3f}s"
        else:
            msg = f"Scoped profiler ({self.scope_name}) : Elapsed time {elapsed:.3f}s"
        
        log.info(msg)