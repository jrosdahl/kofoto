import gtk
from environment import env
from mysortedmodel import *
from objectcollection import *

def attributeSortFunc(model, iterA, iterB, column):
    valueA = model.get_value(iterA, column)
    valueB = model.get_value(iterB, column)
    try:
        result = cmp(float(valueA), float(valueB))
    except (ValueError, TypeError):
        result = cmp(valueA, valueB)
    if result == 0:
        result = cmp(model.get_value(iterA, ObjectCollection.COLUMN_OBJECT_ID),
                     model.get_value(iterB, ObjectCollection.COLUMN_OBJECT_ID))
    return result

class SortableObjectCollection(ObjectCollection):

######################################################################
### Public

    def __init__(self):
        ObjectCollection.__init__(self)
        self.__sortOrder = None
        self.__sortColumnName = None
        self.__sortedTreeModel = MySortedModel(self.getUnsortedModel())
        self.setSortOrder(order=gtk.SORT_ASCENDING)
        self.setSortColumnName(columnName=env.defaultSortColumn)

    def isSortable(self):
        return True

    def isReorderable(self):
        return False    
    
    def getModel(self):
        return self.__sortedTreeModel

    def getUnsortedModel(self):
        return ObjectCollection.getModel(self)

    def convertToUnsortedRowNr(self, rowNr):
        return self.__sortedTreeModel.convert_path_to_child_path(rowNr)[0]
    
    def convertFromUnsortedRowNr(self, unsortedRowNr):
        return self.__sortedTreeModel. convert_child_path_to_path(unsortedRowNr)[0]

    def getSortOrder(self):
        return self.__sortOrder

    def getSortColumnName(self):
        return self.__sortColumnName
    
    def setSortOrder(self, widget=None, order=None):
        if widget != None and not widget.get_active():
            # ignore the callback when the radio menu item is unselected
            return        
        if self.__sortOrder != order:
            env.debug("Setting sort order to: " + str(order))
            self.__sortOrder = order
            self.__configureSortedModel(self.__sortColumnName, self.__sortOrder)
            self.__emitSortOrderChanged()
            
    def setSortColumnName(self, widget=None, columnName=None):
        if widget != None and not widget.get_active():
            # ignore the callback when the radio menu item is unselected
            return
        if self.__sortColumnName != columnName:
            env.debug("Setting sort column to: " + columnName)
            self.__sortColumnName = columnName
            self.__configureSortedModel(self.__sortColumnName, self.__sortOrder)
            self.__emitSortColumnChanged()

    def registerView(self, view):
        ObjectCollection.registerView(self, view)
        self.__emitSortOrderChanged()
        self.__emitSortColumnChanged()

    def __emitSortOrderChanged(self):
        for view in self._getRegisteredViews():
            view.sortOrderChanged(self.__sortOrder)
                
    def __emitSortColumnChanged(self):
        for view in self._getRegisteredViews():
            view.sortColumnChanged(self.__sortColumnName)        
            
    def __configureSortedModel(self, sortColumnName, sortOrder):
        if (sortOrder != None and sortColumnName != None):
            sortColumnNr = self.getObjectMetadataMap()[sortColumnName][self.COLUMN_NR]
            model = self.getModel()
            model.set_sort_column_id(sortColumnNr, self.__sortOrder)
            # It is important that the attributeSortFunc is not an class member method,
            # otherwise we are leaking memmory.
            model.set_sort_func(sortColumnNr,
                                attributeSortFunc,
                                sortColumnNr)
