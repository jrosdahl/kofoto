import gtk
import gobject
import gtk

from environment import env

class Albums:
    _COLUMN_ALBUM_ID  = 0
    _COLUMN_TAG       = 1
    _COLUMN_TYPE      = 2
    _COLUMN_OBJECT    = 3

    _model = None
    
    def __init__(self):
        self._model = gtk.TreeStore(gobject.TYPE_INT,      # ALBUM_ID
                                    gobject.TYPE_STRING,   # TAG
                                    gobject.TYPE_STRING,   # TYPE
                                    gobject.TYPE_PYOBJECT) # OBJECT
        albumView = env.widgets["albumView"]
        albumView.set_model(self._model)
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Albums", renderer, text=self._COLUMN_TAG)
        column.set_clickable(gtk.TRUE)
        albumView.append_column(column)
        albumSelection = albumView.get_selection()
        albumSelection.connect('changed', self._albumSelectionHandler)
        self.reload()
        
    def reload(self):
        env.shelf.begin()
        self._buildModel(None, env.shelf.getRootAlbum(), [])
        env.shelf.rollback()

    def _buildModel(self, parent, object, visited):
        for child in object.getChildren():
            if child.isAlbum():
                albumId = child.getId()
                iter = self._model.insert_before(parent, None)
                self._model.set_value(iter, self._COLUMN_ALBUM_ID, albumId)
                self._model.set_value(iter, self._COLUMN_TYPE, child.getType())
                self._model.set_value(iter, self._COLUMN_OBJECT, child)
                if albumId not in visited:
                    self._model.set_value(iter, self._COLUMN_TAG, child.getTag())
                    self._buildModel(iter, child, visited + [albumId])
                else:
                    # TODO: Use "set_select_funtion" and add [...] as a child instead
                    self._model.set_value(iter, self._COLUMN_TAG, child.getTag() + "  [...]")

    def _albumSelectionHandler(self, selection):
        env.shelf.begin()
        albumModel, iter = selection.get_selected()
        if iter:
            album = albumModel.get_value(iter, self._COLUMN_OBJECT)
            albumTag =  album.getTag()
            selectedImages = []
            for child in album.getChildren():
                if not child.isAlbum():
                    selectedImages.append(child)
        env.shelf.rollback()
        if iter:
            env.controller.loadImages(selectedImages, "Album: " + albumTag)
