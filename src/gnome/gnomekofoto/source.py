import string
import gtk
import gtk.gdk

from environment import env
from kofoto.search import *
from kofoto.shelf import *

class Source:
    def __init__(self):
        self._hasChanged = gtk.FALSE
        # Using "focus-out-event" as a workaround, since there is no
        # "editing_done" signal
        env.widgets["sourceEntry"].connect("focus-out-event", self._updated)
        env.widgets["sourceEntry"].connect("changed", self._changed)
        
    def _changed(self, *foo):
        self._hasChanged = gtk.TRUE
        
    def _updated(self, widget=None, *foo):
        if not self._hasChanged:
            return
        if widget is None:
            widget = env.widgets["sourceEntry"]
        source = widget.get_text()
        l = string.split(source, u"://", 1)
        objectList = []
        if l[0] == u"query":
            parser = Parser(env.shelf)
            try:
                for child in env.shelf.search(parser.parse(l[1])):
                    objectList.append(child)
            except CategoryDoesNotExistError:
                print "Unkown categories:", l[1]
                objectList = []
            except ParseError:
                print "Invalid query:", l[1]
                objectList = []
        elif l[0] == u"album":
            try:
                album = env.shelf.getAlbum(l[1])
                for child in album.getChildren():
                    objectList.append(child)
            except AlbumDoesNotExistError:
                print "Unknown album:", l[1]
        else:
            print "Unknown protocol"
        env.controller.loadObjects(objectList)
        self._hasChanged = gtk.FALSE
                
    def set(self, source):
        env.widgets["sourceEntry"].set_text(source)        
        self._updated()
