import sys
import os
import gtk
import getopt
import locale
import re

from kofoto.clientenvironment import *
from kofoto.common import *
from kofoto.shelf import *
from kofoto.config import *
from kofoto.imagecache import *

class Environment(ClientEnvironment):
    def __init__(self):
        ClientEnvironment.__init__(self)
        self.startupNotices = []

    def setup(self, bindir):
        try:
            ClientEnvironment.setup(self)
        except ClientEnvironmentError, e:
            self.startupNotices += [e[0]]
            return False

        # TODO: Make it possible for the user to specify configuration file on the command line.
        self.thumbnailSize = self.config.getcoordlist(
            "gkofoto", "thumbnail_size_limit")[0]
        self.defaultTableViewColumns = re.findall(
            "\S+",
            self.config.get("gkofoto", "default_table_columns"))
        self.defaultSortColumn = self.config.get(
            "gkofoto", "default_sort_column")
        self.openCommand = self.config.get(
            "gkofoto", "open_command", True)
        self.rotateRightCommand = self.config.get(
            "gkofoto", "rotate_right_command", True)
        self.rotateLeftCommand = self.config.get(
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

        self.isDebug = False # TODO get as a command line parameter
        return True

    def _writeInfo(self, infoString):
        self.startupNotices += [infoString]

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
