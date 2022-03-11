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
        return end - start

    @staticmethod
    def TimeFunction(function) -> None:
        """
        Function decorator used to time a function

        Args:
            function (_type_): function to time
        """
        def _Time(*args, **kwargs):
            start = Timer.Start()
            
            function(args, kwargs)

            end = Timer.Stop()

            time = Timer.Time(start, end)

            print(f"{time:.3f}")

        return _Time