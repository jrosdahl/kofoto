import os
import gtk
import gobject
import gc
from sets import Set
from kofoto.gkofoto.environment import env
from kofoto.gkofoto.objectselection import ObjectSelection
from kofoto.gkofoto.albumdialog import AlbumDialog
from kofoto.gkofoto.registerimagesdialog import RegisterImagesDialog
from kofoto.gkofoto.imageversionsdialog import ImageVersionsDialog
from kofoto.gkofoto.registerimageversionsdialog import \
    RegisterImageVersionsDialog
from kofoto.gkofoto.duplicateandopenimagedialog import \
    DuplicateAndOpenImageDialog

class ObjectCollection(object):

######################################################################
### Public

    def __init__(self):
        env.debug("Init ObjectCollection")
        self.__objectSelection = ObjectSelection(self)
        self.__insertionWorkerTag = None
        self.__registeredViews = []
        self.__disabledFields = Set()
        self.__rowInsertedCallbacks = []
        self.__columnsType = [ gobject.TYPE_BOOLEAN,  # COLUMN_VALID_LOCATION
                               gobject.TYPE_BOOLEAN,  # COLUMN_VALID_CHECKSUM
                               gobject.TYPE_BOOLEAN,  # COLUMN_ROW_EDITABLE
                               gobject.TYPE_BOOLEAN,  # COLUMN_IS_ALBUM
                               gobject.TYPE_INT,      # COLUMN_OBJECT_ID
                               gobject.TYPE_STRING,   # COLUMN_LOCATION
                               gtk.gdk.Pixbuf,        # COLUMN_THUMBNAIL
                               gobject.TYPE_STRING,   # COLUMN_IMAGE_VERSIONS
                               gobject.TYPE_STRING ]  # COLUMN_ALBUM_TAG
        self.__objectMetadataMap = {
            u"id"       :(gobject.TYPE_INT,    self.COLUMN_OBJECT_ID, None,                 None),
            u"location" :(gobject.TYPE_STRING, self.COLUMN_LOCATION,  None,                 None),
            u"thumbnail":(gtk.gdk.Pixbuf,      self.COLUMN_THUMBNAIL, None,                 None),
            u"albumtag" :(gobject.TYPE_STRING, self.COLUMN_ALBUM_TAG, self._albumTagEdited, self.COLUMN_ALBUM_TAG),
            u"versions" :(gobject.TYPE_STRING, self.COLUMN_IMAGE_VERSIONS, None,            None),
            }
        for name in env.shelf.getAllAttributeNames():
            self.__addAttribute(name)
        self.__treeModel = gtk.ListStore(*self.__columnsType)
        self.__frozen = False
        self.__nrOfAlbums = 0
        self.__nrOfImages = 0

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
        return not self.isLoading()

    # Return true if object collection has not finished loading.
    def isLoading(self):
        return self.__insertionWorkerTag != None

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

    def getCreateAlbumChildLabel(self):
        return "Create album child..."

    def getRegisterImagesLabel(self):
        return "Register and add images..."

    def getGenerateHtmlLabel(self):
        return "Generate HTML..."

    def getAlbumPropertiesLabel(self):
        return "Album properties..."

    def getOpenImageLabel(self):
        return "Open image in external program..."

    def getDuplicateAndOpenImageLabel(self):
        return "Duplicate and open image in external program..."

    def getRotateImageLeftLabel(self):
        return "Rotate image left"

    def getRotateImageRightLabel(self):
        return "Rotate image right"

    def getImageVersionsLabel(self):
        return "Edit image versions..."

    def getRegisterImageVersionsLabel(self):
        return "Register image versions..."

    def getMergeImagesLabel(self):
        return "Merge images..."

    def getObjectMetadataMap(self):
        return self.__objectMetadataMap

    def getModel(self):
        return self.__treeModel

    def getUnsortedModel(self):
        return self.__treeModel

    def addInsertedRowCallback(self, callback, data=None):
        self.__rowInsertedCallbacks.append((callback, data))

    def removeInsertedRowCallback(self, callback, data=None):
        self.__rowInsertedCallbacks.remove((callback, data))

    def signalRowInserted(self):
        for callback, data in self.__rowInsertedCallbacks:
            callback(data)

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

    def reloadSingleObjectView(self):
        for view in self.__registeredViews:
            view._reloadSingleObjectView()

    def clear(self, freeze=True):
        env.debug("Clearing object collection")
        if freeze:
            self._freezeViews()
        self.__stopInsertionWorker()
        self.__treeModel.clear()
        gc.collect()
        self.__nrOfAlbums = 0
        self.__nrOfImages = 0
        self._handleNrOfObjectsUpdate()
        self.__objectSelection.unselectAll()
        if freeze:
            self._thawViews()

    def cut(self, *unused):
        raise Exception("Error. Not allowed to cut objects into objectCollection.") # TODO

    def copy(self, *unused):
        env.clipboard.setObjects(self.__objectSelection.getSelectedObjects())

    def paste(self, *unused):
        raise Exception("Error. Not allowed to paste objects into objectCollection.") # TODO

    def delete(self, *unused):
        raise Exception("Error. Not allowed to delete objects from objectCollection.") # TODO

    def destroy(self, *unused):
        model = self.getModel()

        albumsSelected = False
        imagesSelected = False
        for position in self.__objectSelection:
            iterator = model.get_iter(position)
            isAlbum = model.get_value(
                iterator, self.COLUMN_IS_ALBUM)
            if isAlbum:
                albumsSelected = True
            else:
                imagesSelected = True

        assert albumsSelected ^ imagesSelected

        self._freezeViews()
        if albumsSelected:
            dialogId = "destroyAlbumsDialog"
        else:
            dialogId = "destroyImagesDialog"
        widgets = gtk.glade.XML(env.gladeFile, dialogId)
        dialog = widgets.get_widget(dialogId)
        result = dialog.run()
        albumDestroyed = False
        if result == gtk.RESPONSE_OK:
            if albumsSelected:
                deleteFiles = False
            else:
                checkbutton = widgets.get_widget("deleteImageFilesCheckbutton")
                deleteFiles = checkbutton.get_active()
            objectIds = Set()
            # Create a Set to avoid duplicated objects.
            for obj in Set(self.__objectSelection.getSelectedObjects()):
                if deleteFiles and not obj.isAlbum():
                    for iv in obj.getImageVersions():
                        try:
                            os.remove(iv.getLocation().encode(env.codeset))
                            # TODO: Delete from image cache too?
                        except OSError:
                            pass
                env.clipboard.removeObjects(obj)
                env.shelf.deleteObject(obj.getId())
                objectIds.add(obj.getId())
                if obj.isAlbum():
                    albumDestroyed = True
            self.getObjectSelection().unselectAll()
            unsortedModel = self.getUnsortedModel()
            locations = [row.path for row in unsortedModel
                         if row[ObjectCollection.COLUMN_OBJECT_ID] in objectIds]
            locations.sort()
            locations.reverse()
            for loc in locations:
                del unsortedModel[loc]
        dialog.destroy()
        if albumDestroyed:
            env.mainwindow.reloadAlbumTree()
        self._thawViews()

    COLUMN_VALID_LOCATION = 0
    COLUMN_VALID_CHECKSUM = 1
    COLUMN_ROW_EDITABLE   = 2
    COLUMN_IS_ALBUM       = 3

    # Columns visible to user
    COLUMN_OBJECT_ID      = 4
    COLUMN_LOCATION       = 5
    COLUMN_THUMBNAIL      = 6
    COLUMN_IMAGE_VERSIONS = 7
    COLUMN_ALBUM_TAG      = 8

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

    def _insertObjectList(self, objectList, location=None):
        # location = None means insert last, otherwise insert before
        # location.
        #
        # Note that this method does NOT update objectSelection.

        if location == None:
            location = len(self.__treeModel)
        self.__insertionWorkerTag = gobject.idle_add(
            self.__insertionWorker(objectList, location).next)

    def __insertionWorker(self, objectList, location):
        for obj in objectList:
            self._freezeViews()

#            self.__treeModel.insert(location)
# Work-around for bug 171027 in PyGTK 2.6.1:
            if location >= len(self.__treeModel):
                iterator = self.__treeModel.append()
            else:
                iterator = self.__treeModel.insert_before(
                    self.__treeModel[location].iter)
# End work-around.

            self.__treeModel.set_value(iterator, self.COLUMN_OBJECT_ID, obj.getId())
            if obj.isAlbum():
                self.__treeModel.set_value(iterator, self.COLUMN_IS_ALBUM, True)
                self.__treeModel.set_value(iterator, self.COLUMN_ALBUM_TAG, obj.getTag())
                self.__treeModel.set_value(iterator, self.COLUMN_LOCATION, None)
                self.__treeModel.set_value(iterator, self.COLUMN_IMAGE_VERSIONS, "")
                self.__nrOfAlbums += 1
            else:
                if obj.getPrimaryVersion():
                    ivlocation = obj.getPrimaryVersion().getLocation()
                else:
                    ivlocation = None
                imageVersions = list(obj.getImageVersions())
                if len(imageVersions) > 1:
                    imageVersionsText = str(len(imageVersions))
                else:
                    imageVersionsText = ""
                self.__treeModel.set_value(iterator, self.COLUMN_IS_ALBUM, False)
                self.__treeModel.set_value(iterator, self.COLUMN_ALBUM_TAG, None)
                self.__treeModel.set_value(iterator, self.COLUMN_LOCATION, ivlocation)
                self.__treeModel.set_value(iterator, self.COLUMN_IMAGE_VERSIONS, imageVersionsText)
                self.__nrOfImages += 1
                # TODO Set COLUMN_VALID_LOCATION and COLUMN_VALID_CHECKSUM
            for attribute, value in obj.getAttributeMap().items():
                if "@" + attribute in self.__objectMetadataMap:
                    column = self.__objectMetadataMap["@" + attribute][self.COLUMN_NR]
                    self.__treeModel.set_value(iterator, column, value)
            self.__treeModel.set_value(iterator, self.COLUMN_ROW_EDITABLE, True)
            self._thawViews()
            self.signalRowInserted()
            self.__loadThumbnail(self.__treeModel, iterator)
            location += 1
            self.__updateObjectCount(True)
            yield True

        self._handleNrOfObjectsUpdate()
        self.__insertionWorkerFinished()
        yield False

    def __stopInsertionWorker(self):
        if self.__insertionWorkerTag:
            gobject.source_remove(self.__insertionWorkerTag)
            self.__insertionWorkerFinished()

    def __insertionWorkerFinished(self):
        self.__insertionWorkerTag = None
        self.__updateObjectCount(False)
        for view in self.__registeredViews:
            view.loadingFinished()

    def __updateObjectCount(self, loadingInProgress):
        env.widgets["statusbarLoadedObjects"].pop(1)
        if loadingInProgress:
            text = "%d objects (and counting...)" % len(self.__treeModel)
        else:
            text = "%d objects" % len(self.__treeModel)
        env.widgets["statusbarLoadedObjects"].push(1, text)

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
        if self.__frozen:
            return
        for view in self.__registeredViews:
            view.freeze()
        self.__frozen = True

    def _thawViews(self):
        if not self.__frozen:
            return
        for view in self.__registeredViews:
            view.thaw()
        self.__frozen = False


###############################################################################
### Callback functions

    def _attributeEdited(self, unused1, path, value, unused2, attributeName):
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

    def _albumTagEdited(self, unused1, path, value, unused2, columnNumber):
        model = self.getModel()
        iterator = model.get_iter(path)
        assert model.get_value(iterator, self.COLUMN_IS_ALBUM)
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

    def reloadSelectedRows(self):
        model = self.getUnsortedModel()
        for (rowNr, obj) in self.__objectSelection.getMap().items():
            if not obj.isAlbum():
                self.__loadThumbnail(model, model.get_iter(rowNr))
                imageVersions = list(obj.getImageVersions())
                if len(imageVersions) > 1:
                    imageVersionsText = str(len(imageVersions))
                else:
                    imageVersionsText = ""
                model.set_value(model.get_iter(rowNr), self.COLUMN_IMAGE_VERSIONS, imageVersionsText)

    def createAlbumChild(self, *unused):
        dialog = AlbumDialog("Create album")
        dialog.run(self._createAlbumChildHelper)

    def _createAlbumChildHelper(self, tag, desc):
        newAlbum = env.shelf.createAlbum(tag)
        if len(desc) > 0:
            newAlbum.setAttribute(u"title", desc)
        selectedObjects = self.__objectSelection.getSelectedObjects()
        selectedAlbum = selectedObjects[0]
        children = list(selectedAlbum.getChildren())
        children.append(newAlbum)
        selectedAlbum.setChildren(children)
        env.mainwindow.reloadAlbumTree()

    def registerAndAddImages(self, *unused):
        selectedObjects = self.__objectSelection.getSelectedObjects()
        assert len(selectedObjects) == 1 and selectedObjects[0].isAlbum()
        selectedAlbum = selectedObjects[0]
        dialog = RegisterImagesDialog(selectedAlbum)
        if dialog.run() == gtk.RESPONSE_OK:
            env.mainwindow.reload() # TODO: Don't reload everything.
        dialog.destroy()

    def generateHtml(self, *unused):
        selectedObjects = self.__objectSelection.getSelectedObjects()
        assert len(selectedObjects) == 1 and selectedObjects[0].isAlbum()
        selectedAlbum = selectedObjects[0]
        env.mainwindow.generateHtml(selectedAlbum)

    def albumProperties(self, *unused):
        selectedObjects = self.__objectSelection.getSelectedObjects()
        assert len(selectedObjects) == 1 and selectedObjects[0].isAlbum()
        selectedAlbumId = selectedObjects[0].getId()
        dialog = AlbumDialog("Edit album", selectedAlbumId)
        dialog.run(self._albumPropertiesHelper)

    def _albumPropertiesHelper(self, tag, desc):
        selectedObjects = self.__objectSelection.getSelectedObjects()
        selectedAlbum = selectedObjects[0]
        selectedAlbum.setTag(tag)
        if len(desc) > 0:
            selectedAlbum.setAttribute(u"title", desc)
        else:
            selectedAlbum.deleteAttribute(u"title")
        env.mainwindow.reloadAlbumTree()
        # TODO: Update objectCollection.

    def imageVersions(self, *unused):
        selectedObjects = self.__objectSelection.getSelectedObjects()
        assert len(selectedObjects) == 1
        dialog = ImageVersionsDialog(self)
        dialog.runViewImageVersions(selectedObjects[0])
        self.reloadSingleObjectView()

    def registerImageVersions(self, *unused):
        selectedObjects = self.__objectSelection.getSelectedObjects()
        assert len(selectedObjects) == 1
        dialog = RegisterImageVersionsDialog(self)
        dialog.run(selectedObjects[0])
        self.reloadSingleObjectView()

    def mergeImages(self, *unused):
        selectedObjects = self.__objectSelection.getSelectedObjects()
        assert len(selectedObjects) > 1
        dialog = ImageVersionsDialog(self)
        dialog.runMergeImages(selectedObjects)

    def rotateImage(self, unused, angle):
        env.mainwindow.getImagePreloader().clearCache()
        for (rowNr, obj) in self.__objectSelection.getMap().items():
            if not obj.isAlbum():
                imageversion = obj.getPrimaryVersion()
                if not imageversion:
                    # Image has no versions. Skip it for now.
                    continue
                location = imageversion.getLocation()
                if angle == 90:
                    commandString = env.rotateRightCommand
                else:
                    commandString = env.rotateLeftCommand
                command = commandString % { "location":location }
                result = os.system(command.encode(env.codeset))
                if result == 0:
                    imageversion.contentChanged()
                    model = self.getUnsortedModel()
                    self.__loadThumbnail(model, model.get_iter(rowNr))
                    env.mainwindow.getImagePreloader().clearCache()
                else:
                    dialog = gtk.MessageDialog(
                        type=gtk.MESSAGE_ERROR,
                        buttons=gtk.BUTTONS_OK,
                        message_format="Failed to execute command: \"%s\"" % command)
                    dialog.run()
                    dialog.destroy()
        self.reloadSingleObjectView()

    def rotateImageLeft(self, widget, *unused):
        self.rotateImage(widget, 270)

    def rotateImageRight(self, widget, *unused):
        self.rotateImage(widget, 90)

    def openImage(self, *unused):
        locations = ""
        for obj in self.__objectSelection.getSelectedObjects():
            if not obj.isAlbum():
                imageversion = obj.getPrimaryVersion()
                if not imageversion:
                    # Image has no versions. Skip it for now.
                    continue
                location = imageversion.getLocation()
                locations += location + " "
        if locations != "":
            command = env.openCommand % { "locations":locations }
            result = os.system(command.encode(env.codeset) + " &")
            if result != 0:
                dialog = gtk.MessageDialog(
                    type=gtk.MESSAGE_ERROR,
                    buttons=gtk.BUTTONS_OK,
                    message_format="Failed to execute command: \"%s\"" % command)
                dialog.run()
                dialog.destroy()

    def duplicateAndOpenImage(self, *unused):
        selectedObjects = self.__objectSelection.getSelectedObjects()
        assert len(selectedObjects) == 1
        assert not selectedObjects[0].isAlbum()
        dialog = DuplicateAndOpenImageDialog()
        dialog.run(selectedObjects[0].getPrimaryVersion())

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
        elif not obj.getPrimaryVersion():
            pixbuf = env.unknownImageIconPixbuf
        else:
            try:
                thumbnailLocation = env.imageCache.get(
                    obj.getPrimaryVersion(),
                    env.thumbnailSize[0],
                    env.thumbnailSize[1])[0]
                pixbuf = gtk.gdk.pixbuf_new_from_file(thumbnailLocation.encode(env.codeset))
                # TODO Set and use COLUMN_VALID_LOCATION and COLUMN_VALID_CHECKSUM
            except IOError:
                pixbuf = env.unknownImageIconPixbuf
        model.set_value(iterator, self.COLUMN_THUMBNAIL, pixbuf)
