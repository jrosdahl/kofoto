import os
import gtk
import gobject
import gc
from sets import *
from kofoto.shelf import *
from menuhandler import *
from environment import env
from objectselection import *

class ObjectCollection(object):

######################################################################
### Public

    def __init__(self):
        env.debug("Init ObjectCollection")
        self.__objectSelection = ObjectSelection()
        self.__registeredViews = []
        self.__disabledFields = Set()
        self.__columnsType = [ gobject.TYPE_BOOLEAN,  # COLUMN_VALID_LOCATION
                               gobject.TYPE_BOOLEAN,  # COLUMN_VALID_CHECKSUM
                               gobject.TYPE_BOOLEAN,  # COLUMN_ROW_EDITABLE
                               gobject.TYPE_BOOLEAN,  # COLUMN_IS_ALBUM
                               gobject.TYPE_INT,      # COLUMN_OBJECT_ID
                               gobject.TYPE_STRING,   # COLUMN_LOCATION
                               gtk.gdk.Pixbuf,        # COLUMN_THUMBNAIL
                               gobject.TYPE_STRING ]  # COLUMN_ALBUM_TAG
        self.__objectMetadataMap = {
            u"id"       :(gobject.TYPE_INT,    self.COLUMN_OBJECT_ID, None,                 None),
            u"location" :(gobject.TYPE_STRING, self.COLUMN_LOCATION,  None,                 None),
            u"thumbnail":(gtk.gdk.Pixbuf,      self.COLUMN_THUMBNAIL, None,                 None),
            u"albumTag" :(gobject.TYPE_STRING, self.COLUMN_ALBUM_TAG, self._albumTagEdited, self.COLUMN_ALBUM_TAG) }
        for name in env.shelf.getAllAttributeNames():
            self.__addAttribute(name)
        self.__treeModel = gtk.ListStore(*self.__columnsType)


    # Return true if the objects has a defined order and may
    # be reordered. An object that is reorderable is not
    # allowed to also be sortable.
    def isReorderable(self):
        return False

    # Return true if the objects may be sorted.
    def isSortable(self):
        return False

    # Return true if objects may be added and removed from the collection.
    def isMutable(self):
        return False

    def loadThumbnails(self):
        env.enter("Object collection loading thumbnails.")
        for row in self.__treeModel:
            objectId = row[self.COLUMN_OBJECT_ID]
            object = env.shelf.getObject(objectId)
            if object.isAlbum():
                pixbuf = env.albumIconPixbuf
            else:
                try:
                    thumbnailLocation = env.imageCache.get(
                        object, env.thumbnailSize[0], env.thumbnailSize[1])
                    pixbuf = gtk.gdk.pixbuf_new_from_file(thumbnailLocation.encode(env.codeset))
                    # TODO Set and use COLUMN_VALID_LOCATION and COLUMN_VALID_CHECKSUM
                except IOError:
                    pixbuf = env.thumbnailErrorIconPixbuf
            row[self.COLUMN_THUMBNAIL] = pixbuf
        env.exit("Object collection loading thumbnails.")            
            
    def getActions(self):
        return None
        # TODO implement

    def getObjectMetadataMap(self):
        return self.__objectMetadataMap

    def getModel(self):
        return self.__treeModel

    def getObjectSelection(self):
        return self.__objectSelection
        
    def getDisabledFields(self):
        return self.__disabledFields
            
    def registerView(self, view):
        env.debug("Register view to object collection")
        self.__registeredViews.append(view)
        self.__objectSelection.addChangedCallback(view.importSelection)

    def unRegisterView(self, view):
        env.debug("Unregister view from object collection")
        self.__registeredViews.remove(view)
        self.__objectSelection.removeChangedCallback(view.importSelection)        

    def clear(self):
        env.debug("Clearing object collection")
        for view in self.__registeredViews:
            view.freeze()
        self.__treeModel.clear()
        gc.collect()
        for view in self.__registeredViews:
            view.thaw()

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

    # Content in objectMetadata fields
    TYPE                 = 0
    COLUMN_NR            = 1
    EDITED_CALLBACK      = 2
    EDITED_CALLBACK_DATA = 3

    
        
######################################################################
### Only for subbclasses

    def _getRegisteredViews(self):
        return self.__registeredViews

    def _loadObjectList(self, objectList):
        env.enter("Object collection loading objects.")
        for view in self.__registeredViews:
            view.freeze()
        self.__treeModel.clear()
        gc.collect()
        nrOfAlbums = 0
        nrOfImages = 0
        for object in objectList:
            iter = self.__treeModel.append()
            self.__treeModel.set_value(iter, self.COLUMN_OBJECT_ID, object.getId())
            if object.isAlbum():
                self.__treeModel.set_value(iter, self.COLUMN_IS_ALBUM, True)
                self.__treeModel.set_value(iter, self.COLUMN_ALBUM_TAG, object.getTag())
                self.__treeModel.set_value(iter, self.COLUMN_LOCATION, None)
                nrOfAlbums += 1
            else:
                self.__treeModel.set_value(iter, self.COLUMN_IS_ALBUM, False)
                self.__treeModel.set_value(iter, self.COLUMN_ALBUM_TAG, None)
                self.__treeModel.set_value(iter, self.COLUMN_LOCATION, object.getLocation())
                nrOfImages += 1
                # TODO Set COLUMN_VALID_LOCATION and COLUMN_VALID_CHECKSUM
            for attribute, value in object.getAttributeMap().items():
                column = self.__objectMetadataMap["@" + attribute][self.COLUMN_NR]
                self.__treeModel.set_value(iter, column, value)
            self.__treeModel.set_value(iter, self.COLUMN_ROW_EDITABLE, True)
        self.loadThumbnails()
        updatedDisabledFields = Set()
        if nrOfAlbums == 0:
            updatedDisabledFields.add(u"albumTag")
        if nrOfImages == 0:
            updatedDisabledFields.add(u"location")
        for view in self.__registeredViews:
            view.fieldsDisabled(updatedDisabledFields - self.__disabledFields)
            view.fieldsEnabled(self.__disabledFields - updatedDisabledFields)
        self.__disabledFields = updatedDisabledFields
        env.debug("The following fields are disabled: " + str(self.__disabledFields))
        self.__objectSelection.unselectAll()
        for view in self.__registeredViews:
            view.thaw()
        env.exit("Object collection loading objects. (albums=" + str(nrOfAlbums) + " images=" + str(nrOfImages) + ")")

    def _getTreeModel(self):
        return self.__treeModel

###############################################################################
### Callback functions

    def _attributeEdited(self, renderer, path, value, column, attributeName):
        model = self.getModel()
        columnNumber = self.__objectMetadataMap["@" + attributeName][self.COLUMN_NR]
        iter = model.get_iter(path)
        oldValue = model.get_value(iter, columnNumber)
        if not oldValue:
            oldValue = u""
        value = unicode(value, "utf-8")
        if oldValue != value:
            # TODO Show dialog and ask for confirmation?
            objectId = model.get_value(iter, self.COLUMN_OBJECT_ID)
            object = env.shelf.getObject(objectId)
            object.setAttribute(attributeName, value)
            model.set_value(iter, columnNumber, value)
            env.debug("Object attribute edited")
            
    def _albumTagEdited(self, renderer, path, value, column, columnNumber):
        model = self.getModel()
        iter = model.get_iter(path)
        if model.get_value(iter, self.COLUMN_IS_ALBUM):
            oldValue = model.get_value(iter, columnNumber)
            if not oldValue:
                oldValue = u""
            value = unicode(value, "utf-8")
            if oldValue != value:
                # TODO Show dialog and ask for confirmation?
                objectId = model.get_value(iter, self.COLUMN_OBJECT_ID)
                object = env.shelf.getAlbum(objectId)
                object.setTag(value)
                # TODO Handle invalid album tag?
                model.set_value(iter, columnNumber, value)
                # TODO Update the album tree widget.
                env.debug("Album tag edited")                
        else:
            # TODO Show dialog error box?
            print "Not allowed to set album tag on image"
        
            
######################################################################
### Private
    
    def __addAttribute(self, name):
        self.__objectMetadataMap["@" + name] = (gobject.TYPE_STRING,
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
##                        object.contentChanged()
##                    else:
##                        print "failed to execute:", command
##
## Joel upptackte en bugg. (11009090) Det bor inte sta 100 nedan:
##
##                    self._loadThumbnail(100, row.iter, reload=True)
