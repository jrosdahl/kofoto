import os
import gtk
import gobject
import gc
from kofoto.imagecache import *
from kofoto.shelf import *

from environment import env

class Images:
    model = None
    sortedModel = None
    _title = ""
    _imageCache = None
    
    attributeNamesMap = {}

    COLUMN_IMAGE_ID = 0
    COLUMN_LOCATION = 1
    COLUMN_THUMBNAIL = 2
    COLUMN_VALID_LOCATION = 3
    COLUMN_VALID_CHECKSUM = 4
    
    _MANDATORY_COLUMNS_TYPE = [gobject.TYPE_INT,      # COLUMN_IMAGE_ID
                               gobject.TYPE_STRING,   # COLUMN_LOCATION
                               gtk.gdk.Pixbuf,        # COLUMN_THUMBNAIL
                               gobject.TYPE_BOOLEAN,  # COLUMN_VALID_LOCATION
                               gobject.TYPE_BOOLEAN]  # COLUMN_VALID_CHECKSUM 

    def __init__(self, selectedImages):
        self._selectedImages = selectedImages
        self._imageCache = ImageCache(env.imageCacheLocation)
        self._loadModel()

    def reloadModel(self):
        self._loadModel()
        env.controller.newImageModelLoaded()

    def _loadModel(self):
        columnsType = self._MANDATORY_COLUMNS_TYPE
        for attributeName in env.shelf.getAllAttributeNames():
            self.attributeNamesMap[attributeName] = len(columnsType)
            columnsType.append(gobject.TYPE_STRING)
        self.model = gtk.ListStore(*columnsType)
        # self.sortedModel = gtk.TreeModelSort(self.model)
        # Sorting disabled...
        self.sortedModel = self.model
        
    def loadImageList(self, imageList):
        self.model.clear()
        gc.collect()
        self._thumbnailSize = 0
        for image in imageList:
            iter = self.model.append()
            self.model.set_value(iter, self.COLUMN_IMAGE_ID, image.getId()) 
            self.model.set_value(iter, self.COLUMN_LOCATION, image.getLocation())
            for attribute, value in image.getAttributeMap().items():
                self.model.set_value(iter, self.attributeNamesMap[attribute], value)
                # TODO: update COLUMN_VALID_LOCATION

    def loadThumbnails(self, wantedThumbnailSize):
        iter = self.model.get_iter_first()
        while iter:
            self._loadThumbnail(wantedThumbnailSize, iter)
            iter = self.model.iter_next(iter)
        self._thumbnailSize = wantedThumbnailSize

    def _loadThumbnail(self, wantedThumbnailSize, iter, reload=gtk.FALSE):
        try:
            imageId = self.model.get_value(iter, self.COLUMN_IMAGE_ID)
            image = env.shelf.getImage(imageId)
            if wantedThumbnailSize > self._thumbnailSize or reload:
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
                pixbuf = self.model.get_value(iter, self.COLUMN_THUMBNAIL)
            pixbuf = self.scalePixBuf(pixbuf, wantedThumbnailSize, wantedThumbnailSize)
            self.model.set_value(iter, self.COLUMN_THUMBNAIL, pixbuf)
        except IOError:
            # TODO: Show some kind of error icon?
            print "IOError"
        
        
    def scalePixBuf(self, pixbuf, maxWidth, maxHeight):
        scale = min(float(maxWidth) / pixbuf.get_width(), float(maxHeight) / pixbuf.get_height())
        scale = min(1, scale)
        if scale == 1:
            return pixbuf
        else:
            return pixbuf.scale_simple(pixbuf.get_width() * scale,
                                       pixbuf.get_height() * scale,
                                       gtk.gdk.INTERP_BILINEAR) # gtk.gdk.INTERP_HYPER is slower but gives better quality.

    
    def unregisterImages(self, *foo):
        imageIdList = list(self._selectedImages)
        self._selectedImages.clear()
        for row in self.model:
            if row[self.COLUMN_IMAGE_ID] in imageIdList:
                env.shelf.deleteImage(row[self.COLUMN_IMAGE_ID])
                self.model.remove(row.iter)

    def rotate(self, button, angle):
        # TODO: Make it possible for the user to configure if a rotation
        # shall rotate the image or only update the orientation attribute?
        for row in self.model:
            if row[self.COLUMN_IMAGE_ID] in self._selectedImages:
                image = env.shelf.getImage(row[self.COLUMN_IMAGE_ID])
                location = image.getLocation()
                # TODO: Read command from configuration file?
                command = "jpegtran -rotate %s -perfect -copy all -outfile %s %s" % (angle, location, location)
                result = os.system(command)
                if result == 0:
                    newHash = computeImageHash(location)
                    image.setHash(newHash)
                else:
                    print "failed to execute:", command
                self._loadThumbnail(100, row.iter, reload=gtk.TRUE)
                
