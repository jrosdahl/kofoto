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
        validAlbumTag = False
        if query and query[0] == "/":
            try:
                verifyValidAlbumTag(query[1:])
                validAlbumTag = True
            except BadAlbumTagError:
                pass
        try:
            if validAlbumTag:
                self.__albumMembers.loadAlbum(env.shelf.getAlbum(query[1:]))
                return self.__albumMembers
            else:
                self.__searchResult.loadQuery(query)
                return self.__searchResult
        except AlbumDoesNotExistError, tag:
            errorText = "No such album tag: \"%s\"." % tag
        except CategoryDoesNotExistError, tag:
            errorText = "No such category tag: \"%s\"." % tag
        except BadTokenError, pos:
            errorText = "Error parsing query: bad token starting at position %s: \"%s\"." % (
                pos,
                query[pos[0]:])
        except UnterminatedStringError, e:
            errorText = "Error parsing query: unterminated string starting at position %s: \"%s\"." % (
                e.args[0],
                query[e.args[0]:])
        except ParseError, text:
            errorText = "Error parsing query: %s." % text
        dialog = gtk.MessageDialog(
            type=gtk.MESSAGE_ERROR,
            buttons=gtk.BUTTONS_OK,
            message_format=errorText)
        dialog.run()
        dialog.destroy()
        self.__searchResult = SearchResult()
        return self.__searchResult


######################################################################
### Private functions

    def __clear(self):
        self.__searchResult.clear()
        self.__albumMembers.clear()
