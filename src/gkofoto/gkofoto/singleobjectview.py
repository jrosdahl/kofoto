import gtk
import sys
from environment import env
from gkofoto.imageview import *
from gkofoto.objectcollectionview import *
from gkofoto.imageversionslist import ImageVersionsList

class SingleObjectView(ObjectCollectionView, gtk.HPaned):

###############################################################################
### Public

    def __init__(self):
        env.debug("Init SingleObjectView")
        ObjectCollectionView.__init__(self, env.widgets["objectView"])
        gtk.HPaned.__init__(self)
        self._viewWidget.add(self)
        self.__imageView = ImageView()
        self.__imageView.connect("button_press_event", self._mouse_button_pressed)
        self.pack1(self.__imageView, resize=True)
        self.__imageVersionsFrame = gtk.Frame("Image versions")
        self.__imageVersionsFrame.set_size_request(162, -1)
        self.__imageVersionsWindow = gtk.ScrolledWindow()
        self.__imageVersionsList = ImageVersionsList(self, self.__imageView)
        self.__imageVersionsFrame.add(self.__imageVersionsList)
        self.pack2(self.__imageVersionsFrame, resize=False)
        self.show_all()
        env.widgets["nextButton"].connect("clicked", self._goto, 1)
        env.widgets["menubarNextImage"].connect("activate", self._goto, 1)
        env.widgets["previousButton"].connect("clicked", self._goto, -1)
        env.widgets["menubarPreviousImage"].connect("activate", self._goto, -1)
        env.widgets["zoomToFit"].connect("clicked", self.__imageView.fitToWindow)
        env.widgets["menubarZoomToFit"].connect("activate", self.__imageView.fitToWindow)
        env.widgets["zoom100"].connect("clicked", self.__imageView.zoom100)
        env.widgets["menubarActualSize"].connect("activate", self.__imageView.zoom100)
        env.widgets["zoomIn"].connect("clicked", self.__imageView.zoomIn)
        env.widgets["menubarZoomIn"].connect("activate", self.__imageView.zoomIn)
        env.widgets["zoomOut"].connect("clicked", self.__imageView.zoomOut)
        env.widgets["menubarZoomOut"].connect("activate", self.__imageView.zoomOut)
        env.widgets["mainWindow"].connect("key_press_event", self._key_pressed)
        env.widgets["menubarViewDetailsPane"].set_sensitive(True)
        self.__selectionLocked = False

    def showDetailsPane(self):
        self.__imageVersionsFrame.show()

    def hideDetailsPane(self):
        self.__imageVersionsFrame.hide()

    def importSelection(self, objectSelection):
        if not self.__selectionLocked:
            env.debug("SingleImageView is importing selection")
            self.__selectionLocked = True
            model = self._objectCollection.getModel()
            self.__loadedObject = None
            if len(model) == 0:
                # Model is empty. No rows can be selected.
                self.__selectedRowNr = -1
                self.__imageView.clear()
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
                self.__loadedObject = objectSelection[self.__selectedRowNr]
            self.__loadObject(self.__loadedObject)
            enablePreviousButton = (self.__selectedRowNr > 0)
            env.widgets["previousButton"].set_sensitive(enablePreviousButton)
            env.widgets["menubarPreviousImage"].set_sensitive(enablePreviousButton)
            enableNextButton = (self.__selectedRowNr != -1 and
                                self.__selectedRowNr < len(model) - 1)
            env.widgets["nextButton"].set_sensitive(enableNextButton)
            env.widgets["menubarNextImage"].set_sensitive(enableNextButton)
            self._preloadImages()
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

    def __loadObject(self, obj):
        self.__imageVersionsList.clear()
        if obj == None:
            filename = env.unknownImageIconFileName
        elif obj.isAlbum():
            filename = env.albumIconFileName
        elif obj.getPrimaryVersion():
            filename = obj.getPrimaryVersion().getLocation()
            self.__imageVersionsList.loadImage(obj)
        else:
            filename = env.unknownImageIconFileName
        self.__imageView.loadFile(filename)

    def reload(self):
        self.__loadObject(self.__loadedObject)
        self._objectCollection.reloadSelectedRows()

    def _showHelper(self):
        env.enter("SingleObjectView.showHelper()")
        env.widgets["objectView"].show()
        env.widgets["objectView"].grab_focus()
        self._connectMenubarImageItems() # Grossest hack of the month. Sigh.
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
        self.__imageView.clear()
        self._objectCollection.removeInsertedRowCallback(self._modelUpdated)
        env.exit("SingleObjectView.freezeHelper()")

    def _thawHelper(self):
        env.enter("SingleObjectView.thawHelper()")
        model = self._objectCollection.getModel()
        # The following events are needed to update the previous and
        # next navigation buttons.
        self._connect(model, "rows_reordered", self._modelUpdated)
        self._connect(model, "row_deleted", self._modelUpdated)
        self._objectCollection.addInsertedRowCallback(self._modelUpdated)
        env.exit("SingleObjectView.thawHelper()")

    def _modelUpdated(self, *foo):
        env.debug("SingleObjectView is handling model update")
        self.importSelection(self._objectCollection.getObjectSelection())

    def _goto(self, button, direction):
        objectSelection = self._objectCollection.getObjectSelection()
        objectSelection.setSelection([self.__selectedRowNr + direction])

    def _preloadImages(self):
        objectSelection = self._objectCollection.getObjectSelection()
        filenames = objectSelection.getImageFilenamesToPreload()
        maxWidth, maxHeight = self.__imageView.getAvailableSpace()

        # Work-around for bug in GTK. (pixbuf.scale_iter(1, 1) crashes.)
        if maxWidth < 10 and maxHeight < 10:
            return

        env.mainwindow.getImagePreloader().preloadImages(
            filenames, maxWidth, maxHeight)

    def _key_pressed(self, widget, event):
        # TODO use UiManager instead of this...
        if event.state & gtk.gdk.CONTROL_MASK:
            if (event.keyval == gtk.gdk.keyval_from_name("space") and
                env.widgets["nextButton"].flags() & gtk.SENSITIVE):
                self._goto(None, 1)
            elif (event.keyval == gtk.gdk.keyval_from_name("BackSpace") and
                  env.widgets["previousButton"].flags() & gtk.SENSITIVE):
                self._goto(None, -1)
        return False

    def _hasFocus(self):
        return True
