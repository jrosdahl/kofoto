import string
from searchresult import *
from albummembers import *
from environment import env
from kofoto.search import *
from kofoto.shelf import *

class ObjectCollectionFactory:

######################################################################
### Public functions and constants

    def __init__(self):
        env.debug("Init ObjectCollectionFactory")
        self.__searchResult = SearchResult()
        self.__albumMembers = AlbumMembers()

    def getObjectCollection(self, query):
        env.debug("Object collection factory loading query: " + query);
        self.__clear()
        if query and query[0] == "/":
            try:
                verifyValidAlbumTag(query[1:])
                self.__albumMembers.loadAlbum(env.shelf.getAlbum(query[1:]))
                return self.__albumMembers
            except BadAlbumTagError:
                pass
        self.__searchResult.loadQuery(query)
        return self.__searchResult

######################################################################
### Private functions

    def __clear(self):
        self.__searchResult.clear()
        self.__albumMembers.clear()
