import sys
import os
import getopt

# Find libraries if installed in ../lib (like in the source tree).
if os.path.islink(sys.argv[0]):
    link = os.readlink(sys.argv[0])
    absloc = os.path.normpath(
        os.path.join(os.path.dirname(sys.argv[0]), link))
    bindir = os.path.dirname(absloc)
else:
    bindir = os.path.dirname(sys.argv[0])
sys.path.insert(0, os.path.join(bindir, "..", "lib"))

class Environment:
    imageCacheLocation = os.path.expanduser("~/.kofoto/imagecache") # TODO: Read from configuration file
    iconDir = bindir + "/icons/"
    largestThumbnailSize = 400 # TODO: Read from configuration file

from kofoto.common import *
from kofoto.shelf import *
   
env = Environment()
env.baseDir = bindir
env.iconDir = bindir + "/icons/"
env.shelf = Shelf(os.path.expanduser("~/.kofoto/shelf")) # TODO: Read from configuration file
