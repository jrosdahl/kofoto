import sys
import os
import gtk
import getopt
import locale
import re

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

class Environment:
    pass

env = Environment()
locale.setlocale(locale.LC_ALL, "")
env.codeset = locale.nl_langinfo(locale.CODESET)
conf = Config(DEFAULT_CONFIGFILE, env.codeset)
conf.read()
genconf = conf.getGeneralConfig()

dataDir = os.path.join(bindir, "..", "share", "gnomekofoto")
if not os.path.exists(dataDir):
    dataDir = bindir

env.imageCacheLocation = genconf["imagecache_location"]
env.thumbnailSize = conf.getcoordlist("gnome client", "thumbnail_size_limit")[0]
env.defaultTableViewColumns = re.findall(
    "\w+",
    conf.get("gnome client", "default_table_columns"))
env.defaultSortColumn = conf.get("gnome client", "default_sort_column")
env.iconDir = os.path.join(dataDir, "icons")
env.gladeFile = os.path.join(dataDir, "glade", "gkofoto.glade")
env.shelf = Shelf(genconf["shelf_location"], env.codeset)
env.albumIconFileName = os.path.join(env.iconDir, "album.png")
env.albumIconPixbuf = gtk.gdk.pixbuf_new_from_file(env.albumIconFileName)
