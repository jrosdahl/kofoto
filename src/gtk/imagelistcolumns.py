# TODO: This class should probably refactored and/or merged with the class ImageListModel.

import gtk
import gobject

class ImageListColumns:

    # The information in _attributeColumns should probably be read from a
    # configuration file where the user may specify what attributes that shall be
    # loaded and hence possible to show.
    _attributeColumns = [ ("Title",       gobject.TYPE_STRING),
                          ("Description", gobject.TYPE_STRING) ]

    types = [gobject.TYPE_INT, gobject.TYPE_STRING]
    
    map = { "ImageId"  : (0, gtk.TRUE),   # TODO: Don't mix imageId and location with the
            "Location" : (1, gtk.TRUE) }  # image attributes, else there might be name collisions.
        
    def __init__(self):
        for attribute, type in self._attributeColumns:
            self.map[attribute] = len(self.types), gtk.TRUE
            self.types.append(type)
            
    def getColNumber(self, columnName):
        if columnName in self.map:
            columnNumber, visible = self.map[columnName]
            return columnNumber
        else:
            return None
