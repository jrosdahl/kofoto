import os
import gtk
import gobject
import gc
from kofoto.shelf import *
from kofoto.search import *
from mysortedmodel import *

from objectcollection import *
from environment import env

class SearchResult(ObjectCollection):

######################################################################
### Public functions and constants

    def __init__(self, query):
        ObjectCollection.__init__(self)
        self.loadQuery(query)
        self.__sortedTreeModel = MySortedModel(ObjectCollection.getModel(self))

    def loadQuery(self, query):
        parser = Parser(env.shelf)
        self._loadObjectList(env.shelf.search(parser.parse(query)))
            
    def isSortable(self):
        return gtk.TRUE

    def getModel(self):
        return self.__sortedTreeModel

######################################################################
### Private functions and datastructures
