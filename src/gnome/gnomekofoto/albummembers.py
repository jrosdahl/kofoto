import os
import gtk
import gobject
import gc
from kofoto.shelf import *

from objectcollection import *
from environment import env

class AlbumMembers(ObjectCollection):

######################################################################
### Public functions and constants

    def __init__(self, album=env.shelf.getRootAlbum()):
        ObjectCollection.__init__(self)
        self.loadAlbum(album)

    def loadAlbum(self, album=env.shelf.getRootAlbum()):
        self._loadObjectList(album.getChildren())
        self.unselectAll()
        
    def isReorderable(self):
        return gtk.FALSE
        # TODO Change to true when required methods has been implemented.

    def isMutable(self):
        return gtk.FALSE
        # TODO Change to true when required methods has been implemented.


######################################################################
### Private functions and datastructures
