import sys, os
from optparse import OptionParser

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from BoltApi.Core.Logger import *
from BoltCommand.Cook import CookCmd

class Command():
    """
    BoltCommand is a utility module to call various functions from the command line.
    Its main utility is to launch graph cooking as subprocesses 
    """

    progressCallbackPattern = "PROGRESS : %d%%"

    def __init__(self):
        """
        Initializes the command by reading arguments and starts the command
        """
        self.logger = Logger(level=LogLevel.MESSAGE)

        self.parser = OptionParser()

        self.parser.add_option("-m", "--mode", dest="mode", action="store", default="Cook",
        help="""Command mode :
    - Cook : cooks the graph passed to -g|--graph arg
    - Modify : launch a python interpreter to modify the graph passed to -g|--graph argument (not implemented yet)""")

        self.parser.add_option("-g", "--graph", dest="graph", action="store", 
        help="Path to the graph file to cook")

        self.parser.add_option("-p", "--progressPattern", dest="progressPattern", action="store", default="PROGRESS : %d%%",
        help="Pattern used to output the cooking progress")

        (options, args) = self.parser.parse_args()

        if options.graph is None:
            self.logger.Log(LogLevel.ERROR, "Missing graph filepath, exiting BoltCommand...")
            return

        if options.progressPattern is not None:
            self.progressCallbackPattern = options.progressPattern

        if options.mode == "Cook":
            CookCmd(options.graph, self.logger, self.ProgressCallbackFunc)

    def ProgressCallbackFunc(self, progress : int) -> None:
        """
        """
        sys.stdout.write(self.progressCallbackPattern % progress)
        sys.stdout.write("\n")


if __name__ == "__main__":
    command = Command()