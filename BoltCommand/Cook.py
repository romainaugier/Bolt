import os, shutil

from BoltApi.Core.Graph import *
from BoltApi.Core.FileSystem import GetRoamingDataDir
from BoltApi.Utils.String import *


def CookCmd(graphFile : str, logger : Logger, progressCallbackFunction) -> None:
    """
    Cooks the given graph file

    To avoid interfering with the given graph, the actual graph that will be cooked
    is copied to the Bolt roaming directory, thus enabling the user to launch multiple
    cooks of the same graph and keep modifying it in the app if needed  

    Args:
        graphFile (_type_): file path of the graph to cook
        progressCallbackFunction (_type_): callback function to output progress
    """
    if not os.path.exists(graphFile):
        logger.Log(LogLevel.ERROR, f"Graph ({graphFile}) does not exist, exiting BoltCommand...")
        return

    roamingDir = GetRoamingDataDir()

    graphName, _ = os.path.splitext(os.path.basename(graphFile))
    newGraphPath = f"{roamingDir}/{graphName}_{GetCurrentTimeAsStr()}.bgraph"
    shutil.copyfile(graphFile, newGraphPath)

    logger.Log(LogLevel.MESSAGE, "Copied graph to temp directory, cooking will start soon...")

    graph = Graph(logger, Environment())
    graph.LoadFromFile(newGraphPath)

    graph.SetProgressCallback(progressCallbackFunction)

    graph.Cook(skipCookedNodes=False)

    logger.Log(LogLevel.MESSAGE, "Graph cooking finished, exiting BoltCommand...")