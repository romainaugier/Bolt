import time

class Timer():
    """
    """
    @staticmethod
    def Start() -> float:
        """
        """
        return time.perf_counter()
    
    @staticmethod
    def Stop() -> float:
        """
        """
        return time.perf_counter()

    @staticmethod
    def Time(start : float, end : float) -> float:
        """
        """
        return start - end