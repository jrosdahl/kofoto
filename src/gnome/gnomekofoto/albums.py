import gtk
import gobject
import gtk

from environment import env

class Albums:
    _COLUMN_ALBUM_ID   = 0
    _COLUMN_TAG        = 1
    _COLUMN_TYPE       = 2
    _COLUMN_SELECTABLE = 3

    _model = None
    
    def __init__(self, source):
        self._model = gtk.TreeStore(gobject.TYPE_INT,      # ALBUM_ID
                                    gobject.TYPE_STRING,   # TAG
                                    gobject.TYPE_STRING,   # TYPE
                                    gobject.TYPE_BOOLEAN)  # SELECTABLE
        albumView = env.widgets["albumView"]
        self._source = source
        albumView.set_model(self._model)
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Albums", renderer, text=self._COLUMN_TAG)
        column.set_clickable(gtk.TRUE)
        albumView.append_column(column)
        albumSelection = albumView.get_selection()
        albumSelection.connect('changed', self._albumSelectionHandler)
        albumSelection.set_select_function(self._isSelectable, self._model)
        self.reload()

    def reload(self):
        self._model.clear()
        self._buildModel(None, env.shelf.getRootAlbum(), [])
        env.widgets["albumView"].expand_row(0, gtk.FALSE)

    def _buildModel(self, parent, album, visited):
        iter = self._model.insert_before(parent, None)
        self._model.set_value(iter, self._COLUMN_ALBUM_ID, album.getId())
        self._model.set_value(iter, self._COLUMN_TYPE, album.getType())
        self._model.set_value(iter, self._COLUMN_TAG, album.getTag())
        self._model.set_value(iter, self._COLUMN_SELECTABLE, gtk.TRUE)
        if album.getId() not in visited:
            for child in album.getAlbumChildren():
                self._buildModel(iter, child, visited + [album.getId()])
        else:
            iter = self._model.insert_before(iter, None)
            self._model.set_value(iter, self._COLUMN_TAG, "[...]")                        
            self._model.set_value(iter, self._COLUMN_SELECTABLE, gtk.FALSE)        

    def _isSelectable(self, path, model):
        return model[path][self._COLUMN_SELECTABLE]

    def _albumSelectionHandler(self, selection):
        albumModel, iter = selection.get_selected()
        if iter:
            albumTag = albumModel.get_value(iter, self._COLUMN_TAG)
            self._source.set("album://" + albumTag)
