import os
import gtk
import gobject
import gc
from sets import *
from kofoto.imagecache import *
from kofoto.shelf import *

from environment import env
from mysortedmodel import *

class Images:
    _unsortedModel = None
    model = None
    _title = ""
    _imageCache = None
    _sortColumn = None
    
    attributeNamesMap = {}

    COLUMN_IMAGE_ID = 0
    COLUMN_LOCATION = 1
    COLUMN_THUMBNAIL = 2
    COLUMN_VALID_LOCATION = 3
    COLUMN_VALID_CHECKSUM = 4
    COLUMN_ROW_EDITABLE   = 5
    
    _MANDATORY_COLUMNS_TYPE = [gobject.TYPE_INT,      # COLUMN_IMAGE_ID
                               gobject.TYPE_STRING,   # COLUMN_LOCATION
                               gtk.gdk.Pixbuf,        # COLUMN_THUMBNAIL
                               gobject.TYPE_BOOLEAN,  # COLUMN_VALID_LOCATION
                               gobject.TYPE_BOOLEAN,  # COLUMN_VALID_CHECKSUM
                               gobject.TYPE_BOOLEAN]  # COLUMN_ROW_EDITABLE
    

    def __init__(self, selectedImages):
        self._selectedImages = selectedImages
        self._imageCache = ImageCache(env.imageCacheLocation)
        self._loadModel()

    def reloadModel(self):
        self._loadModel()
        env.controller.newImageModelLoaded()

    def _loadModel(self):
        columnsType = self._MANDATORY_COLUMNS_TYPE
        allAttributeNames = Set(env.shelf.getAllAttributeNames())
        allAttributeNames = allAttributeNames | Set(env.defaultTableViewColumns)
        allAttributeNames = allAttributeNames | Set(env.defaultThumbnailViewColumns)
        allAttributeNames = allAttributeNames | Set([env.defaultSortColumn])
        for attributeName in allAttributeNames:
            self.attributeNamesMap[attributeName] = len(columnsType)
            columnsType.append(gobject.TYPE_STRING)
        self._unsortedModel = gtk.ListStore(*columnsType)
        self.model = MySortedModel(self._unsortedModel)

    def loadImageList(self, imageList):
        self._unsortedModel.clear()
        gc.collect()
        self._thumbnailSize = 0
        for image in imageList:
            iter = self._unsortedModel.append()
            self._unsortedModel.set_value(iter, self.COLUMN_IMAGE_ID, image.getId()) 
            self._unsortedModel.set_value(iter, self.COLUMN_LOCATION, image.getLocation())
            self._unsortedModel.set_value(iter, self.COLUMN_ROW_EDITABLE, gtk.TRUE)
            for attribute, value in image.getAttributeMap().items():
                self._unsortedModel.set_value(iter, self.attributeNamesMap[attribute], value)
                # TODO: update COLUMN_VALID_LOCATION

    def loadThumbnails(self, wantedThumbnailSize):
        iter = self._unsortedModel.get_iter_first()
        while iter:
            self._loadThumbnail(wantedThumbnailSize, iter)
            iter = self._unsortedModel.iter_next(iter)
        self._thumbnailSize = wantedThumbnailSize

    def _loadThumbnail(self, wantedThumbnailSize, iter, reload=gtk.FALSE):
        # Reload was used when thumbnail has been invalid and can not be reused.
        # It is probably better to remove the "reload" parameter and instead
        # remove thumbnails from the not-yet-existing-cache when needed.
        try:
            imageId = self._unsortedModel.get_value(iter, self.COLUMN_IMAGE_ID)
            image = env.shelf.getImage(imageId)
            thumbnailLocation = self._imageCache.get(image, wantedThumbnailSize)
            pixbuf = gtk.gdk.pixbuf_new_from_file(thumbnailLocation)
            self._unsortedModel.set_value(iter, self.COLUMN_THUMBNAIL, pixbuf)
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
        # TODO Show dialog and ask for confirmation!
        imageIdList = list(self._selectedImages)
        self._selectedImages.clear()
        for row in self._unsortedModel:
            if row[self.COLUMN_IMAGE_ID] in imageIdList:
                env.shelf.deleteImage(row[self.COLUMN_IMAGE_ID])
                self._unsortedModel.remove(row.iter)

    def rotate(self, button, angle):
        # TODO: Make it possible for the user to configure if a rotation
        # shall rotate the image or only update the orientation attribute?
        for row in self._unsortedModel:
            if row[self.COLUMN_IMAGE_ID] in self._selectedImages:
                image = env.shelf.getImage(row[self.COLUMN_IMAGE_ID])
                location = image.getLocation().encode(env.codeset)
                # TODO: Read command from configuration file?
                command = "jpegtran -rotate %s -perfect -copy all -outfile %s %s" % (angle, location, location)
                result = os.system(command)
                if result == 0:
                    newHash = computeImageHash(location)
                    image.setHash(newHash)
                else:
                    print "failed to execute:", command
                self._loadThumbnail(100, row.iter, reload=gtk.TRUE)

    def setSortOrder(self, widget, order):
        self._sortOrder = order
        if self._sortColumn:
            self.sortByColumn(None, self._sortColumn)

    def sortByColumn(self, menuItem, column):
        self.model.set_sort_column_id(column, self._sortOrder)
        self.model.set_sort_func(column, self._sort_func, column)
        self._sortColumn = column

    def _sort_func(self, model, iterA, iterB, column):
        valueA = model.get_value(iterA, column)
        valueB = model.get_value(iterB, column)
        try:
            result = cmp(float(valueA), float(valueB))
        except (ValueError, TypeError):
            result = cmp(valueA, valueB)
        if result == 0:
            result = cmp(model.get_value(iterA, self.COLUMN_IMAGE_ID),
                         model.get_value(iterB, self.COLUMN_IMAGE_ID))
        return result
