import sys
import os
import gtk
import getopt
import locale
import re

from kofoto.common import *
from kofoto.shelf import *
from kofoto.config import *
from kofoto.imagecache import *

class Environment:
    def init(self, bindir):
        self.codeset = locale.getpreferredencoding()
        # TODO: Make it possible for the user to specify configuration file on the command line.
        conf = Config(DEFAULT_CONFIGFILE, self.codeset)
        conf.read()
        genconf = conf.getGeneralConfig()
        self.imageCache = ImageCache(genconf["imagecache_location"])
        self.thumbnailSize = conf.getcoordlist(
            "gkofoto", "thumbnail_size_limit")[0]
        self.defaultTableViewColumns = re.findall(
            "\S+",
            conf.get("gkofoto", "default_table_columns"))
        self.defaultSortColumn = conf.get(
            "gkofoto", "default_sort_column")
        self.openCommand = conf.get(
            "gkofoto", "open_command", True)
        self.rotateRightCommand = conf.get(
            "gkofoto", "rotate_right_command", True)
        self.rotateLeftCommand = conf.get(
            "gkofoto", "rotate_left_command", True)

        dataDir = os.path.join(bindir, "..", "share", "gkofoto")
        if not os.path.exists(dataDir):
            dataDir = bindir
        self.iconDir = os.path.join(dataDir, "icons")
        self.gladeFile = os.path.join(dataDir, "glade", "gkofoto.glade")
        self.albumIconFileName = os.path.join(self.iconDir, "album.png")
        self.albumIconPixbuf = gtk.gdk.pixbuf_new_from_file(self.albumIconFileName)
        self.loadingPixbuf = self.albumIconPixbuf # TODO: create another icon with a hour-glass or something
        self.unknownImageIconFileName = os.path.join(self.iconDir, "unknownimage.png")
        self.unknownImageIconPixbuf = gtk.gdk.pixbuf_new_from_file(self.unknownImageIconFileName)
        from clipboard import Clipboard
        self.clipboard = Clipboard()

        self.shelf = Shelf(genconf["shelf_location"], self.codeset)

        self.isDebug=False # TODO get as a command line parameter

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
        assert isinstance(obj, unicode), \
               "%s is not a unicode object: \"%s\"" % (type(obj), obj)

env = Environment()
