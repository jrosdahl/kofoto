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
        ObjectCollectionView.setObjectCollection(self, objectCollection)
        if not self.__hidden:
            self._connect("row_inserted",   self._reloadAllFromModel)
            self._connect("row_deleted",    self._reloadAllFromModel)
            self._connect("rows_reordered", self._reloadAllFromModel)
            self._connect("row_changed",    self._reloadRowFromModel)
            self._reloadAllFromModel()

    def show(self):
        self.__hidden = gtk.FALSE
        env.widgets["thumbnailView"].show()
        self._viewWidget.grab_focus()
        self.setObjectCollection(self._objectCollection)
        self.__importSelection()
        self.__selectionLocked = gtk.FALSE
        numberOfIcons = self._viewWidget.get_num_icons()
        if numberOfIcons > 1:
            # First check that the widget contains icons because I don't know
            # how icon_is_visible() is handled if the view is empty.
            if self._viewWidget.icon_is_visible(0) == gtk.VISIBILITY_FULL and self._viewWidget.icon_is_visible(numberOfIcons - 1) == gtk.VISIBILITY_FULL:
                # All icons already visible. No need to scroll widget.
                pass
            else:
                # Scroll widget to first selected icon
                for row in self._objectCollection.getModel():
                    if row[ObjectCollection.COLUMN_OBJECT_ID] in self._objectCollection.getSelectedIds():
                        self._viewWidget.moveto(row.path[0], 0.4)
                        break

    def hide(self):
        self.__hidden = gtk.TRUE
        self._clearAllConnections()
        self._viewWidget.clear()
        self.__selectionLocked = gtk.TRUE
        env.widgets["thumbnailView"].hide()        


###############################################################################
### Callback functions registered by this class but invoked from other classes.
        
    def _reloadRowFromModel(self, model, path, *foo):
        savedLockedState = self.__selectionLocked
        self.__selectionLocked = gtk.TRUE
        self._viewWidget.remove(path[0])
        self.__loadRow(model[path[0]])
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
    __maxWidth = env.thumbnailSize[0]
    __hidden = gtk.TRUE

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
        
