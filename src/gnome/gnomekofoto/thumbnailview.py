import gtk
import sys

# from gnomekofoto.thumbnailcontextmenu import *
from gnomekofoto.objectcollectionview import *
from gnomekofoto.objectcollection import *
from environment import env

class ThumbnailView(ObjectCollectionView):

###############################################################################            
### Public
    
    def __init__(self, objectCollection):
        ObjectCollectionView.__init__(self,
                                      objectCollection,
                                      env.widgets["thumbnailList"],
                                      None) # TODO pass context menu
        self._viewWidget.connect("select_icon", self._widgetIconSelected)
        self._viewWidget.connect("unselect_icon", self._widgetIconUnselected)
        
    def setObjectCollection(self, objectCollection):
        self._clearAllConnections()
        self._objectCollection = objectCollection
        self._reloadAllFromModel()
        # TODO Improve. Avoid reloading all when not necessery?
        self._connect("row_inserted", self._reloadAllFromModel)
        self._connect("row_changed", self._reloadRowFromModel)
        self._connect("row_deleted", self._reloadAllFromModel)
        self._connect("rows_reordered", self._reloadAllFromModel)

    def show(self):
        env.widgets["thumbnailView"].show()
        self._viewWidget.grab_focus()
        self.setObjectCollection(self._objectCollection) # TODO Improve?
        self.__importSelection()
        self.__selectionLocked = gtk.FALSE
        for row in self._objectCollection.getModel():
            if row[ObjectCollection.COLUMN_OBJECT_ID] in self._objectCollection.getSelectedIds():
                self._viewWidget.moveto(row.path[0], 0.0)
                break

    def hide(self):
        self._clearAllConnections() # TODO Improve?
        self._viewWidget.clear()    # TODO Improve?
        self.__selectionLocked = gtk.TRUE
        env.widgets["thumbnailView"].hide()        


###############################################################################
### Callback functions registered by this class but invoked from other classes.
        
    def _reloadRowFromModel(self, model, path, iter):
        savedLockedState = self.__selectionLocked
        self.__selectionLocked = gtk.TRUE
        self._viewWidget.remove(path[0])
        self._loadThumbnail(model[path[0]])
        if path[0] in self._objectCollection.getSelectedIds():
            self._viewWidget.select_icon(path[0])
        self.__selectionLocked = savedLockedState
        
    def _widgetIconSelected(self, widget, index, event):
        if not self.__selectionLocked:
            row = self._objectCollection.getModel()[index]
            self._objectCollection.selectRow(row, gtk.TRUE)

    def _widgetIconUnselected(self, widget, index, event):
        if not self.__selectionLocked:
            row = self._objectCollection.getModel()[index]
            self._objectCollection.unSelectRow(row, gtk.TRUE)

    def _reloadAllFromModel(self, *garbage):
        self._viewWidget.clear()
        for row in self._objectCollection.getModel():
            self.__loadRow(row)
            
###############################################################################        
### Private

    __selectionLocked = gtk.FALSE
    __maxWidth = env.thumbnailSize

    def __importSelection(self):
        self._viewWidget.unselect_all()        
        for row in self._objectCollection.getSelectedRows():
            self._viewWidget.select_icon(row.path[0])

    def __loadRow(self, row):
        if row[ObjectCollection.COLUMN_IS_ALBUM]:
            text = row[ObjectCollection.COLUMN_ALBUM_TAG]
        else:
            # TODO Let configuration decide what to show...
            text = row[ObjectCollection.COLUMN_OBJECT_ID]
        pixbuf = row[ObjectCollection.COLUMN_THUMBNAIL]
        self._viewWidget.insert_pixbuf(row.path[0], pixbuf, "", str(text))
        self.__maxWidth = max(self.__maxWidth, pixbuf.get_width())
        self._viewWidget.set_icon_width(self.__maxWidth)
        
