import os
import gtk
import gobject
from kofoto.imagecache import *

from environment import env

class Images:
    _model = None
    sortedModel = None
    _title = ""
    _imageCache = None
    
    attributeNamesMap = {}

    COLUMN_IMAGE_ID = 0
    COLUMN_LOCATION = 1
    COLUMN_THUMBNAIL = 2
    COLUMN_VALID_LOCATION = 3
    COLUMN_VALID_CHECKSUM = 4
    COLUMN_IMAGE_OBJECT = 5
    
    _MANDATORY_COLUMNS_TYPE = [gobject.TYPE_INT,      # COLUMN_IMAGE_ID
                               gobject.TYPE_STRING,   # COLUMN_LOCATION
                               gtk.gdk.Pixbuf,        # COLUMN_THUMBNAIL
                               gobject.TYPE_BOOLEAN,  # COLUMN_VALID_LOCATION
                               gobject.TYPE_BOOLEAN,  # COLUMN_VALID_CHECKSUM 
                               gobject.TYPE_PYOBJECT] # COLUMN_IMAGE_OBJECT

    def __init__(self):
        env.shelf.begin()
        columnsType = self._MANDATORY_COLUMNS_TYPE
        for attributeName in env.shelf.getAllAttributeNames():
            self.attributeNamesMap[attributeName] = len(columnsType)
            columnsType.append(gobject.TYPE_STRING)
        self._model = gtk.ListStore(*columnsType)
        self.sortedModel = gtk.TreeModelSort(self._model)
        env.shelf.rollback()
        self._imageCache = ImageCache(env.imageCacheLocation)

    def loadImageList(self, imageList):
        env.shelf.begin()
        self._model.clear()
        self._thumbnailSize = 0
        for image in imageList:
            iter = self._model.append()
            self._model.set_value(iter, self.COLUMN_IMAGE_ID, image.getId()) 
            self._model.set_value(iter, self.COLUMN_LOCATION, image.getLocation())
            self._model.set_value(iter, self.COLUMN_IMAGE_OBJECT, image)
            for attribute, value in image.getAttributeMap().items():
                self._model.set_value(iter, self.attributeNamesMap[attribute], value)
            # TODO: update COLUMN_VALID_LOCATION
        env.shelf.rollback()

    def loadThumbnails(self, wantedThumbnailSize):
        env.shelf.begin()                    
        try:
            iter = self._model.get_iter_first()
            while iter:
                image = None
                image = self._model.get_value(iter, self.COLUMN_IMAGE_OBJECT)
                if wantedThumbnailSize > self._thumbnailSize:
                    # Load a new thumbnail from image cache.
                    largeEnoughSizes = [x for x in env.imageSizes
                                          if x >= wantedThumbnailSize]
                    if largeEnoughSizes:
                        sizeToUse = largeEnoughSizes[0]
                    else:
                        sizeToUse = wantedThumbnailSize
                    thumbnailLocation = self._imageCache.get(image, sizeToUse)
                    pixbuf = gtk.gdk.pixbuf_new_from_file(thumbnailLocation)
                else:
                    # Reuse current thumbnail
                    pixbuf = self._model.get_value(iter, self.COLUMN_THUMBNAIL)
                pixbuf = self.scalePixBuf(pixbuf, wantedThumbnailSize, wantedThumbnailSize)
                self._model.set_value(iter, self.COLUMN_THUMBNAIL, pixbuf)
                iter = self._model.iter_next(iter)
            self._thumbnailSize = wantedThumbnailSize
        except IOError:
            self._thumbnailSize = min(self._thumbnailSize, wantedThumbnailSize)
            # TODO: Show some kind of error icon?
            print "IOError"
        env.shelf.rollback()
        
    def scalePixBuf(self, pixbuf, maxWidth, maxHeight):
        scale = min(float(maxWidth) / pixbuf.get_width(), float(maxHeight) / pixbuf.get_height())
        scale = min(1, scale)
        if scale == 1:
            return pixbuf
        else:
            return pixbuf.scale_simple(pixbuf.get_width() * scale,
                                       pixbuf.get_height() * scale,
                                       gtk.gdk.INTERP_BILINEAR) # gtk.gdk.INTERP_HYPER is slower but gives better quality.
        
