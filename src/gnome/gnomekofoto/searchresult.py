from kofoto.shelf import *
from kofoto.search import *
from sortableobjectcollection import *
from environment import env

class SearchResult(SortableObjectCollection):

######################################################################
### Public functions and constants

    def __init__(self):
        SortableObjectCollection.__init__(self)

    def loadQuery(self, query):
        parser = Parser(env.shelf)
        self._loadObjectList(env.shelf.search(parser.parse(query)))

######################################################################
### Private functions and datastructures

