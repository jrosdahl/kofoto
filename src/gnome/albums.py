import gtk
import gobject
import gtk

from environment import env

class Albums:
    _COLUMN_ALBUM_ID  = 0
    _COLUMN_TAG       = 1
    _COLUMN_TYPE      = 2

    _model = None
    
    def __init__(self, source):
        self._model = gtk.TreeStore(gobject.TYPE_INT,      # ALBUM_ID
                                    gobject.TYPE_STRING,   # TAG
                                    gobject.TYPE_STRING)   # TYPE
        albumView = env.widgets["albumView"]
        self._source = source
        albumView.set_model(self._model)
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Albums", renderer, text=self._COLUMN_TAG)
        column.set_clickable(gtk.TRUE)
        albumView.append_column(column)
        albumSelection = albumView.get_selection()
        albumSelection.connect('changed', self._albumSelectionHandler)
        self.reload()
        
    def reload(self):
        self._buildModel(None, env.shelf.getRootAlbum(), [])

    def _buildModel(self, parent, object, visited):
        for child in object.getChildren():
            if child.isAlbum():
                albumId = child.getId()
                iter = self._model.insert_before(parent, None)
                self._model.set_value(iter, self._COLUMN_ALBUM_ID, albumId)
                self._model.set_value(iter, self._COLUMN_TYPE, child.getType())
                if albumId not in visited:
                    self._model.set_value(iter, self._COLUMN_TAG, child.getTag())
                    self._buildModel(iter, child, visited + [albumId])
                else:
                    # TODO: Use "set_select_funtion" and add [...] as a child instead
                    self._model.set_value(iter, self._COLUMN_TAG, child.getTag() + "  [...]")

    def _albumSelectionHandler(self, selection):
        albumModel, iter = selection.get_selected()
        if iter:
            albumTag = albumModel.get_value(iter, self._COLUMN_TAG)
            self._source.set("album://" + albumTag)
