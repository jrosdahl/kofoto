import gtk
from gnomekofoto.objectcollectionview import *
from gnomekofoto.objectcollection import *
from environment import env

class ThumbnailView(ObjectCollectionView):

###############################################################################            
### Public
    
    def __init__(self):
        env.debug("Init ThumbnailView")        
        ObjectCollectionView.__init__(self,
                                      env.widgets["thumbnailList"])
        self.__currentMaxWidth = env.thumbnailSize[0]
        self.__selectionLocked = False
        self._viewWidget.connect("select_icon", self._widgetIconSelected)
        self._viewWidget.connect("unselect_icon", self._widgetIconUnselected)

    def show(self, objectCollection):
        env.enter("ThumbnailView.show()")
        ObjectCollectionView.show(self, objectCollection)
        env.widgets["thumbnailView"].show()
        self._viewWidget.grab_focus()
        self.__scrollToFirstSelectedObject()
        env.exit("ThumbnailView.show()")            
        
    def hide(self):
        env.enter("ThumbnailView.hide()")
        ObjectCollectionView.hide(self)
        env.widgets["thumbnailView"].hide()
        env.exit("ThumbnailView.hide()")

    def freeze(self):
        self._clearAllConnections()
        self._viewWidget.clear()

    def thaw(self):
        env.enter("ThumbnailView.thaw()")
        model = self._objectCollection.getModel()
        for row in model:
            self.__loadRow(row)
        self._connect(model, "row_inserted",   self._rowInserted)
        self._connect(model, "row_deleted",    self._rowDeleted)
        self._connect(model, "rows_reordered", self._rowsReordered)
        self._connect(model, "row_changed",    self._rowChanged)
        self.importSelection(self._objectCollection.getObjectSelection())
        env.exit("ThumbnailView.thaw()")        

    def importSelection(self, objectSelection):
        if not self.__selectionLocked:        
            env.debug("TableView is importing selection")
            self.__selectionLocked = True            
            self._viewWidget.unselect_all()        
            for row in self._objectCollection.getModel():
                if row[ObjectCollection.COLUMN_OBJECT_ID] in objectSelection:
                    self._viewWidget.select_icon(row.path[0])
            self.__selectionLocked = False
        
    def _connectObjectCollection(self, objectCollection):
        env.enter("Connecting ThumbnailView to object collection")
        ObjectCollectionView._connectObjectCollection(self, objectCollection)
        self.thaw()
        env.exit("Connecting ThumbnailView to object collection")

    def _disconnectObjectCollection(self):
        env.enter("Disconnecting ThumbnailView from object collection")
        ObjectCollectionView._disconnectObjectCollection(self)
        self.freeze()
        env.exit("Disconnecting ThumbnailView from object collection")
        
###############################################################################
### Callback functions registered by this class but invoked from other classes.

    def _rowChanged(self, model, path, iter):
        env.debug("ThumbnailView row changed.")
        self._viewWidget.remove(path[0])
        self.__loadRow(model[path])
        if path[0] in self._objectCollection.getObjectSelection().getSelectedIds():
            self._viewWidget.select_icon(path[0])
            
    def _rowInserted(self, model, path, iter):
        env.debug("ThumbnailView row inserted.")
        self.__loadRow(model[path])

    def _rowsReordered(self, model, b, c, d):
        env.debug("ThumbnailView rows reordered.")
        print "rowReordered", model, b, c, d
        # TODO I Don't know how to parse which rows that has
        #      been reordered. Hence I must reload all rows.
        self._viewWidget.clear()        
        for row in self._objectCollection.getModel():
            self.__loadRow(row)
        self.importSelection(self._objectCollection.getObjectSelection())

    def _rowDeleted(self, model, path):
        env.debug("ThumbnailView row deleted.")
        self._viewWidget.remove(path[0])
        
    def _widgetIconSelected(self, widget, index, event):
        if not self.__selectionLocked:
            env.enter("ThumbnailView selection changed")
            self.__selectionLocked = True
            objectId = self._objectCollection.getModel()[index][ObjectCollection.COLUMN_OBJECT_ID]
            self._objectCollection.getObjectSelection().addSelection(objectId)
            self.__selectionLocked = False

    def _widgetIconUnselected(self, widget, index, event):
        if not self.__selectionLocked:
            env.enter("ThumbnailView selection changed")
            self.__selectionLocked = True
            objectId = self._objectCollection.getModel()[index][ObjectCollection.COLUMN_OBJECT_ID]
            self._objectCollection.getObjectSelection().removeSelection(objectId)
            self.__selectionLocked = False
    
###############################################################################        
### Private

    def __loadRow(self, row):
        if row[ObjectCollection.COLUMN_IS_ALBUM]:
            text = row[ObjectCollection.COLUMN_ALBUM_TAG]
        else:
            # TODO Let configuration decide what to show...
            text = row[ObjectCollection.COLUMN_OBJECT_ID]
        pixbuf = row[ObjectCollection.COLUMN_THUMBNAIL]
        if pixbuf == None:
            # It is possible that we get the row inserted event before
            # the thumbnail is loaded. The temporary icon will be removed
            # when we receive the row changed event.
            pixbuf = env.loadingPixbuf
        self._viewWidget.insert_pixbuf(row.path[0], pixbuf, "", str(text))
        self.__currentMaxWidth = max(self.__currentMaxWidth, pixbuf.get_width())
        self._viewWidget.set_icon_width(self.__currentMaxWidth)

    def __scrollToFirstSelectedObject(self):
        numberOfIcons = self._viewWidget.get_num_icons()
        if numberOfIcons > 1:
            # First check that the widget contains icons because I don't know
            # how icon_is_visible() is handled if the view is empty.
            if (self._viewWidget.icon_is_visible(0) == gtk.VISIBILITY_FULL
                and self._viewWidget.icon_is_visible(numberOfIcons - 1) == gtk.VISIBILITY_FULL):
                # All icons already visible. No need to scroll widget.
                pass
            else:
                # Scroll widget to first selected icon
                selectedObjects = self._objectCollection.getObjectSelection()
                for row in self._objectCollection.getModel():
                    if row[ObjectCollection.COLUMN_OBJECT_ID] in selectedObjects:
                        self._viewWidget.moveto(row.path[0], 0.4)
                        break
