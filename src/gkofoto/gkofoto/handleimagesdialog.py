import gtk
import gobject
import os
from environment import env
from kofoto.shelf import \
     ImageVersionDoesNotExistError, ImageVersionExistsError, \
     MultipleImageVersionsAtOneLocationError, \
     makeValidTag, computeImageHash
from kofoto.clientutils import walk_files

class HandleImagesDialog(gtk.FileChooserDialog):
    def __init__(self):
        gtk.FileChooserDialog.__init__(
            self,
            title="Handle images",
            action=gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER,
            buttons=(
                gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                gtk.STOCK_OK, gtk.RESPONSE_OK))
        self.connect("response", self._response)

    def _response(self, widget, responseId):
        if responseId != gtk.RESPONSE_OK:
            return
        widgets = gtk.glade.XML(env.gladeFile, "handleImagesProgressDialog")
        handleImagesProgressDialog = widgets.get_widget(
            "handleImagesProgressDialog")
        knownUnchangedImagesCount = widgets.get_widget(
            "knownUnchangedImagesCount")
        knownMovedImagesCount = widgets.get_widget(
            "knownMovedImagesCount")
        unknownModifiedImagesCount = widgets.get_widget(
            "unknownModifiedImagesCount")
        unknownFilesCount = widgets.get_widget(
            "unknownFilesCount")
        investigatedFilesCount = widgets.get_widget(
            "investigatedFilesCount")
        okButton = widgets.get_widget("okButton")
        okButton.set_sensitive(False)

        handleImagesProgressDialog.show()

        knownUnchangedImages = 0
        knownMovedImages = 0
        unknownModifiedImages = 0
        unknownFiles = 0
        investigatedFiles = 0
        modifiedImages = []
        movedImages = []
        for filepath in walk_files([self.get_filename()]):
            try:
                filepath = filepath.decode("utf-8")
            except UnicodeDecodeError:
                filepath = filepath.decode("latin1")
            try:
                imageversion = env.shelf.getImageVersionByHash(
                    computeImageHash(filepath))
                if imageversion.getLocation() == os.path.realpath(filepath):
                    # Registered.
                    knownUnchangedImages += 1
                    knownUnchangedImagesCount.set_text(
                        str(knownUnchangedImages))
                else:
                    # Moved.
                    knownMovedImages += 1
                    knownMovedImagesCount.set_text(str(knownMovedImages))
                    movedImages.append(filepath)
            except ImageVersionDoesNotExistError:
                try:
                    env.shelf.getImageVersionByLocation(filepath)
                    # Modified.
                    unknownModifiedImages += 1
                    unknownModifiedImagesCount.set_text(
                        str(unknownModifiedImages))
                    modifiedImages.append(filepath)
                except MultipleImageVersionsAtOneLocationError:
                    # Multiple images at one location.
                    # TODO: Handle this error.
                    pass
                except ImageVersionDoesNotExistError:
                    # Unregistered.
                    unknownFiles += 1
                    unknownFilesCount.set_text(str(unknownFiles))
            investigatedFiles += 1
            investigatedFilesCount.set_text(str(investigatedFiles))
            while gtk.events_pending():
                gtk.main_iteration()

        okButton.set_sensitive(True)
        handleImagesProgressDialog.run()
        handleImagesProgressDialog.destroy()

        if modifiedImages or movedImages:
            if modifiedImages:
                self._dialogHelper(
                    "Update modified images",
                    "The above image files have been modified. Press OK to"
                    " make Kofoto recognize the new contents.",
                    modifiedImages,
                    self._updateModifiedImages)
            if movedImages:
                self._dialogHelper(
                    "Update moved or renamed images",
                    "The above image files have been moved or renamed. Press OK to"
                    " make Kofoto recognize the new locations.",
                    movedImages,
                    self._updateMovedImages)
        else:
            dialog = gtk.MessageDialog(
                type=gtk.MESSAGE_INFO,
                buttons=gtk.BUTTONS_OK,
                message_format="No modified, renamed or moved images found.")
            dialog.run()
            dialog.destroy()

    def _dialogHelper(self, title, text, filepaths, handlerFunction):
        widgets = gtk.glade.XML(env.gladeFile, "updateImagesDialog")
        dialog = widgets.get_widget("updateImagesDialog")
        dialog.set_title(title)
        filenameList = widgets.get_widget("filenameList")
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Image filename", renderer, text=0)
        filenameList.append_column(column)
        dialogText = widgets.get_widget("dialogText")
        dialogText.set_text(text)
        model = gtk.ListStore(gobject.TYPE_STRING)
        for filepath in filepaths:
            model.append([filepath])
        filenameList.set_model(model)
        if dialog.run() == gtk.RESPONSE_OK:
            handlerFunction(filepaths)
        dialog.destroy()

    def _error(self, errorText):
        dialog = gtk.MessageDialog(
            type=gtk.MESSAGE_ERROR,
            buttons=gtk.BUTTONS_OK,
            message_format=errorText)
        dialog.run()
        dialog.destroy()

    def _updateModifiedImages(self, filepaths):
        for filepath in filepaths:
            try:
                imageversion = env.shelf.getImageVersionByLocation(filepath)
                imageversion.contentChanged()
            except ImageVersionDoesNotExistError:
                self._error("Image does not exist: %s" % filepath)
            except MultipleImageVersionsAtOneLocationError:
                # TODO: Handle this.
                pass
            except IOError, x:
                self._error("Error while reading %s: %s" % (
                    filepath, x))

    def _updateMovedImages(self, filepaths):
        for filepath in filepaths:
            try:
                imageversion = env.shelf.getImageVersionByHash(
                    computeImageHash(filepath))
                imageversion.locationChanged(filepath)
            except ImageVersionDoesNotExistError:
                self._error("Image does not exist: %s" % filepath)
            except MultipleImageVersionsAtOneLocationError:
                # TODO: Handle this.
                pass
            except IOError, x:
                self._error("Error while reading %s: %s" % (
                    filepath, x))
