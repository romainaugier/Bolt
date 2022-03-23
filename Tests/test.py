import sys, os, copy, json

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from BoltApi.Core.Graph import *
from BoltApi.Core.Lib import *

from BoltApp import BOLTROOT

TESTDIR = os.path.dirname(__file__).replace("\\", "/")

def PrintSeps():
    print(f"\n{'#' * 30}\n")
