import gtk
import gobject

class ImageListModel(gtk.ListStore):
    _shelf = None

    attributeNamesMap = {}

    COLUMN_IMAGE_ID = 0
    COLUMN_LOCATION = 1
    COLUMN_THUMBNAIL = 2

    _MANDATORY_COLUMNS_TYPE = [gobject.TYPE_INT, gobject.TYPE_STRING, gtk.gdk.Pixbuf]

    imageList = None
    source = None
    
    def __init__(self, shelf):
        shelf.begin()
        self._shelf = shelf
        gtk.ListStore.__init__(self, *self._loadColumns())
        shelf.rollback()

    def _loadColumns(self):
        columnsType = self._MANDATORY_COLUMNS_TYPE
        for attributeName in self._shelf.getAllAttributeNames():
            self.attributeNamesMap[attributeName] = len(columnsType)
            columnsType.append(gobject.TYPE_STRING)
        return columnsType

    def loadImageList(self, source, imageList):
        self.imageList = imageList
        self.source = source
        self.reloadImageData()

    def reloadImageData(self):
        self._shelf.begin()
        self.clear()
        for image in self.imageList:
            iter = self.append()
            self.set_value(iter, self.COLUMN_IMAGE_ID, image.getId()) 
            self.set_value(iter, self.COLUMN_LOCATION, image.getLocation())
            # TODO: self.set_value(iter, COLUMN_THUMBNAIL, ....)
            for attribute, value in image.getAttributeMap().items():
                self.set_value(iter, self.attributeNamesMap[attribute], value)
        self._shelf.rollback()
 
 
