import gtk
import gobject
import gtk
from environment import env

class Albums:

###############################################################################            
### Public

    # TODO This class should probably be splited in a model and a view when/if
    #      a multiple windows feature is introduced.
    
    def __init__(self, mainWindow):
        self.__albumModel = gtk.TreeStore(gobject.TYPE_INT,      # ALBUM_ID
                                          gobject.TYPE_STRING,   # TAG
                                          gobject.TYPE_STRING,   # TYPE
                                          gobject.TYPE_BOOLEAN)  # SELECTABLE
        self.__mainWindow = mainWindow
        albumView = env.widgets["albumView"]
        albumView.set_model(self.__albumModel)
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Albums", renderer, text=self.__COLUMN_TAG)
        column.set_clickable(True)
        albumView.append_column(column)
        albumSelection = albumView.get_selection()
        albumSelection.connect('changed', self._albumSelectionHandler)
        albumSelection.set_select_function(self._isSelectable, self.__albumModel)
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

    def _albumSelectionHandler(self, selection):
        albumModel, iter = selection.get_selected()
        if iter:
            albumTag = albumModel.get_value(iter, self.__COLUMN_TAG)
            self.__mainWindow.loadUrl("album://" + albumTag)
        
###############################################################################        
### Private

    __COLUMN_ALBUM_ID   = 0
    __COLUMN_TAG        = 1
    __COLUMN_TYPE       = 2
    __COLUMN_SELECTABLE = 3

    def __loadAlbumTreeHelper(self, parentAlbum=None, album=None, visited=[]):
        if not album:
            album = env.shelf.getRootAlbum()
        iter = self.__albumModel.append(parentAlbum)
        # TODO Do we have to use iterators here or can we use pygtks simplified syntax?        
        self.__albumModel.set_value(iter, self.__COLUMN_ALBUM_ID, album.getId())
        self.__albumModel.set_value(iter, self.__COLUMN_TYPE, album.getType())
        self.__albumModel.set_value(iter, self.__COLUMN_TAG, album.getTag())
        self.__albumModel.set_value(iter, self.__COLUMN_SELECTABLE, True)
        if album.getId() not in visited:
            for child in album.getAlbumChildren():
                self.__loadAlbumTreeHelper(iter, child, visited + [album.getId()])
        else:
            iter = self.__albumModel.insert_before(iter, None)
            self.__albumModel.set_value(iter, self.__COLUMN_TAG, "[...]")                        
            self.__albumModel.set_value(iter, self.__COLUMN_SELECTABLE, False)
