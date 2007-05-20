import gtk
import os
from kofoto.gkofoto.environment import env
from kofoto.gkofoto.menuhandler import MenuGroup
from kofoto.gkofoto.objectcollection import ObjectCollection
from kofoto.common import UnimplementedError

class ObjectCollectionView:

###############################################################################
### Public

    def __init__(self, view):
        self._viewWidget = view
        self._objectCollection = None
        self._contextMenu = None
        self.__objectCollectionLoaded = False
        self.__hidden = True
        self.__connections = []
        self.__singleImageMenuGroup = None
        self.__objectMenuGroup = None
        self.__multipleImagesMenuGroup = None
        self.__sortMenuGroup = None
        self.__albumMenuGroup = None
        self.__clipboardMenuGroup = None
        self.__imageMenuGroup = None

    def show(self, objectCollection):
        if self.__hidden:
            self.__hidden = False
            self.__connectObjectCollection(objectCollection)
            self._showHelper()
            self._updateMenubarSortMenu()
        else:
            self.setObjectCollection(objectCollection)

    def _connectMenubarImageItems(self):
        self._connect(
            env.widgets["menubarOpenImage"],
            "activate",
            self._objectCollection.openImage)
        self._connect(
            env.widgets["menubarDuplicateAndOpenImage"],
            "activate",
            self._objectCollection.duplicateAndOpenImage)
        self._connect(
            env.widgets["menubarRotateLeft"],
            "activate",
            self._objectCollection.rotateImage,
            270)
        self._connect(
            env.widgets["menubarRotateRight"],
            "activate",
            self._objectCollection.rotateImage,
            90)
        self._connect(
            env.widgets["menubarImageVersions"],
            "activate",
            self._objectCollection.imageVersions)
        self._connect(
            env.widgets["menubarRegisterImageVersions"],
            "activate",
            self._objectCollection.registerImageVersions)
        self._connect(
            env.widgets["menubarMergeImages"],
            "activate",
            self._objectCollection.mergeImages)

    def _updateMenubarSortMenu(self):
        sortMenuGroup = self.__createSortMenuGroup(self._objectCollection)
        sortByItem = env.widgets["menubarSortBy"]
        if self._objectCollection.isSortable():
            sortByItem.set_sensitive(True)
            sortByItem.set_submenu(sortMenuGroup.createGroupMenu())
        else:
            sortByItem.remove_submenu()
            sortByItem.set_sensitive(False)

    def hide(self):
        if not self.__hidden:
            self.__hidden = True
            self._hideHelper()
            self._clearAllConnections()
            self.__disconnectObjectCollection()

    def setObjectCollection(self, objectCollection):
        if not self.__hidden:
            env.debug("ObjectCollectionView sets object collection")
            self.__connectObjectCollection(objectCollection)

    def freeze(self):
        self._freezeHelper()
        self._objectCollection.getObjectSelection().removeChangedCallback(self.importSelection)
        env.clipboard.removeChangedCallback(self._updateContextMenu)

    def thaw(self):
        self._thawHelper()
        self._objectCollection.getObjectSelection().addChangedCallback(self.importSelection)
        env.clipboard.addChangedCallback(self._updateContextMenu)
        self.importSelection(self._objectCollection.getObjectSelection())
        # importSelection makes an implicit _updateContextMenu()

    def sortOrderChanged(self, sortOrder):
        env.debug("Sort order is " + str(sortOrder))
        self.__sortMenuGroup[sortOrder].activate()

    def sortColumnChanged(self, sortColumn):
        env.debug("Sort column is " + str(sortColumn))
        self.__sortMenuGroup[sortColumn].activate()

    def fieldsDisabled(self, fields):
        pass

    def fieldsEnabled(self, fields):
        pass

    def loadingFinished(self):
        self._updateContextMenu()

    def _mouse_button_pressed(self, widget, event):
        widget.grab_focus()
        if event.button == 3:
            self._contextMenu.popup(None, None, None, event.button, event.time)
            return True
        else:
            return False

##############################################################################
### Methods used by and overloaded by subclasses

    def _hasFocus(self):
        raise UnimplementedError

    def _showHelper(self):
        raise UnimplementedError

    def _hideHelper(self):
        raise UnimplementedError

    def _freezeHelper(self):
        raise UnimplementedError

    def _thawHelper(self):
        raise UnimplementedError

    def _connectObjectCollectionHelper(self):
        raise UnimplementedError

    def _disconnectObjectCollectionHelper(self):
        raise UnimplementedError

    def importSelection(self, objectCollection):
        raise UnimplementedError

    def _connect(self, obj, signal, function, data=None):
        oid = obj.connect(signal, function, data)
        self.__connections.append((obj, oid))
        return oid

    def _disconnect(self, obj, oid):
        obj.disconnect(oid)
        self.__connections.remove((obj, oid))

    def _clearAllConnections(self):
        for (obj, oid) in self.__connections:
            obj.disconnect(oid)
        self.__connections = []

    def _createContextMenu(self, objectCollection):
        env.debug("Creating view context menu")
        self._contextMenu = gtk.Menu()
        self.__clipboardMenuGroup = self.__createClipboardMenuGroup(objectCollection)
        for item in self.__clipboardMenuGroup:
            self._contextMenu.add(item)
        self.__objectMenuGroup = self.__createObjectMenuGroup(objectCollection)
        for item in self.__objectMenuGroup:
            self._contextMenu.add(item)
        self.__albumMenuGroup = self.__createAlbumMenuGroup(objectCollection)
        for item in self.__albumMenuGroup:
            self._contextMenu.add(item)
        self.__imageMenuGroup = self.__createImageMenuGroup(objectCollection)
        for item in self.__imageMenuGroup:
            self._contextMenu.add(item)
        self.__singleImageMenuGroup = self.__createSingleImageMenuGroup(objectCollection)
        for item in self.__singleImageMenuGroup:
            self._contextMenu.add(item)
        self.__multipleImagesMenuGroup = self.__createMultipleImagesMenuGroup(objectCollection)
        for item in self.__multipleImagesMenuGroup:
            self._contextMenu.add(item)
        self.__sortMenuGroup = self.__createSortMenuGroup(objectCollection)
        self._contextMenu.add(self.__sortMenuGroup.createGroupMenuItem())

    def _clearContextMenu(self):
        env.debug("Clearing view context menu")
        self._contextMenu = None
        self.__clipboardMenuGroup = None
        self.__objectMenuGroup = None
        self.__albumMenuGroup = None
        self.__imageMenuGroup = None
        self.__singleImageMenuGroup = None
        self.__multipleImagesMenuGroup = None
        self.__sortMenuGroup = None

    def _updateContextMenu(self, *unused):
        if not self._hasFocus():
            return
        env.debug("Updating context menu")
        self.__objectMenuGroup[self._objectCollection.getDestroyLabel()].set_sensitive(False)
        env.widgets["menubarDestroy"].set_sensitive(False)
        mutable = self._objectCollection.isMutable()
        loading = self._objectCollection.isLoading()
        objectSelection = self._objectCollection.getObjectSelection()
        if objectSelection:
            model = self._objectCollection.getModel()
            rootAlbumId = env.shelf.getRootAlbum().getId()

            albumsSelected = 0
            imagesSelected = 0
            rootAlbumSelected = False
            for position in objectSelection:
                iterator = model.get_iter(position)
                isAlbum = model.get_value(
                    iterator, self._objectCollection.COLUMN_IS_ALBUM)
                if isAlbum:
                    albumsSelected += 1
                    if rootAlbumId == model.get_value(
                        iterator, self._objectCollection.COLUMN_OBJECT_ID):
                        rootAlbumSelected = True
                else:
                    imagesSelected += 1

            self.__clipboardMenuGroup[self._objectCollection.getCutLabel()].set_sensitive(mutable and not loading)
            env.widgets["menubarCut"].set_sensitive(mutable and not loading)
            self.__clipboardMenuGroup[self._objectCollection.getCopyLabel()].set_sensitive(True)
            env.widgets["menubarCopy"].set_sensitive(True)
            self.__clipboardMenuGroup[self._objectCollection.getDeleteLabel()].set_sensitive(mutable and not loading)
            env.widgets["menubarDelete"].set_sensitive(mutable and not loading)
            destroyActive = (imagesSelected == 0) ^ (albumsSelected == 0) and not rootAlbumSelected and not loading
            self.__objectMenuGroup[self._objectCollection.getDestroyLabel()].set_sensitive(destroyActive)
            env.widgets["menubarDestroy"].set_sensitive(destroyActive)
            if albumsSelected == 1 and imagesSelected == 0:
                selectedAlbumId = model.get_value(
                    iterator, self._objectCollection.COLUMN_OBJECT_ID)
                selectedAlbum = env.shelf.getAlbum(selectedAlbumId)
                if selectedAlbum.isMutable():
                    self.__albumMenuGroup.enable()
                    env.widgets["menubarCreateAlbumChild"].set_sensitive(True)
                    env.widgets["menubarRegisterAndAddImages"].set_sensitive(True)
                    env.widgets["menubarGenerateHtml"].set_sensitive(True)
                    env.widgets["menubarProperties"].set_sensitive(True)
                else:
                    self.__albumMenuGroup.disable()
                    self.__albumMenuGroup[
                        self._objectCollection.getAlbumPropertiesLabel()
                        ].set_sensitive(True)
                    env.widgets["menubarCreateAlbumChild"].set_sensitive(False)
                    env.widgets["menubarRegisterAndAddImages"].set_sensitive(False)
                    env.widgets["menubarGenerateHtml"].set_sensitive(True)
                    env.widgets["menubarProperties"].set_sensitive(True)
            else:
                self.__albumMenuGroup.disable()
                env.widgets["menubarCreateAlbumChild"].set_sensitive(False)
                env.widgets["menubarRegisterAndAddImages"].set_sensitive(False)
                env.widgets["menubarGenerateHtml"].set_sensitive(False)
                env.widgets["menubarProperties"].set_sensitive(False)
            if albumsSelected == 0 and imagesSelected > 0:
                self.__imageMenuGroup.enable()
                env.widgets["menubarOpenImage"].set_sensitive(True)
                env.widgets["menubarRotateLeft"].set_sensitive(True)
                env.widgets["menubarRotateRight"].set_sensitive(True)
                if imagesSelected == 1:
                    env.widgets["menubarDuplicateAndOpenImage"].set_sensitive(True)
                    self.__singleImageMenuGroup.enable()
                    env.widgets["menubarImageVersions"].set_sensitive(True)
                    env.widgets["menubarRegisterImageVersions"].set_sensitive(True)
                    self.__multipleImagesMenuGroup.disable()
                    env.widgets["menubarMergeImages"].set_sensitive(False)
                else:
                    self.__imageMenuGroup[
                        self._objectCollection.getDuplicateAndOpenImageLabel()
                        ].set_sensitive(False)
                    env.widgets["menubarDuplicateAndOpenImage"].set_sensitive(False)
                    self.__singleImageMenuGroup.disable()
                    env.widgets["menubarImageVersions"].set_sensitive(False)
                    env.widgets["menubarRegisterImageVersions"].set_sensitive(False)
                    self.__multipleImagesMenuGroup.enable()
                    env.widgets["menubarMergeImages"].set_sensitive(True)
            else:
                self.__imageMenuGroup.disable()
                self.__singleImageMenuGroup.disable()
                env.widgets["menubarOpenImage"].set_sensitive(False)
                env.widgets["menubarDuplicateAndOpenImage"].set_sensitive(False)
                env.widgets["menubarRegisterImageVersions"].set_sensitive(False)
                env.widgets["menubarRotateLeft"].set_sensitive(False)
                env.widgets["menubarRotateRight"].set_sensitive(False)
        else:
            self.__clipboardMenuGroup.disable()
            env.widgets["menubarCut"].set_sensitive(False)
            env.widgets["menubarCopy"].set_sensitive(False)
            env.widgets["menubarDelete"].set_sensitive(False)

            self.__objectMenuGroup.disable()
            env.widgets["menubarDestroy"].set_sensitive(False)

            self.__albumMenuGroup.disable()
            env.widgets["menubarCreateAlbumChild"].set_sensitive(False)
            env.widgets["menubarRegisterAndAddImages"].set_sensitive(False)
            env.widgets["menubarGenerateHtml"].set_sensitive(False)
            env.widgets["menubarProperties"].set_sensitive(False)

            self.__imageMenuGroup.disable()
            env.widgets["menubarOpenImage"].set_sensitive(False)
            env.widgets["menubarDuplicateAndOpenImage"].set_sensitive(False)
            env.widgets["menubarRotateLeft"].set_sensitive(False)
            env.widgets["menubarRotateRight"].set_sensitive(False)
            self.__singleImageMenuGroup.disable()
            env.widgets["menubarImageVersions"].set_sensitive(False)
            env.widgets["menubarRegisterImageVersions"].set_sensitive(False)
            self.__multipleImagesMenuGroup.disable()
            env.widgets["menubarMergeImages"].set_sensitive(False)

        if env.clipboard.hasObjects():
            self.__clipboardMenuGroup[
                self._objectCollection.getPasteLabel()].set_sensitive(mutable)
            env.widgets["menubarPaste"].set_sensitive(mutable)
        else:
            self.__clipboardMenuGroup[
                self._objectCollection.getPasteLabel()].set_sensitive(False)
            env.widgets["menubarPaste"].set_sensitive(False)


###############################################################################
### Private

    def __connectObjectCollection(self, objectCollection):
        if self._objectCollection != None:
            self.__disconnectObjectCollection()
        self._objectCollection = objectCollection
        self._createContextMenu(objectCollection)
        self._connectObjectCollectionHelper()
        self.thaw()
        self._objectCollection.registerView(self)

    def __disconnectObjectCollection(self):
        if self._objectCollection is not None:
            self._objectCollection.unRegisterView(self)
            self.freeze()
            self._disconnectObjectCollectionHelper()
            self._clearContextMenu()
            self._objectCollection = None

    def __createSortMenuGroup(self, objectCollection):
        menuGroup = MenuGroup("Sort by")
        if objectCollection.isSortable():
            env.debug("Creating sort menu group for sortable log collection")
            menuGroup.addRadioMenuItem("Ascending",
                                       objectCollection.setSortOrder,
                                       gtk.SORT_ASCENDING)
            menuGroup.addRadioMenuItem("Descending",
                                       objectCollection.setSortOrder,
                                       gtk.SORT_DESCENDING)
            menuGroup.addSeparator()
            objectMetadataMap = objectCollection.getObjectMetadataMap()
            columnNames = sorted(objectMetadataMap)
            for columnName in columnNames:
                if objectMetadataMap[columnName][ObjectCollection.TYPE] != gtk.gdk.Pixbuf:
                    menuGroup.addRadioMenuItem(columnName,
                                               objectCollection.setSortColumnName,
                                               columnName)
        return menuGroup

    def __createClipboardMenuGroup(self, oc):
        menuGroup = MenuGroup()
        env.debug("Creating clipboard menu")
        menuGroup.addStockImageMenuItem(
            oc.getCutLabel(), gtk.STOCK_CUT, oc.cut)
        menuGroup.addStockImageMenuItem(
            oc.getCopyLabel(), gtk.STOCK_COPY, oc.copy)
        menuGroup.addStockImageMenuItem(
            oc.getPasteLabel(), gtk.STOCK_PASTE, oc.paste)
        menuGroup.addStockImageMenuItem(
            oc.getDeleteLabel(), gtk.STOCK_DELETE, oc.delete)
        menuGroup.addSeparator()
        return menuGroup

    def __createObjectMenuGroup(self, oc):
        menuGroup = MenuGroup()
        menuGroup.addStockImageMenuItem(
            oc.getDestroyLabel(), gtk.STOCK_DELETE, oc.destroy)
        menuGroup.addSeparator()
        return menuGroup

    def __createAlbumMenuGroup(self, oc):
        menuGroup = MenuGroup()
        menuGroup.addMenuItem(
            oc.getCreateAlbumChildLabel(), oc.createAlbumChild)
        menuGroup.addMenuItem(
            oc.getRegisterImagesLabel(), oc.registerAndAddImages)
        menuGroup.addMenuItem(
            oc.getGenerateHtmlLabel(), oc.generateHtml)
        menuGroup.addStockImageMenuItem(
            oc.getAlbumPropertiesLabel(),
            gtk.STOCK_PROPERTIES,
            oc.albumProperties)
        menuGroup.addSeparator()
        return menuGroup

    def __createImageMenuGroup(self, oc):
        menuGroup = MenuGroup()
        menuGroup.addStockImageMenuItem(
            oc.getOpenImageLabel(),
            gtk.STOCK_OPEN,
            oc.openImage)
        menuGroup.addStockImageMenuItem(
            oc.getDuplicateAndOpenImageLabel(),
            gtk.STOCK_OPEN,
            oc.duplicateAndOpenImage)
        menuGroup.addImageMenuItem(
            oc.getRotateImageLeftLabel(),
            os.path.join(env.iconDir, "rotateleft.png"),
            oc.rotateImage, 270)
        menuGroup.addImageMenuItem(
            oc.getRotateImageRightLabel(),
            os.path.join(env.iconDir, "rotateright.png"),
            oc.rotateImage, 90)
        menuGroup.addSeparator()
        return menuGroup

    def __createSingleImageMenuGroup(self, oc):
        menuGroup = MenuGroup()
        menuGroup.addMenuItem(oc.getImageVersionsLabel(), oc.imageVersions)
        menuGroup.addMenuItem(
            oc.getRegisterImageVersionsLabel(), oc.registerImageVersions)
        return menuGroup

    def __createMultipleImagesMenuGroup(self, oc):
        menuGroup = MenuGroup()
        menuGroup.addMenuItem(oc.getMergeImagesLabel(), oc.mergeImages)
        menuGroup.addSeparator()
        return menuGroup
