# pylint: disable-msg=W0222

import sys
import os
import re

import pygtk
try:
    pygtk.require("2.0")
except AssertionError:
    # pygtk.require("2.0") fails in the py2exe installer. Don't know why.
    pass
import gtk
import gtk.gdk
import gtk.glade
from kofoto.gkofoto import crashdialog
sys.excepthook = crashdialog.show

from kofoto.clientenvironment import ClientEnvironment, ClientEnvironmentError

class WidgetsWrapper:
    def __init__(self):
        self.widgets = gtk.glade.XML(env.gladeFile, "mainWindow")

    def __getitem__(self, key):
        return self.widgets.get_widget(key)

class Environment(ClientEnvironment):
    def __init__(self):
        ClientEnvironment.__init__(self)
        self.startupNotices = []
        self.openCommand = None
        self.loadingPixbuf = None
        self.gladeFile = None
        self.unknownImageIconFileName = None
        self.albumIconFileName = None
        self.thumbnailSize = None
        self.albumIconPixbuf = None
        self.unknownImageIconPixbuf = None
        self.defaultSortColumn = None
        self.isDebug = None
        self.clipboard = None
        self.defaultTableViewColumns = None
        self.iconDir = None
        self.widgets = None
        self.rotateRightCommand = None
        self.rotateLeftCommand = None

    def setup(self, bindir, isDebug=False, configFileLocation=None,
              shelfLocation=None):
        try:
            ClientEnvironment.setup(self, configFileLocation, shelfLocation)
        except ClientEnvironmentError, e:
            self.startupNotices += [e[0]]
            return False

        self.isDebug = isDebug
        self.thumbnailSize = self.config.getcoordlist(
            "gkofoto", "thumbnail_size_limit")[0]
        self.defaultTableViewColumns = re.findall(
            "\S+",
            self.config.get("gkofoto", "default_table_columns"))
        if not "versions" in self.defaultTableViewColumns:
            # Ugly, temporary hack:
            self.defaultTableViewColumns.insert(1, "versions")
        self.defaultSortColumn = self.config.get(
            "gkofoto", "default_sort_column")
        self.openCommand = self.config.get(
            "gkofoto", "open_command", True)
        self.rotateRightCommand = self.config.get(
            "gkofoto", "rotate_right_command", True)
        self.rotateLeftCommand = self.config.get(
            "gkofoto", "rotate_left_command", True)

        # Case 1: Running from normal UNIX or Windows non-py2exe installation.
        dataDir = os.path.join(bindir, "..", "share", "gkofoto")
        if not os.path.isdir(dataDir):
            # Case 2: Running from Windows py2exe installation.
            dataDir = os.path.join(bindir, "share", "gkofoto")
            if not os.path.isdir(dataDir):
                # Case 3: Running from source code.
                dataDir = bindir
        self.iconDir = os.path.join(dataDir, "icons")
        self.gladeFile = os.path.join(dataDir, "glade", "gkofoto.glade")
        self.albumIconFileName = os.path.join(self.iconDir, "album.png")
        self.albumIconPixbuf = gtk.gdk.pixbuf_new_from_file(self.albumIconFileName)
        self.loadingPixbuf = self.albumIconPixbuf # TODO: create another icon with a hour-glass or something
        self.unknownImageIconFileName = os.path.join(self.iconDir, "unknownimage.png")
        self.unknownImageIconPixbuf = gtk.gdk.pixbuf_new_from_file(self.unknownImageIconFileName)
        from kofoto.gkofoto.clipboard import Clipboard
        self.clipboard = Clipboard()

        self.widgets = WidgetsWrapper()

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
