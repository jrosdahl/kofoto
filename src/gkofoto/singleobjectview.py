import gtk
import sys
from environment import env
from gkofoto.imageview import *
from gkofoto.objectcollectionview import *

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
        env.widgets["menubarNextImage"].connect("activate", self._goto, 1)
        env.widgets["previousButton"].connect("clicked", self._goto, -1)
        env.widgets["menubarPreviousImage"].connect("activate", self._goto, -1)
        env.widgets["zoomToFit"].connect("clicked", self.fitToWindow)
        env.widgets["menubarZoomToFit"].connect("activate", self.fitToWindow)
        env.widgets["zoom100"].connect("clicked", self.zoom100)
        env.widgets["menubarActualSize"].connect("activate", self.zoom100)
        env.widgets["zoomIn"].connect("clicked", self.zoomIn)
        env.widgets["menubarZoomIn"].connect("activate", self.zoomIn)
        env.widgets["zoomOut"].connect("clicked", self.zoomOut)
        env.widgets["menubarZoomOut"].connect("activate", self.zoomOut)
        self.connect("button_press_event", self._mouse_button_pressed)
        self.__selectionLocked = False

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
                    objectSelection.setSelection([self.__selectedRowNr])
                elif len(objectSelection) > 1:
                    # More than one object selected -> select first object
                    self.__selectedRowNr = objectSelection.getLowestSelectedRowNr()
                    objectSelection.setSelection([self.__selectedRowNr])
                else:
                    # Exactly one object selected
                    self.__selectedRowNr = objectSelection.getLowestSelectedRowNr()
                selectedObject = objectSelection[self.__selectedRowNr]
                if selectedObject.isAlbum():
                    self.loadFile(env.albumIconFileName, False)
                else:
                    self.loadFile(selectedObject.getLocation(), False)
            enablePreviousButton = (self.__selectedRowNr > 0)
            env.widgets["previousButton"].set_sensitive(enablePreviousButton)
            env.widgets["menubarPreviousImage"].set_sensitive(enablePreviousButton)
            enableNextButton = (self.__selectedRowNr != -1 and
                                self.__selectedRowNr < len(model) - 1)
            env.widgets["nextButton"].set_sensitive(enableNextButton)
            env.widgets["menubarNextImage"].set_sensitive(enableNextButton)
            self.__selectionLocked = False
        self._updateContextMenu()

        # Override sensitiveness set in _updateContextMenu.
        for widgetName in [
                "menubarCut",
                "menubarCopy",
                "menubarDelete",
                "menubarDestroy",
                "menubarProperties",
                "menubarCreateAlbumChild",
                "menubarRegisterAndAddImages",
                "menubarGenerateHtml",
                ]:
            env.widgets[widgetName].set_sensitive(False)

    def _showHelper(self):
        env.enter("SingleObjectView.showHelper()")
        env.widgets["objectView"].show()
        env.widgets["objectView"].grab_focus()
        for widgetName in [
                "zoom100",
                "zoomToFit",
                "zoomIn",
                "zoomOut",
                "menubarZoom",
                ]:
            env.widgets[widgetName].set_sensitive(True)
        env.exit("SingleObjectView.showHelper()")

    def _hideHelper(self):
        env.enter("SingleObjectView.hideHelper()")
        env.widgets["objectView"].hide()
        for widgetName in [
                "previousButton",
                "nextButton",
                "menubarPreviousImage",
                "menubarNextImage",
                "zoom100",
                "zoomToFit",
                "zoomIn",
                "zoomOut",
                "menubarZoom",
                ]:
            env.widgets[widgetName].set_sensitive(False)
        env.exit("SingleObjectView.hideHelper()")

    def _connectObjectCollectionHelper(self):
        env.enter("Connecting SingleObjectView to object collection")
        env.exit("Connecting SingleObjectView to object collection")

    def _disconnectObjectCollectionHelper(self):
        env.enter("Disconnecting SingleObjectView from object collection")
        env.exit("Disconnecting SingleObjectView from object collection")

    def _freezeHelper(self):
        env.enter("SingleObjectView.freezeHelper()")
        self._clearAllConnections()
        self.clear()
        env.exit("SingleObjectView.freezeHelper()")

    def _thawHelper(self):
        env.enter("SingleObjectView.thawHelper()")
        model = self._objectCollection.getModel()
        # The row_changed event is needed when the location attribute of the image object is changed.
        self._connect(model, "row_changed", self._rowChanged)
        # The following events are needed to update the previous and next navigation buttons.
        self._connect(model, "rows_reordered", self._modelUpdated)
        self._connect(model, "row_inserted", self._modelUpdated)
        self._connect(model, "row_deleted", self._modelUpdated)
        self.importSelection(self._objectCollection.getObjectSelection())
        env.exit("SingleObjectView.thawHelper()")

    def _modelUpdated(self, *foo):
        env.debug("SingleObjectView is handling model update")
        self.importSelection(self._objectCollection.getObjectSelection())

    def _rowChanged(self, model, path, iter):
        if path[0] == self.__selectedRowNr:
            env.debug("selected object in SingleObjectView changed")
            objectSelection = self._objectCollection.getObjectSelection()
            obj = objectSelection[path[0]]
            if not obj.isAlbum():
                self.loadFile(obj.getLocation(), True)

    def _goto(self, button, direction):
        objectSelection = self._objectCollection.getObjectSelection()
        objectSelection.setSelection([self.__selectedRowNr + direction])

    def _viewWidgetFocusInEvent(self, widget, event):
        ObjectCollectionView._viewWidgetFocusInEvent(self, widget, event)
        for widgetName in [
                "menubarClear",
                "menubarSelectAll",
                ]:
            env.widgets[widgetName].set_sensitive(False)
