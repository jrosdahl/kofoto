# pylint: disable-msg=F0203, E0201

import gtk
from kofoto.gkofoto.environment import env
from kofoto.gkofoto.imageview import ImageView
from kofoto.gkofoto.objectcollectionview import ObjectCollectionView
from kofoto.gkofoto.imageversionslist import ImageVersionsList

def _make_callback_wrapper(fn):
    def f(*unused):
        fn()
    return f

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
        self.__imageVersionsList = ImageVersionsList(self)
        self.__imageVersionsFrame.add(self.__imageVersionsList)
        self.pack2(self.__imageVersionsFrame, resize=False)
        self.show_all()
        env.widgets["nextButton"].connect("clicked", self._goto, 1)
        env.widgets["menubarNextImage"].connect("activate", self._goto, 1)
        env.widgets["previousButton"].connect("clicked", self._goto, -1)
        env.widgets["menubarPreviousImage"].connect("activate", self._goto, -1)
        env.widgets["zoomToFit"].connect(
            "clicked", _make_callback_wrapper(self.__imageView.zoom_to_fit))
        env.widgets["menubarZoomToFit"].connect(
            "activate", _make_callback_wrapper(self.__imageView.zoom_to_fit))
        env.widgets["zoom100"].connect(
            "clicked", _make_callback_wrapper(self.__imageView.zoom_to_actual))
        env.widgets["menubarActualSize"].connect(
            "activate", _make_callback_wrapper(self.__imageView.zoom_to_actual))
        env.widgets["zoomIn"].connect(
            "clicked", _make_callback_wrapper(self.__imageView.zoom_in))
        env.widgets["menubarZoomIn"].connect(
            "activate", _make_callback_wrapper(self.__imageView.zoom_in))
        env.widgets["zoomOut"].connect(
            "clicked", _make_callback_wrapper(self.__imageView.zoom_out))
        env.widgets["menubarZoomOut"].connect(
            "activate", _make_callback_wrapper(self.__imageView.zoom_out))
        env.widgets["menubarViewDetailsPane"].set_sensitive(True)
        self.__loadedObject = False
        self.__selectionLocked = False
        self.__selectedRowNr = None
        self.__currentImageLocation = None
        self.__latestLoadPixbufHandle = None
        self.__latestSize = (0, 0)

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
            location = env.unknownImageIconFileName
        elif obj.isAlbum():
            location = env.albumIconFileName
        elif obj.getPrimaryVersion():
            location = obj.getPrimaryVersion().getLocation()
            self.__imageVersionsList.loadImage(obj)
        else:
            location = env.unknownImageIconFileName
        self._loadImageAtLocation(location)

    def _loadImageAtLocation(self, location):
        if location == self.__currentImageLocation:
            return
        self.__currentImageLocation = location
        self.__imageView.set_image(self.__loadPixbuf_cb)

    def __loadPixbuf_cb(self, size_limit):
        if self.__latestLoadPixbufHandle is not None:
            env.pixbufLoader.cancel_load(self.__latestLoadPixbufHandle)
        self.__latestLoadPixbufHandle = env.pixbufLoader.load(
            self.__currentImageLocation,
            size_limit,
            self.__imageView.set_from_pixbuf,
            self.__imageView.set_error)
        if size_limit != self.__latestSize:
            self._unloadImages(self.__latestSize)
        self._preloadImages(size_limit)
        self.__latestSize = size_limit

    def _reloadSingleObjectView(self):
        self.reload()

    def reload(self):
        self.__loadObject(self.__loadedObject)
        self.__imageVersionsList.reload()
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

    def _modelUpdated(self, *unused):
        env.debug("SingleObjectView is handling model update")
        self.importSelection(self._objectCollection.getObjectSelection())

    def _goto(self, unused, direction):
        objectSelection = self._objectCollection.getObjectSelection()
        objectSelection.setSelection([self.__selectedRowNr + direction])

    def _preloadImages(self, size):
        self._preloadOrUnloadImages(size, True)

    def _preloadOrUnloadImages(self, size, preload):
        objectSelection = self._objectCollection.getObjectSelection()
        for location in objectSelection.getImageFilenamesToPreload():
            if preload:
                env.pixbufLoader.preload(location, size)
            else:
                env.pixbufLoader.unload(location, size)

    def _unloadImages(self, size):
        self._preloadOrUnloadImages(size, False)

    def _hasFocus(self):
        return True

    def _mouse_button_pressed(self, widget, event):
        if event.button == 1 and event.type == gtk.gdk._2BUTTON_PRESS:
            env.mainwindow._fullScreen()
        else:
            ObjectCollectionView._mouse_button_pressed(self, widget, event)
