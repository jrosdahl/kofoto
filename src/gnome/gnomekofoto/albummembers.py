from objectcollection import *
from environment import env

class AlbumMembers(ObjectCollection):

######################################################################
### Public functions and constants

    def __init__(self):
        env.debug("Init AlbumMembers")
        ObjectCollection.__init__(self)        
        self.__album = None

    def loadAlbum(self, album):
        env.debug("Loading album: " + album.getTag())
        self.__album = album
        self._loadObjectList(album.getChildren())
        
    def isReorderable(self):
        return True

    def isMutable(self):
        return True

    def getContainer(self):
        return self.__album
    
######################################################################
### Private functions

    
