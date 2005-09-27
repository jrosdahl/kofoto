from kofoto.search import Parser
from kofoto.gkofoto.sortableobjectcollection import SortableObjectCollection
from kofoto.gkofoto.environment import env

class SearchResult(SortableObjectCollection):

######################################################################
### Public functions and constants

    def __init__(self):
        SortableObjectCollection.__init__(self)

    def isMutable(self):
        return False

    def loadQuery(self, query):
        parser = Parser(env.shelf)
        self._loadObjectList(env.shelf.search(parser.parse(query)))

######################################################################
### Private functions and datastructures
