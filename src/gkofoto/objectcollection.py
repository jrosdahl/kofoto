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
        self.__objectSelection = ObjectSelection(self)
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
            u"albumtag" :(gobject.TYPE_STRING, self.COLUMN_ALBUM_TAG, self._albumTagEdited, self.COLUMN_ALBUM_TAG) }
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

    def getCutLabel(self):
        return "Cut reference"

    def getCopyLabel(self):
        return "Copy reference"

    def getPasteLabel(self):
        return "Paste reference"

    def getDeleteLabel(self):
        return "Delete reference"

    def getDestroyLabel(self):
        return "Destroy..."

    def getActions(self):
        return None
        # TODO implement

    def getObjectMetadataMap(self):
        return self.__objectMetadataMap

    def getModel(self):
        return self.__treeModel

    def getUnsortedModel(self):
        return self.__treeModel

    def convertToUnsortedRowNr(self, rowNr):
        return rowNr

    def convertFromUnsortedRowNr(self, unsortedRowNr):
        return unsortedRowNr

    def getObjectSelection(self):
        return self.__objectSelection

    def getDisabledFields(self):
        return self.__disabledFields

    def registerView(self, view):
        env.debug("Register view to object collection")
        self.__registeredViews.append(view)

    def unRegisterView(self, view):
        env.debug("Unregister view from object collection")
        self.__registeredViews.remove(view)

    def clear(self, freeze=True):
        env.debug("Clearing object collection")
        if freeze:
            self._freezeViews()
        self.__treeModel.clear()
        gc.collect()
        self.__nrOfAlbums = 0
        self.__nrOfImages = 0
        self._handleNrOfObjectsUpdate()
        self.__objectSelection.unselectAll()
        if freeze:
            self._thawViews()

    def cut(self, *foo):
        raise Exception("Error. Not allowed to cut objects into objectCollection.") # TODO

    def copy(self, *foo):
        env.clipboard.setObjects(self.__objectSelection.getSelectedObjects())

    def paste(self, *foo):
        raise Exception("Error. Not allowed to paste objects into objectCollection.") # TODO

    def delete(self, *foo):
        raise Exception("Error. Not allowed to delete objects from objectCollection.") # TODO

    def destroy(self, *foo):
        raise Exception("Destroy not implemented.") #TODO

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
        self._freezeViews()
        self.clear(False)
        self._insertObjectList(objectList)
        self._thawViews()
        env.exit("Object collection loading objects. (albums=" + str(self.__nrOfAlbums) + " images=" + str(self.__nrOfImages) + ")")

    def _insertObjectList(self, objectList, iterator=None):
        # Note that this methods does NOT update objectSelection.
        for obj in objectList:
            if iterator is None:
                iterator = self.__treeModel.append(None)
            else:
                iterator = self.__treeModel.insert_after(iterator, None)
            self.__treeModel.set_value(iterator, self.COLUMN_OBJECT_ID, obj.getId())
            if obj.isAlbum():
                self.__treeModel.set_value(iterator, self.COLUMN_IS_ALBUM, True)
                self.__treeModel.set_value(iterator, self.COLUMN_ALBUM_TAG, obj.getTag())
                self.__treeModel.set_value(iterator, self.COLUMN_LOCATION, None)
                self.__nrOfAlbums += 1
            else:
                self.__treeModel.set_value(iterator, self.COLUMN_IS_ALBUM, False)
                self.__treeModel.set_value(iterator, self.COLUMN_ALBUM_TAG, None)
                self.__treeModel.set_value(iterator, self.COLUMN_LOCATION, obj.getLocation())
                self.__nrOfImages += 1
                # TODO Set COLUMN_VALID_LOCATION and COLUMN_VALID_CHECKSUM
            for attribute, value in obj.getAttributeMap().items():
                column = self.__objectMetadataMap["@" + attribute][self.COLUMN_NR]
                self.__treeModel.set_value(iterator, column, value)
            self.__treeModel.set_value(iterator, self.COLUMN_ROW_EDITABLE, True)
            self.__loadThumbnail(self.__treeModel, iterator)
        self. _handleNrOfObjectsUpdate()

    def _handleNrOfObjectsUpdate(self):
        updatedDisabledFields = Set()
        if self.__nrOfAlbums == 0:
            updatedDisabledFields.add(u"albumtag")
        if self.__nrOfImages == 0:
            updatedDisabledFields.add(u"location")
        for view in self.__registeredViews:
            view.fieldsDisabled(updatedDisabledFields - self.__disabledFields)
            view.fieldsEnabled(self.__disabledFields - updatedDisabledFields)
        self.__disabledFields = updatedDisabledFields
        env.debug("The following fields are disabled: " + str(self.__disabledFields))

    def _getTreeModel(self):
        return self.__treeModel

    def _freezeViews(self):
        for view in self.__registeredViews:
            view.freeze()

    def _thawViews(self):
        for view in self.__registeredViews:
            view.thaw()


###############################################################################
### Callback functions

    def _attributeEdited(self, renderer, path, value, column, attributeName):
        model = self.getModel()
        columnNumber = self.__objectMetadataMap["@" + attributeName][self.COLUMN_NR]
        iterator = model.get_iter(path)
        oldValue = model.get_value(iterator, columnNumber)
        if not oldValue:
            oldValue = u""
        value = unicode(value, "utf-8")
        if oldValue != value:
            # TODO Show dialog and ask for confirmation?
            objectId = model.get_value(iterator, self.COLUMN_OBJECT_ID)
            obj = env.shelf.getObject(objectId)
            obj.setAttribute(attributeName, value)
            model.set_value(iterator, columnNumber, value)
            env.debug("Object attribute edited")

    def _albumTagEdited(self, renderer, path, value, column, columnNumber):
        model = self.getModel()
        iterator = model.get_iter(path)
        if model.get_value(iterator, self.COLUMN_IS_ALBUM):
            oldValue = model.get_value(iterator, columnNumber)
            if not oldValue:
                oldValue = u""
            value = unicode(value, "utf-8")
            if oldValue != value:
                # TODO Show dialog and ask for confirmation?
                objectId = model.get_value(iterator, self.COLUMN_OBJECT_ID)
                obj = env.shelf.getAlbum(objectId)
                obj.setTag(value)
                # TODO Handle invalid album tag?
                model.set_value(iterator, columnNumber, value)
                # TODO Update the album tree widget.
                env.debug("Album tag edited")
        else:
            # TODO Show dialog error box?
            print "Not allowed to set album tag on image"

    def rotate(self, widget, angle):
        for (rowNr, obj) in self.__objectSelection.getMap().items():
            if not obj.isAlbum():
                location = obj.getLocation().encode(env.codeset)
                if angle == 90:
                    commandString = env.rotateRightCommand
                else:
                    commandString = env.rotateLeftCommand
                command = commandString.encode(env.codeset) % { "location":location }
                result = os.system(command)
                if result == 0:
                    obj.contentChanged()
                    model = self.getUnsortedModel()
                    self.__loadThumbnail(model, model.get_iter(rowNr))
                else:
                    print "failed to execute:", command

    def open(self, widget, data):
        locations = ""
        for obj in self.__objectSelection.getSelectedObjects():
            if not obj.isAlbum():
                location = obj.getLocation()
                locations += location + " "
        if locations != "":
            command = env.openCommand % { "locations":locations }
            # GIMP does not seem to be able to open locations containing swedish
            # characters. I tried latin-1 and utf-8 without success.
            result = os.system(command + " &")
            if result != 0:
                print "failed to execute:", command

######################################################################
### Private

    def __addAttribute(self, name):
        self.__objectMetadataMap["@" + name] = (gobject.TYPE_STRING,
                                                len(self.__columnsType),
                                                self._attributeEdited,
                                                name)
        self.__columnsType.append(gobject.TYPE_STRING)

    def __loadThumbnail(self, model, iterator):
        objectId = model.get_value(iterator, self.COLUMN_OBJECT_ID)
        obj = env.shelf.getObject(objectId)
        if obj.isAlbum():
            pixbuf = env.albumIconPixbuf
        else:
            try:
                thumbnailLocation = env.imageCache.get(
                    obj, env.thumbnailSize[0], env.thumbnailSize[1])[0]
                pixbuf = gtk.gdk.pixbuf_new_from_file(thumbnailLocation.encode(env.codeset))
                # TODO Set and use COLUMN_VALID_LOCATION and COLUMN_VALID_CHECKSUM
            except IOError:
                pixbuf = env.unknownImageIconPixbuf
        model.set_value(iterator, self.COLUMN_THUMBNAIL, pixbuf)
