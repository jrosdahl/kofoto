import os
import gtk
import gobject
import gc
from sets import *
from kofoto.imagecache import *
from kofoto.shelf import *

from environment import env

class ObjectCollection(object):

######################################################################
### Public

    def __init__(self):
        self.__columnsType = self.__DEFAULT_COLUMNS_TYPE
        self.__nonAttributesMap = {
            "id"       :(gobject.TYPE_INT,    self.COLUMN_OBJECT_ID, None,                 None),
            "location" :(gobject.TYPE_STRING, self.COLUMN_LOCATION,  None,                 None),
            "thumbnail":(gtk.gdk.Pixbuf,      self.COLUMN_THUMBNAIL, None,                 None),
            "album tag":(gobject.TYPE_STRING, self.COLUMN_ALBUM_TAG, self._albumTagEdited, None) }        
        for name in env.shelf.getAllAttributeNames():
            self.__addAttribute(name)
        self.__treeModel = gtk.ListStore(*self.__columnsType)

    def isReorderable(self):
        return gtk.FALSE

    def isSortable(self):
        return gtk.FALSE

    def isMutable(self):
        return gtk.FALSE

    def loadThumbnails(self):
        for row in self.__treeModel:
            objectId = row[self.COLUMN_OBJECT_ID]
            object = env.shelf.getObject(objectId)
            if object.isAlbum():
                pixbuf = env.albumIconPixbuf
            else:
                try:
                    thumbnailLocation = self.__imageCache.get(object, env.thumbnailSize)
                    pixbuf = gtk.gdk.pixbuf_new_from_file(thumbnailLocation)
                    # TODO Set and use COLUMN_VALID_LOCATION and COLUMN_VALID_CHECKSUM
                except IOError:
                    pixbuf = env.thumbnailErrorIconPixbuf
            row[self.COLUMN_THUMBNAIL] = pixbuf
            
    def getActions(self):
        return None
        # TODO implement

    def getNonAttributes(self):
        # TODO
        return self.__nonAttributesMap

    def getAttributes(self):
        # TODO
        return self.__attributesMap    

    def getModel(self):
        return self.__treeModel

    # TODO Which select methods is needed? Remove the others...

    def getSelectedIds(self):
        return self.__selectedImagesObjects.keys()
    
    def getSelectedObjects(self):
        return self.__selectedImagesObjects.values()

    def getSelectedRows(self):
        # TODO is row.path still valid a
        return self.__selectedImagesRows.values()

    def selectRow(self, row, sendSelectionChangedSignal=gtk.TRUE):
        objectId = row[ObjectCollection.COLUMN_OBJECT_ID]
        self.select(objectId, 
                    env.shelf.getObject(objectId),
                    row,
                    sendSelectionChangedSignal)

    def unSelectRow(self, row, sendSelectionChangedSignal=gtk.TRUE):
        objectId = row[ObjectCollection.COLUMN_OBJECT_ID]
        self.unSelect(objectId, sendSelectionChangedSignal)        
    
    def select(self, objectId, object, row, sendSelectionChangedSignal=gtk.TRUE):
        self.__selectedImagesObjects[objectId] = object
        self.__selectedImagesRows[objectId] = row
        if (sendSelectionChangedSignal):
            self.sendSelectionChangedSignal()

    def unSelect(self, objectId, sendSelectionChangedSignal=gtk.TRUE):
        del self.__selectedImagesObjects[objectId]
        del self.__selectedImagesRows[objectId]
        if (sendSelectionChangedSignal):
            self.sendSelectionChangedSignal()

    def unselectAll(self, sendSelectionChangedSignal=gtk.TRUE):
        self.__selectedImagesObjects = { }
        self.__selectedImagesRows = { }
        if (sendSelectionChangedSignal):
            self.sendSelectionChangedSignal()
            
    def sendSelectionChangedSignal(self):
        for callback in self.__selectionChangedCallbacks:
            callback.objectSelectionChanged()

    def registerSelectionChangedCallback(self, callback):
        self.__selectionChangedCallbacks.append(callback)

    def unregisterSelectionChangedCallback(self, callback):
        try:
            self.__selectionChangedCallbacks.remove(callback)
        except ValueError:
            pass
        
    # Hidden columns
    COLUMN_VALID_LOCATION = 0
    COLUMN_VALID_CHECKSUM = 1
    COLUMN_ROW_EDITABLE   = 2
    COLUMN_IS_ALBUM       = 3    
    
    # Columns visible to user
    COLUMN_OBJECT_ID      = 4
    COLUMN_LOCATION       = 5
    COLUMN_THUMBNAIL      = 6
    COLUMN_ALBUM_TAG      = 7

    # Content in data fields map and attributes map
    TYPE                 = 0
    COLUMN_NR            = 1
    EDITED_CALLBACK      = 2
    EDITED_CALLBACK_DATA = 3
   
        
######################################################################
### Only for subbclasses
        
    def _loadObjectList(self, objectList):
        for object in objectList:
            iter = self.__treeModel.append()
            self.__treeModel.set_value(iter, self.COLUMN_OBJECT_ID, object.getId())
            if object.isAlbum():
                self.__treeModel.set_value(iter, self.COLUMN_IS_ALBUM, gtk.TRUE)
                self.__treeModel.set_value(iter, self.COLUMN_ALBUM_TAG, object.getTag())
                self.__treeModel.set_value(iter, self.COLUMN_LOCATION, None)
            else:
                self.__treeModel.set_value(iter, self.COLUMN_IS_ALBUM, gtk.FALSE)
                self.__treeModel.set_value(iter, self.COLUMN_ALBUM_TAG, None)
                self.__treeModel.set_value(iter, self.COLUMN_LOCATION, object.getLocation())
                # TODO Set COLUMN_VALID_LOCATION and  COLUMN_VALID_CHECKSUM
            for attribute, value in object.getAttributeMap().items():
                column = self.__attributesMap[attribute][self.COLUMN_NR]
                self.__treeModel.set_value(iter, column, value)
            # TODO set COLUMN_ROW_EDITABLE?
        self.unselectAll()
        self.loadThumbnails()


###############################################################################
### Callback functions

    def _attributeEdited(self, renderer, path, value, column, attributeName):
        # TODO
        iter = self.__model.get_iter(path)
        oldValue = self.__model.get_value(iter, column)
        if not oldValue:
            oldValue = u""
        value = unicode(value, "utf-8")
        if oldValue != value:
            # TODO Show dialog and ask for confirmation?
            objectId = self.__model.get_value(iter, Objects.COLUMN_OBJECT_ID)
            object = env.shelf.getObject(objectId)
            object.setAttribute(attributeName, value)
            self.__model.set_value(iter, column, value)
            
    def _albumTagEdited(self, renderer, path, value, column, attributeName):
        # TODO        
        iter = self.__model.get_iter(path)
        oldValue = self.__model.get_value(iter, column)
        if not oldValue:
            oldValue = u""
        value = unicode(value, "utf-8")
        if oldValue != value:
            # TODO Show dialog and ask for confirmation?
            objectId = self.__model.get_value(iter, Objects.COLUMN_OBJECT_ID)
            object = env.shelf.getObject(objectId)
            object.setAttribute(attributeName, value)
            self.__model.set_value(iter, column, value)                
            
######################################################################
### Private
    
    __imageCache = ImageCache(env.imageCacheLocation)

    __DEFAULT_COLUMNS_TYPE = [ gobject.TYPE_BOOLEAN,  # COLUMN_VALID_LOCATION
                               gobject.TYPE_BOOLEAN,  # COLUMN_VALID_CHECKSUM
                               gobject.TYPE_BOOLEAN,  # COLUMN_ROW_EDITABLE
                               gobject.TYPE_BOOLEAN,  # COLUMN_IS_ALBUM
                               gobject.TYPE_INT,      # COLUMN_OBJECT_ID
                               gobject.TYPE_STRING,   # COLUMN_LOCATION
                               gtk.gdk.Pixbuf,        # COLUMN_THUMBNAIL
                               gobject.TYPE_STRING ]  # COLUMN_ALBUM_TAG
    __attributesMap = {}    
    __nonAttributesMap = None
    
    __selectedImagesObjects = {}
    __selectedImagesRows = {}
    __selectionChangedCallbacks = []
    
    def __addNonAttribute(self, name, type, editedCallback, editedCallbackData):
        self.__nonAttributesMap[name] = (type,
                                        len(self.__columnsType),
                                        editedCallback,
                                        editedCallbackData)
        self.__columnsType.append(type)

    def __addAttribute(self, name):
        self.__attributesMap[name] = (gobject.TYPE_STRING,
                                      len(self.__columnsType),
                                      self._attributeEdited,
                                      name)
        self.__columnsType.append(gobject.TYPE_STRING)

##    def rotate(self, button, angle):
##        # TODO: Make it possible for the user to configure if a rotation
##        # shall rotate the object or only update the orientation attribute?
##        for row in self._unsortedModel:
##            if row[self.COLUMN_OBJECT_ID] in self._selectedObjects:
##                object = env.shelf.getObject(row[self.COLUMN_OBJECT_ID])
##                if not object.isAlbum():
##                    location = object.getLocation().encode(env.codeset)
##                    # TODO: Read command from configuration file?
##                    command = "jpegtran -rotate %(angle)s -perfect -copy all -outfile %(location)s %(location)s" % { "angle":angle, "location":location}
##                    result = os.system(command)
##                    if result == 0:
##                        newHash = computeImageHash(location)
##                        object.setHash(newHash)
##                    else:
##                        print "failed to execute:", command
##
## Joel upptackte en bugg. (11009090) Det bor inte sta 100 nedan:
##
##                    self._loadThumbnail(100, row.iter, reload=gtk.TRUE)


