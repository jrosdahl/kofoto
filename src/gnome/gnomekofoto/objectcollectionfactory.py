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

    def getObjectCollection(self, url):
        env.debug("Object collection factory loading URL: " + url);
        self.__clear()
        l = string.split(url, u"://", 1)
        if l[0] == u"query":
            self.__searchResult.loadQuery(l[1])
            return self.__searchResult
        elif l[0] == u"album":
            self.__albumMembers.loadAlbum(env.shelf.getAlbum(l[1]))
            return self.__albumMembers
        else:
            raise "Unkown protocol" # TODO

######################################################################
### Private functions
    
    def __clear(self):
        self.__searchResult.clear()
        self.__albumMembers.clear()
