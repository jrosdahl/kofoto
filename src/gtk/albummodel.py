import gtk
import gobject
from gtk import TRUE, FALSE

class AlbumModel(gtk.TreeStore):
    COLUMN_ALBUM_ID  = 0
    COLUMN_TAG       = 1
    COLUMN_TYPE      = 2
    COLUMN_OBJECT    = 3

    _CYCLE_DETECTION_LEVEL = 10  # read from configuration file?
    _shelf = None
    _ignoredAlbums = FALSE
    
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
        self._ignoredAlbums = FALSE
        self._buildModel(None, self._shelf.getRootAlbum(), 0, {})
        self._shelf.rollback()
        if self._ignoredAlbums == TRUE:
            # TODO: Show warning in pop up window instead of printing to stdout
            print "Max album depth reached for cycle detection. All albums not showed"

    def _buildModel(self, parent, object, level, visited):
        level += 1
        for child in object.getChildren():
            if child.isAlbum():
                albumId = child.getId()
                if level > self._CYCLE_DETECTION_LEVEL and albumId in visited:
                    # Too depth cycle detected
                    self._ignoredAlbums = TRUE
                else:
                    # Add album to model
                    iter = self.insert_after(parent, None)
                    self.set_value(iter, self.COLUMN_ALBUM_ID, albumId)
                    self.set_value(iter, self.COLUMN_TAG, child.getTag())
                    self.set_value(iter, self.COLUMN_TYPE, child.getType())
                    self.set_value(iter, self.COLUMN_OBJECT, child)
                    visited[albumId] = 1
                    print "Adding: ", child.getTag()
                    self._buildModel(iter, child, level, visited)

