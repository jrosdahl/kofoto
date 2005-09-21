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
        return self.__album and self.__album.isMutable()

    def isMutable(self):
        return (self.__album and
                self.__album.isMutable() and
                not self.isLoading())

    def getContainer(self):
        return self.__album

    def cut(self, *foo):
        self.copy()
        self.delete()

    def paste(self, *foo):
        # This method assumes that self.getModel() returns an unsorted
        # and mutable model.
        self._freezeViews()
        locations = list(self.getObjectSelection())
        newObjects = list(env.clipboard)
        albumCopied = False
        for obj in newObjects:
            if obj.isAlbum():
                albumCopied = True
                break
        currentChildren = list(self.__album.getChildren())
        if len(locations) > 0:
            locations.sort()
            insertLocation = locations[0]
        else:
            # Insert last.
            insertLocation = len(currentChildren)
        self.__album.setChildren(currentChildren[:insertLocation] +
                                 newObjects +
                                 currentChildren[insertLocation:])
        self._insertObjectList(newObjects, insertLocation)
        if albumCopied:
            # TODO: Don't reload the whole tree.
            env.mainwindow.reloadAlbumTree()
        self.getObjectSelection().unselectAll()
        self._thawViews()

    def delete(self, *foo):
        # This method assumes that self.getModel() returns an unsorted
        # and mutable model
        model = self.getModel()
        self._freezeViews()
        albumMembers = list(self.__album.getChildren())
        locations = list(self.getObjectSelection())
        locations.sort()
        locations.reverse()
        albumDeleted = False
        for loc in locations:
            if albumMembers[loc].isAlbum():
                albumDeleted = True
            albumMembers.pop(loc)
            del model[loc]
        self.__album.setChildren(albumMembers)
        self.getObjectSelection().unselectAll()
        if albumDeleted:
            # TODO: Don't reload the whole tree.
            env.mainwindow.reloadAlbumTree()
        self._thawViews()

######################################################################
### Private functions
