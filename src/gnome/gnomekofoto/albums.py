import gtk
import gobject
import gtk
from environment import env
from albumdialog import AlbumDialog
from menuhandler import *

class Albums:

###############################################################################            
### Public

    __createAlbumLabel = "Create child album"
    __destroyAlbumLabel = "Destroy album"
    __editAlbumLabel = "Album properties"
    
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
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Albums", renderer, text=self.__COLUMN_TEXT)
        column.set_clickable(True)
        self.__albumView.append_column(column)
        albumSelection = self.__albumView.get_selection()
        albumSelection.connect('changed', self._albumSelectionUpdated)
        albumSelection.set_select_function(self._isSelectable, self.__albumModel)
        self.__contextMenu = self.__createContextMenu()
        self._albumSelectionUpdated()
        self.__albumView.connect("button_press_event", self._button_pressed)
        self.loadAlbumTree()

    def loadAlbumTree(self):
        env.shelf.flushObjectCache()
        self.__albumModel.clear()
        self.__loadAlbumTreeHelper()
        env.widgets["albumView"].expand_row(0, False) # Expand root album
        

###############################################################################
### Callback functions registered by this class but invoked from other classes.

    def _isSelectable(self, path, model):
        return model[path][self.__COLUMN_SELECTABLE]

    def _albumSelectionUpdated(self, selection=None):
        if not selection:
            selection = self.__albumView.get_selection()
        albumModel, iter =  self.__albumView.get_selection().get_selected()
        destroyMenuItem = self.__menuGroup[self.__destroyAlbumLabel]
        editMenuItem = self.__menuGroup[self.__editAlbumLabel]
        if iter:
            albumTag = albumModel.get_value(iter, self.__COLUMN_TAG)
            self.__mainWindow.loadUrl("album://" + albumTag)
            destroyMenuItem.set_sensitive(True)
            editMenuItem.set_sensitive(True)            
        else:
            destroyMenuItem.set_sensitive(False)
            editMenuItem.set_sensitive(False)

    def _createChildAlbum(self, *dummies):
        dialog = AlbumDialog("Create album")
        dialog.run(self._createAlbumHelper)

    def _createAlbumHelper(self, tag, desc):
        newAlbum = env.shelf.createAlbum(tag)
        if len(desc) > 0:
            newAlbum.setAttribute(u"title", desc)
        albumModel, iter =  self.__albumView.get_selection().get_selected()
        if iter is None:
            selectedAlbum = env.shelf.getRootAlbum()
        else:
            selectedAlbumTag = albumModel.get_value(iter, self.__COLUMN_TAG)
            selectedAlbum = env.shelf.getAlbum(selectedAlbumTag)
        children = list(selectedAlbum.getChildren())
        children.append(newAlbum)
        selectedAlbum.setChildren(children)
        # TODO The whole tree should not be reloaded
        self.loadAlbumTree()
        # TODO update objectCollection?
        
    def _destroyAlbum(self, *dummies):
        # TODO add confirmation dialog?
        albumModel, iter =  self.__albumView.get_selection().get_selected()
        selectedAlbumTag = albumModel.get_value(iter, self.__COLUMN_TAG)
        env.shelf.deleteAlbum(selectedAlbumTag.decode("utf-8"))
        # TODO The whole tree should not be reloaded
        self.loadAlbumTree()
        # TODO update objectCollection?

    def _editAlbum(self, *dummies):
        albumModel, iter =  self.__albumView.get_selection().get_selected()
        selectedAlbumId = albumModel.get_value(iter, self.__COLUMN_ALBUM_ID)
        dialog = AlbumDialog("Edit album", selectedAlbumId)
        dialog.run(self._editAlbumHelper)

    def _editAlbumHelper(self, tag, desc):
        albumModel, iter =  self.__albumView.get_selection().get_selected()
        selectedAlbumTag = albumModel.get_value(iter, self.__COLUMN_TAG)
        selectedAlbum = env.shelf.getAlbum(selectedAlbumTag)
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
        iter = self.__albumModel.append(parentAlbum)
        # TODO Do we have to use iterators here or can we use pygtks simplified syntax?        
        self.__albumModel.set_value(iter, self.__COLUMN_ALBUM_ID, album.getId())
        self.__albumModel.set_value(iter, self.__COLUMN_TYPE, album.getType())
        self.__albumModel.set_value(iter, self.__COLUMN_TAG, album.getTag())
        self.__albumModel.set_value(iter, self.__COLUMN_SELECTABLE, True)
        albumTitle = album.getAttribute(u"title")
        if albumTitle == None or len(albumTitle) < 1:
            self.__albumModel.set_value(iter, self.__COLUMN_TEXT, album.getTag())
        else:
            self.__albumModel.set_value(iter, self.__COLUMN_TEXT, albumTitle)
        if album.getId() not in visited:
            for child in album.getAlbumChildren():
                self.__loadAlbumTreeHelper(iter, child, visited + [album.getId()])
        else:
            iter = self.__albumModel.insert_before(iter, None)
            self.__albumModel.set_value(iter, self.__COLUMN_TEXT, "[...]")
            self.__albumModel.set_value(iter, self.__COLUMN_SELECTABLE, False)

    def __createContextMenu(self):
        self.__menuGroup = MenuGroup()
        self.__menuGroup.addMenuItem(self.__createAlbumLabel,
                                     self._createChildAlbum)
        self.__menuGroup.addMenuItem(self.__destroyAlbumLabel,
                                     self._destroyAlbum)
        self.__menuGroup.addMenuItem(self.__editAlbumLabel,
                                     self._editAlbum)
        return self.__menuGroup.createGroupMenu()

