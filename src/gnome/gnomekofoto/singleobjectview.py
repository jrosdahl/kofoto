import gtk
import sys
from environment import env
from gnomekofoto.imageview import *
from gnomekofoto.objectcollectionview import *

class SingleObjectView(ObjectCollectionView, ImageView):

###############################################################################            
### Public
    
    def __init__(self):
        env.debug("Init SingleObjectView")
        ImageView.__init__(self)
        ObjectCollectionView.__init__(self, env.widgets["objectView"])
        self._viewWidget.add(self)
        self.show_all()
        env.widgets["nextButton"].connect("clicked", self._goto, 1)
        env.widgets["previousButton"].connect("clicked", self._goto, -1)
        env.widgets["zoomToFit"].connect("clicked", self.fitToWindow)
        env.widgets["zoom100"].connect("clicked", self.zoom100)
        env.widgets["zoomIn"].connect("clicked", self.zoomIn)
        env.widgets["zoomOut"].connect("clicked", self.zoomOut)
        self.connect("button_press_event", self._mouse_button_pressed)
        self.__selectionLocked = False

    def show(self, objectCollection):
        env.enter("SingleObjectView.show()")
        ObjectCollectionView.show(self, objectCollection)
        env.widgets["objectView"].show()
        env.widgets["objectView"].grab_focus()
        env.widgets["zoom100"].set_sensitive(True)
        env.widgets["zoomToFit"].set_sensitive(True)
        env.widgets["zoomIn"].set_sensitive(True)
        env.widgets["zoomOut"].set_sensitive(True)
        env.exit("SingleObjectView.show()")

    def hide(self):
        env.enter("SingleObjectView.hide()")
        ObjectCollectionView.hide(self)
        env.widgets["objectView"].hide()
        env.widgets["previousButton"].set_sensitive(False)
        env.widgets["nextButton"].set_sensitive(False)
        env.widgets["zoom100"].set_sensitive(False)
        env.widgets["zoomToFit"].set_sensitive(False)
        env.widgets["zoomIn"].set_sensitive(False)
        env.widgets["zoomOut"].set_sensitive(False)
        env.exit("SingleObjectView.hide()")

    def freeze(self):
        self._clearAllConnections()
        self.clear()
        self.__selectionLocked = True
        
    def thaw(self):
        env.enter("SingleObjectView.thaw()")
        model = self._objectCollection.getModel()
        # The row_changed event is needed when the location attribute of the image object is changed.
        self._connect(model, "row_changed", self._rowChanged)
        # The following events are needed to update the previous and next navigation buttons.
        self._connect(model, "rows_reordered", self._modelUpdated)
        self._connect(model, "row_inserted", self._modelUpdated)
        self._connect(model, "row_deleted", self._modelUpdated)
        self.__selectionLocked = False
        self.importSelection(self._objectCollection.getObjectSelection())
        env.exit("SingleObjectView.thaw()")
        
    def importSelection(self, objectSelection):
        if not self.__selectionLocked:
            env.debug("SingleImageView is importing selection")
            self.__selectionLocked = True
            model = self._objectCollection.getModel()
            if len(model) == 0:
                # Model is empty. No rows can be selected.
                self.__selectedRowNr = -1
                self.clear()
            else:
                if len(objectSelection) == 0:
                    # No objects is selected -> select first object
                    self.__selectedRowNr = 0                    
                    selectedRow = model[self.__selectedRowNr]
                    selectedObjectId = selectedRow[ObjectCollection.COLUMN_OBJECT_ID]
                    objectSelection.setSelection([selectedObjectId])
                else:
                    # There are one or more selected objects
                    for row in model:
                        objectId = row[ObjectCollection.COLUMN_OBJECT_ID]
                        if objectId in objectSelection:
                            self.__selectedRowNr = row.path[0]
                            selectedObjectId = objectId
                            if len(objectSelection) > 1:
                                # We don't want more then one selected object.
                                objectSelection.setSelection([selectedObjectId])
                selectedObject = objectSelection[selectedObjectId]
                if selectedObject.isAlbum():
                    self.loadFile(env.albumIconFileName, False)
                else:
                    self.loadFile(selectedObject.getLocation(), False)
            if self.__selectedRowNr <= 0:
                env.widgets["previousButton"].set_sensitive(False)
            else: 
                env.widgets["previousButton"].set_sensitive(True)
            if (self.__selectedRowNr == -1 or self.__selectedRowNr >= len(model) - 1):
                env.widgets["nextButton"].set_sensitive(False)
            else:
                env.widgets["nextButton"].set_sensitive(True)
            self.__selectionLocked = False
        
    def _connectObjectCollection(self, objectCollection):
        env.enter("Connecting SingleObjectView to object collection")
        ObjectCollectionView._connectObjectCollection(self, objectCollection)
        self.thaw()
        env.exit("Connecting SingleObjectView to object collection")

    def _disconnectObjectCollection(self):
        env.enter("Disconnecting SingleObjectView from object collection")
        ObjectCollectionView._disconnectObjectCollection(self)
        self.freeze()
        env.exit("Disconnecting SingleObjectView from object collection")

    def _modelUpdated(self, *foo):
        env.debug("SingleObjectView is handling model update")
        self.importSelection(self._objectCollection.getObjectSelection())        

    def _rowChanged(self, model, path, iter):
        if path[0] == self.__selectedRowNr:
            env.debug("selected object in SingleObjectView changed")
            objectId = model[path][ObjectCollection.COLUMN_OBJECT_ID]
            objectSelection = self._objectCollection.getObjectSelection()
            object = objectSelection[objectId]
            self.loadFile(selectedObject.getLocation(), False)
        
    def _goto(self, button, direction):
        model = self._objectCollection.getModel()
        objectSelection = self._objectCollection.getObjectSelection()
        selectedObjectId = model[self.__selectedRowNr + direction][ObjectCollection.COLUMN_OBJECT_ID]
        objectSelection.setSelection([selectedObjectId])


