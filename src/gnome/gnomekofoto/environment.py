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
from kofoto.imagecache import *

class Environment:
    def debug(self, msg):
        if self.isDebug:
            print msg

    def enter(self, method):
        if self.isDebug:
            print "-->", method

    def exit(self, method):
        if self.isDebug:
            print "<--", method
            
    def assertUnicode(self, obj):
        if not isinstance(obj, (unicode)):
            raise "Assertion failed! " + str(type(obj)) + " is not an unicode object: \"" + str(obj) + "\""
        
env = Environment()

env.codeset = locale.getpreferredencoding()
# TODO Make it possible for the user to specify configuration file on the command line.
conf = Config(DEFAULT_CONFIGFILE, env.codeset)
conf.read()
genconf = conf.getGeneralConfig()
env.imageCache = ImageCache(genconf["imagecache_location"])
env.thumbnailSize = conf.getcoordlist("gnome client", "thumbnail_size_limit")[0]
env.defaultTableViewColumns = re.findall(
    "\S+",
    conf.get("gnome client", "default_table_columns"))
env.defaultSortColumn = conf.get("gnome client", "default_sort_column")
env.openCommand = conf.get("gnome client", "open_command", True)
env.rotateRightCommand = conf.get("gnome client", "rotate_right_command", True)
env.rotateLeftCommand = conf.get("gnome client", "rotate_left_command", True)

dataDir = os.path.join(bindir, "..", "share", "gnomekofoto")
if not os.path.exists(dataDir):
    dataDir = bindir
env.iconDir = os.path.join(dataDir, "icons")
env.gladeFile = os.path.join(dataDir, "glade", "gkofoto.glade")
env.albumIconFileName = os.path.join(env.iconDir, "album.png")
env.albumIconPixbuf = gtk.gdk.pixbuf_new_from_file(env.albumIconFileName)
env.loadingPixbuf = env.albumIconPixbuf # TODO create another icon with a hour-glass or something
env.thumbnailErrorIconPixbuf = env.albumIconPixbuf # TODO create another icon
from clipboard import Clipboard
env.clipboard = Clipboard()

env.shelf = Shelf(genconf["shelf_location"], env.codeset)
env.shelf.begin()

env.isDebug=False # TODO get as a command line parameter


