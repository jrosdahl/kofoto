import gtk
import gobject
import gtk
from environment import env
from albumdialog import AlbumDialog
from menuhandler import *
from registerimagesdialog import RegisterImagesDialog

class Albums:

###############################################################################
### Public

    __createAlbumLabel = "Create child album..."
    __registerImagesLabel = "Register and add images..."
    __destroyAlbumLabel = "Destroy album..."
    __editAlbumLabel = "Album properties..."

    # TODO This class should probably be splited in a model and a view when/if
    #      a multiple windows feature is introduced.

    def __init__(self, mainWindow):
        self.__albumModel = gtk.TreeStore(gobject.TYPE_INT,      # ALBUM_ID
                                          gobject.TYPE_STRING,   # TAG
                                          gobject.TYPE_STRING,   # TEXT
                                          gobject.TYPE_STRING,   # TYPE
                                          gobject.TYPE_BOOLEAN)  # SELECTABLE
        self.__mainWindow = mainWindow
        self.__albumView = env.widgets["albumView"]
        self.__albumView.set_model(self.__albumModel)
        self.__albumView.connect("focus-in-event", self._treeViewFocusInEvent)
        self.__albumView.connect("focus-out-event", self._treeViewFocusOutEvent)
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Albums", renderer, text=self.__COLUMN_TEXT)
        column.set_clickable(True)
        self.__albumView.append_column(column)
        albumSelection = self.__albumView.get_selection()
        albumSelection.connect("changed", self._albumSelectionUpdated)
        albumSelection.set_select_function(self._isSelectable, self.__albumModel)
        self.__contextMenu = self.__createContextMenu()
        self._albumSelectionUpdated()
        self.__albumView.connect("button_press_event", self._button_pressed)
        self.loadAlbumTree()
        self._connectedOids = []

    def loadAlbumTree(self):
        env.shelf.flushObjectCache()
        self.__albumModel.clear()
        self.__loadAlbumTreeHelper()
        env.widgets["albumView"].expand_row(0, False) # Expand root album


###############################################################################
### Callback functions registered by this class but invoked from other classes.

    def _isSelectable(self, path, model):
        return model[path][self.__COLUMN_SELECTABLE]

    def _albumSelectionUpdated(self, selection=None, load=True):
        if not selection:
            selection = self.__albumView.get_selection()
        albumModel, iterator =  self.__albumView.get_selection().get_selected()
        createMenuItem = self.__menuGroup[self.__createAlbumLabel]
        registerMenuItem = self.__menuGroup[self.__registerImagesLabel]
        destroyMenuItem = self.__menuGroup[self.__destroyAlbumLabel]
        editMenuItem = self.__menuGroup[self.__editAlbumLabel]
        if iterator:
            albumTag = albumModel.get_value(iterator, self.__COLUMN_TAG)
            if load:
                self.__mainWindow.loadQuery("/" + albumTag.decode("utf-8"))
            album = env.shelf.getAlbum(
                albumModel.get_value(iterator, self.__COLUMN_ALBUM_ID))
            createMenuItem.set_sensitive(album.isMutable())
            env.widgets["menubarCreateAlbumChild"].set_sensitive(album.isMutable())
            registerMenuItem.set_sensitive(album.isMutable())
            env.widgets["menubarRegisterAndAddImages"].set_sensitive(album.isMutable())
            destroyMenuItem.set_sensitive(album != env.shelf.getRootAlbum())
            env.widgets["menubarDestroy"].set_sensitive(album != env.shelf.getRootAlbum())
            editMenuItem.set_sensitive(True)
            env.widgets["menubarProperties"].set_sensitive(True)
        else:
            createMenuItem.set_sensitive(False)
            registerMenuItem.set_sensitive(False)
            destroyMenuItem.set_sensitive(False)
            editMenuItem.set_sensitive(False)
            env.widgets["menubarCreateAlbumChild"].set_sensitive(False)
            env.widgets["menubarRegisterAndAddImages"].set_sensitive(False)
            env.widgets["menubarDestroy"].set_sensitive(False)
            env.widgets["menubarProperties"].set_sensitive(False)

    def _createChildAlbum(self, *dummies):
        dialog = AlbumDialog("Create album")
        dialog.run(self._createAlbumHelper)

    def _registerImages(self, *dummies):
        albumModel, iterator =  self.__albumView.get_selection().get_selected()
        selectedAlbumId = albumModel.get_value(iterator, self.__COLUMN_ALBUM_ID)
        selectedAlbum = env.shelf.getAlbum(selectedAlbumId)
        dialog = RegisterImagesDialog(selectedAlbum)
        dialog.run()
        dialog.destroy()
        # TODO: update objectCollection?

    def _createAlbumHelper(self, tag, desc):
        newAlbum = env.shelf.createAlbum(tag)
        if len(desc) > 0:
            newAlbum.setAttribute(u"title", desc)
        albumModel, iterator =  self.__albumView.get_selection().get_selected()
        if iterator is None:
            selectedAlbum = env.shelf.getRootAlbum()
        else:
            selectedAlbumId = albumModel.get_value(iterator, self.__COLUMN_ALBUM_ID)
            selectedAlbum = env.shelf.getAlbum(selectedAlbumId)
        children = list(selectedAlbum.getChildren())
        children.append(newAlbum)
        selectedAlbum.setChildren(children)
        # TODO The whole tree should not be reloaded
        self.loadAlbumTree()
        # TODO update objectCollection?

    def _destroyAlbum(self, *dummies):
        dialogId = "destroyAlbumsDialog"
        widgets = gtk.glade.XML(env.gladeFile, dialogId)
        dialog = widgets.get_widget(dialogId)
        result = dialog.run()
        if result == gtk.RESPONSE_OK:
            albumModel, iterator =  self.__albumView.get_selection().get_selected()
            selectedAlbumId = albumModel.get_value(iterator, self.__COLUMN_ALBUM_ID)
            env.shelf.deleteAlbum(selectedAlbumId)
            # TODO The whole tree should not be reloaded
            self.loadAlbumTree()
            # TODO update objectCollection?
        dialog.destroy()

    def _editAlbum(self, *dummies):
        albumModel, iterator =  self.__albumView.get_selection().get_selected()
        selectedAlbumId = albumModel.get_value(iterator, self.__COLUMN_ALBUM_ID)
        dialog = AlbumDialog("Edit album", selectedAlbumId)
        dialog.run(self._editAlbumHelper)

    def _editAlbumHelper(self, tag, desc):
        albumModel, iterator =  self.__albumView.get_selection().get_selected()
        selectedAlbumId = albumModel.get_value(iterator, self.__COLUMN_ALBUM_ID)
        selectedAlbum = env.shelf.getAlbum(selectedAlbumId)
        selectedAlbum.setTag(tag)
        if len(desc) > 0:
            selectedAlbum.setAttribute(u"title", desc)
        else:
            selectedAlbum.deleteAttribute(u"title")
        # TODO The whole tree should not be reloaded
        self.loadAlbumTree()
        # TODO update objectCollection?

    def _button_pressed(self, treeView, event):
        if event.button == 3:
            self.__contextMenu.popup(None,None,None,event.button,event.time)
            return True
        else:
            return False

    def _treeViewFocusInEvent(self, widget, event):
        self._albumSelectionUpdated(None, load=False)
        for widgetName, function in [
                ("menubarCreateAlbumChild", self._createChildAlbum),
                ("menubarRegisterAndAddImages", self._registerImages),
                ("menubarProperties", self._editAlbum),
                ]:
            oid = env.widgets[widgetName].connect("activate", function, None)
            self._connectedOids.append((env.widgets[widgetName], oid))
        for widgetName, function in [
                ("menubarCreateAlbumChild", self._createChildAlbum),
                ("menubarRegisterAndAddImages", self._registerImages),
                ("menubarProperties", self._editAlbum),
                ("menubarDestroy", self._destroyAlbum),
                ]:
            w = env.widgets[widgetName]
            oid = w.connect("activate", function, None)
            self._connectedOids.append((w, oid))

    def _treeViewFocusOutEvent(self, widget, event):
        for (widget, oid) in self._connectedOids:
            widget.disconnect(oid)
        self._connectedOids = []
        for widgetName in [
                "menubarCreateAlbumChild",
                "menubarRegisterAndAddImages",
                "menubarProperties",
                ]:
            env.widgets[widgetName].set_sensitive(False)

###############################################################################
### Private

    __COLUMN_ALBUM_ID   = 0
    __COLUMN_TAG        = 1
    __COLUMN_TEXT       = 2
    __COLUMN_TYPE       = 3
    __COLUMN_SELECTABLE = 4

    def __loadAlbumTreeHelper(self, parentAlbum=None, album=None, visited=[]):
        if not album:
            album = env.shelf.getRootAlbum()
        iterator = self.__albumModel.append(parentAlbum)
        # TODO Do we have to use iterators here or can we use pygtks simplified syntax?
        self.__albumModel.set_value(iterator, self.__COLUMN_ALBUM_ID, album.getId())
        self.__albumModel.set_value(iterator, self.__COLUMN_TYPE, album.getType())
        self.__albumModel.set_value(iterator, self.__COLUMN_TAG, album.getTag())
        self.__albumModel.set_value(iterator, self.__COLUMN_SELECTABLE, True)
        albumTitle = album.getAttribute(u"title")
        if albumTitle == None or len(albumTitle) < 1:
            self.__albumModel.set_value(iterator, self.__COLUMN_TEXT, album.getTag())
        else:
            self.__albumModel.set_value(iterator, self.__COLUMN_TEXT, albumTitle)
        if album.getId() not in visited:
            for child in album.getAlbumChildren():
                self.__loadAlbumTreeHelper(iterator, child, visited + [album.getId()])
        else:
            iterator = self.__albumModel.insert_before(iterator, None)
            self.__albumModel.set_value(iterator, self.__COLUMN_TEXT, "[...]")
            self.__albumModel.set_value(iterator, self.__COLUMN_SELECTABLE, False)

    def __createContextMenu(self):
        self.__menuGroup = MenuGroup()
        self.__menuGroup.addMenuItem(
            self.__createAlbumLabel, self._createChildAlbum)
        self.__menuGroup.addMenuItem(
            self.__registerImagesLabel, self._registerImages)
        self.__menuGroup.addMenuItem(
            self.__destroyAlbumLabel, self._destroyAlbum)
        self.__menuGroup.addStockImageMenuItem(
            self.__editAlbumLabel,
            gtk.STOCK_PROPERTIES,
            self._editAlbum)
        return self.__menuGroup.createGroupMenu()
