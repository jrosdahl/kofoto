import os
import gtk
import gobject
import gc
from sets import *
from kofoto.imagecache import *
from kofoto.shelf import *

from environment import env
from mysortedmodel import *

class Objects:
    _unsortedModel = None
    model = None
    _title = ""
    _imageCache = None
    _sortColumn = None
    albumsInList = gtk.FALSE    
    attributeNamesMap = {}

    COLUMN_OBJECT_ID      = 0
    COLUMN_LOCATION       = 1
    COLUMN_THUMBNAIL      = 2
    COLUMN_VALID_LOCATION = 3
    COLUMN_VALID_CHECKSUM = 4
    COLUMN_ROW_EDITABLE   = 5
    COLUMN_IS_ALBUM       = 6
    COLUMN_ALBUM_TAG      = 7
    
    _MANDATORY_COLUMNS_TYPE = [gobject.TYPE_INT,      # COLUMN_OBJECT_ID
                               gobject.TYPE_STRING,   # COLUMN_LOCATION
                               gtk.gdk.Pixbuf,        # COLUMN_THUMBNAIL
                               gobject.TYPE_BOOLEAN,  # COLUMN_VALID_LOCATION
                               gobject.TYPE_BOOLEAN,  # COLUMN_VALID_CHECKSUM
                               gobject.TYPE_BOOLEAN,  # COLUMN_ROW_EDITABLE
                               gobject.TYPE_BOOLEAN,  # COLUMN_IS_ALBUM
                               gobject.TYPE_STRING]   # COLUMN_ALBUM_TAG
    

    def __init__(self, selectedObjects):
        self._selectedObjects = selectedObjects
        self._imageCache = ImageCache(env.imageCacheLocation)
        self._loadModel()

    def reloadModel(self):
        self._loadModel()
        env.controller.newObjectModelLoaded()

    def _loadModel(self):
        columnsType = self._MANDATORY_COLUMNS_TYPE
        allAttributeNames = Set(env.shelf.getAllAttributeNames())
        allAttributeNames = allAttributeNames | Set(env.defaultTableViewColumns)
        allAttributeNames = allAttributeNames | Set([env.defaultSortColumn])
        for attributeName in allAttributeNames:
            self.attributeNamesMap[attributeName] = len(columnsType)
            columnsType.append(gobject.TYPE_STRING)
        self._unsortedModel = gtk.ListStore(*columnsType)
        self.model = MySortedModel(self._unsortedModel)

    def loadObjectList(self, objectList):
        self.albumsInList = gtk.FALSE
        self._unsortedModel.clear()
        gc.collect()
        for object in objectList:
            if object.isAlbum():
                self.albumsInList = gtk.TRUE
            iter = self._unsortedModel.append()
            self._unsortedModel.set_value(iter, self.COLUMN_OBJECT_ID, object.getId())
            if object.isAlbum():
                self._unsortedModel.set_value(iter, self.COLUMN_IS_ALBUM, gtk.TRUE)
                self._unsortedModel.set_value(iter, self.COLUMN_ALBUM_TAG, object.getTag())
            else:
                self._unsortedModel.set_value(iter, self.COLUMN_LOCATION, object.getLocation())
                self._unsortedModel.set_value(iter, self.COLUMN_IS_ALBUM, gtk.FALSE)
            self._unsortedModel.set_value(iter, self.COLUMN_ROW_EDITABLE, gtk.TRUE)
            for attribute, value in object.getAttributeMap().items():
                self._unsortedModel.set_value(iter, self.attributeNamesMap[attribute], value)
                # TODO: update COLUMN_VALID_LOCATION

    def loadThumbnails(self):
        iter = self._unsortedModel.get_iter_first()
        while iter:
            self._loadThumbnail(iter)
            iter = self._unsortedModel.iter_next(iter)

    def _loadThumbnail(self, iter, reload=gtk.FALSE):
        try:
            objectId = self._unsortedModel.get_value(iter, self.COLUMN_OBJECT_ID)
            object = env.shelf.getObject(objectId)
            if object.isAlbum():
                pixbuf = env.albumIconPixbuf
            else:
                thumbnailLocation = self._imageCache.get(object, env.thumbnailSize[0], env.thumbnailSize[1])
                pixbuf = gtk.gdk.pixbuf_new_from_file(thumbnailLocation.encode(env.codeset))
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

    
    def unregisterObjects(self, *foo):
        # TODO Show dialog and ask for confirmation!
        objectIdList = list(self._selectedObjects)
        self._selectedObjects.clear()
        for row in self._unsortedModel:
            if row[self.COLUMN_OBJECT_ID] in objectIdList:
                env.shelf.deleteObject(row[self.COLUMN_OBJECT_ID])
                self._unsortedModel.remove(row.iter)

    def rotate(self, button, angle):
        # TODO: Make it possible for the user to configure if a rotation
        # shall rotate the object or only update the orientation attribute?
        for row in self._unsortedModel:
            if row[self.COLUMN_OBJECT_ID] in self._selectedObjects:
                object = env.shelf.getObject(row[self.COLUMN_OBJECT_ID])
                if not object.isAlbum():
                    location = object.getLocation().encode(env.codeset)
                    # TODO: Read command from configuration file?
                    command = "jpegtran -rotate %(angle)s -perfect -copy all -outfile %(location)s %(location)s" % { "angle":angle, "location":location}
                    result = os.system(command)
                    if result == 0:
                        object.contentChanged()
                    else:
                        print "failed to execute:", command
                    self._loadThumbnail(row.iter, reload=gtk.TRUE)

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
            result = cmp(model.get_value(iterA, self.COLUMN_OBJECT_ID),
                         model.get_value(iterB, self.COLUMN_OBJECT_ID))
        return result
