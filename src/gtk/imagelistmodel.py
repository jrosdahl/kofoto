import gtk

class ImageListModel(gtk.ListStore):
    _shelf = None
    _imageListColumns = None
    
    def __init__(self, shelf, imageListColumns):
        gtk.ListStore.__init__(self, *imageListColumns.types)
        self._shelf = shelf
        self._imageListColumns = imageListColumns

    def load(self, source, imageList):
        self._shelf.begin()
        self.clear()
        for image in imageList:
            iter = self.append()
            # To be refactored...
            self._setColumnValue(iter,"ImageId", image.getId()) 
            self._setColumnValue(iter,"Location", image.getLocation())
            attributeMap = image.getAttributeMap()
            for attribute in attributeMap:
                self._setColumnValue(iter,attribute, attributeMap[attribute])
        self._shelf.rollback()

    def _setColumnValue(self, iter, name, value):
        if  name in self._imageListColumns.map:
            columnNumber, visible = self._imageListColumns.map[name]
            self.set_value(iter, columnNumber, value)
