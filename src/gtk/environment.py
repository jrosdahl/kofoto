import sys
import os
import getopt
import locale

# Find libraries if installed in ../lib (like in the source tree).
if os.path.islink(sys.argv[0]):
    link = os.readlink(sys.argv[0])
    absloc = os.path.normpath(
        os.path.join(os.path.dirname(sys.argv[0]), link))
    bindir = os.path.dirname(absloc)
else:
    bindir = os.path.dirname(sys.argv[0])
sys.path.insert(0, os.path.join(bindir, "..", "lib"))

from kofoto.common import *
from kofoto.shelf import *
from kofoto.config import *

locale.setlocale(locale.LC_ALL, "")
CODESET = locale.nl_langinfo(locale.CODESET)

conf = Config(DEFAULT_CONFIGFILE, CODESET)
conf.read()
genconf = conf.getGeneralConfig()

class Environment:
    pass
env = Environment()
env.imageCacheLocation = genconf["imagecache_location"]
env.imageSizes = genconf["image_sizes"]
env.baseDir = bindir
env.iconDir = bindir + "/icons/"
env.shelf = Shelf(genconf["shelf_location"], CODESET)
