import gtk
import gobject
from gtk import TRUE, FALSE

class AlbumModel(gtk.TreeStore):
    COLUMN_ALBUM_ID  = 0
    COLUMN_TAG       = 1
    COLUMN_TYPE      = 2
    COLUMN_OBJECT    = 3
    
    _shelf = None
    
    def __init__(self, shelf):
        gtk.TreeStore.__init__(self,
                               gobject.TYPE_INT,      # ALBUM_ID
                               gobject.TYPE_STRING,   # TAG
                               gobject.TYPE_STRING,   # TYPE
                               gobject.TYPE_PYOBJECT) # OBJECT
        self._shelf = shelf
        self.reload()
        
    def reload(self):
        self._shelf.begin()
        self._buildModel(None, self._shelf.getRootAlbum(), 0, [])
        self._shelf.rollback()

    def _buildModel(self, parent, object, level, visited):
        for child in object.getChildren():
            if child.isAlbum():
                albumId = child.getId()
                iter = self.insert_before(parent, None)
                self.set_value(iter, self.COLUMN_ALBUM_ID, albumId)
                self.set_value(iter, self.COLUMN_TYPE, child.getType())
                self.set_value(iter, self.COLUMN_OBJECT, child)
                if albumId not in visited:
                    self.set_value(iter, self.COLUMN_TAG, child.getTag())
                    self._buildModel(iter, child, level, visited + [albumId])
                else:
                    self.set_value(iter, self.COLUMN_TAG, child.getTag() + "  [...]")
        return FALSE

