import gtk
from environment import env
from menuhandler import *
from objectcollection import *

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
        view.connect("button_press_event", self._mouse_button_pressed)

    def show(self, objectCollection):
        if self.__hidden:
            self.__hidden = False
            self.__connectObjectCollection(objectCollection)
            self._showHelper()
        else:
            self.setObjectCollection(objectCollection)

    def hide(self):
        if not self.__hidden:
            self.__hidden = True
            self._hideHelper()
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

    def _mouse_button_pressed(self, widget, event):
        if event.button == 3:
            self._contextMenu.popup(None, None, None, event.button, event.time)
            return True
        else:
            return False

##############################################################################
### Methods used by and overloaded by subbclasses

    def _connect(self, obj, signal, function):
        oid = obj.connect(signal, function)
        self.__connections.append((obj, oid))

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
        self.__commandMenuGroup = self.__createCommandMenuGroup(objectCollection)
        for item in self.__commandMenuGroup:
            self._contextMenu.add(item)
        self.__sortMenuGroup = self.__createSortMenuGroup(objectCollection)
        self._contextMenu.add(self.__sortMenuGroup.createGroupMenuItem())

    def _clearContextMenu(self):
        env.debug("Clearing view context menu")
        self._contextMenu = None
        self.__sortMenuGroup = None
        self.__clipboardMenuGroup = None

    def _updateContextMenu(self, *foo):
        env.debug("Updating context menu")
        self.__clipboardMenuGroup[self._objectCollection.getDestroyLabel()].set_sensitive(False)
        mutable = self._objectCollection.isMutable()
        if env.clipboard.hasObjects():
            self.__clipboardMenuGroup[self._objectCollection.getPasteLabel()].set_sensitive(mutable)
        else:
            self.__clipboardMenuGroup[self._objectCollection.getPasteLabel()].set_sensitive(False)
        objectSelection = self._objectCollection.getObjectSelection()
        if objectSelection:
            model = self._objectCollection.getModel()
            rootAlbumId = env.shelf.getRootAlbum().getId()

            albumsSelected = False
            imagesSelected = False
            rootAlbumSelected = False
            for position in objectSelection:
                iterator = model.get_iter(position)
                isAlbum = model.get_value(
                    iterator, self._objectCollection.COLUMN_IS_ALBUM)
                if isAlbum:
                    albumsSelected = True
                    if rootAlbumId == model.get_value(
                        iterator, self._objectCollection.COLUMN_OBJECT_ID):
                        rootAlbumSelected = True
                else:
                    imagesSelected = True

            self.__clipboardMenuGroup[self._objectCollection.getCopyLabel()].set_sensitive(True)
            self.__clipboardMenuGroup[self._objectCollection.getCutLabel()].set_sensitive(mutable)
            self.__clipboardMenuGroup[self._objectCollection.getDeleteLabel()].set_sensitive(mutable)
            self.__clipboardMenuGroup[self._objectCollection.getDestroyLabel()].set_sensitive(
                imagesSelected ^ albumsSelected and not rootAlbumSelected)
            self.__commandMenuGroup["Open image"].set_sensitive(True)
            self.__commandMenuGroup[90].set_sensitive(True)
            self.__commandMenuGroup[270].set_sensitive(True)
        else:
            self.__clipboardMenuGroup[self._objectCollection.getCopyLabel()].set_sensitive(False)
            self.__clipboardMenuGroup[self._objectCollection.getCutLabel()].set_sensitive(False)
            self.__clipboardMenuGroup[self._objectCollection.getDeleteLabel()].set_sensitive(False)
            self.__clipboardMenuGroup[self._objectCollection.getDestroyLabel()].set_sensitive(False)
            self.__commandMenuGroup["Open image"].set_sensitive(False)
            self.__commandMenuGroup[90].set_sensitive(False)
            self.__commandMenuGroup[270].set_sensitive(False)

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
            columnNames = list(objectMetadataMap.keys())
            columnNames.sort()
            for columnName in columnNames:
                if objectMetadataMap[columnName][ObjectCollection.TYPE] != gtk.gdk.Pixbuf:
                    menuGroup.addRadioMenuItem(columnName,
                                               objectCollection.setSortColumnName,
                                               columnName)
        return menuGroup

    def __createClipboardMenuGroup(self, oc):
        menuGroup = MenuGroup()
        env.debug("Creating clipboard menu")
        menuGroup.addMenuItem(oc.getCutLabel(), oc.cut)
        menuGroup.addMenuItem(oc.getCopyLabel(), oc.copy)
        menuGroup.addMenuItem(oc.getPasteLabel(), oc.paste)
        menuGroup.addMenuItem(oc.getDeleteLabel(), oc.delete)
        menuGroup.addSeparator()
        menuGroup.addMenuItem(oc.getDestroyLabel(), oc.destroy)
        menuGroup.addSeparator()
        return menuGroup

    def __createCommandMenuGroup(self, oc):
        menuGroup = MenuGroup()
        menuGroup.addMenuItem("Open image", oc.open)
        menuGroup.addMenuItem("Rotate JPEG left", oc.rotate, 270)
        menuGroup.addMenuItem("Rotate JPEG right", oc.rotate, 90)
        menuGroup.addSeparator()
        return menuGroup
