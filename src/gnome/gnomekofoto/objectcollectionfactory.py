import string
import gtk
import gtk.gdk

from searchresult import *
from albummembers import *
from environment import env
from kofoto.search import *
from kofoto.shelf import *

class ObjectCollectionFactory:
    def __init__(self):
        pass

    def getObjectCollection(self, url):
        l = string.split(url, u"://", 1)
        if l[0] == u"query":
            return SearchResult(l[1])
        elif l[0] == u"album":
            return AlbumMembers(env.shelf.getAlbum(l[1]))
        else:
            raise "Unkown protocol" # TODO

    def getDefaultObjectCollection(self):
        return AlbumMembers()
