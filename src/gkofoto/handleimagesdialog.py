import gtk
import gobject
import os
from environment import env
from kofoto.shelf import \
     ImageDoesNotExistError, ImageExistsError, \
     MultipleImagesAtOneLocationError, NotAnImageError, \
     makeValidTag
from kofoto.clientutils import walk_files

class HandleImagesDialog(gtk.FileSelection):
    def __init__(self):
        gtk.FileSelection.__init__(self, title="Register images")
        self.set_select_multiple(True)
        self.ok_button.connect("clicked", self._ok)

    def _ok(self, widget):
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
        for filepath in walk_files(self.get_selections()):
            filepath = filepath.decode("utf-8")
            try:
                image = env.shelf.getImage(filepath)
                if image.getLocation() == os.path.realpath(filepath):
                    # Registered.
                    knownUnchangedImages += 1
                    knownUnchangedImagesCount.set_text(
                        str(knownUnchangedImages))
                else:
                    # Moved.
                    knownMovedImages += 1
                    knownMovedImagesCount.set_text(str(knownMovedImages))
                    movedImages.append(filepath)
            except ImageDoesNotExistError:
                try:
                    image = env.shelf.getImage(
                        filepath, identifyByLocation=True)
                    # Modified.
                    unknownModifiedImages += 1
                    unknownModifiedImagesCount.set_text(
                        str(unknownModifiedImages))
                    modifiedImages.append(filepath)
                except MultipleImagesAtOneLocationError:
                    # Multiple images at one location.
                    # TODO: Handle this error.
                    pass
                except ImageDoesNotExistError:
                    # Unregistered.
                    unknownFiles += 1
                    unknownFilesCount.set_text(str(unknownFiles))
            investigatedFiles += 1
            investigatedFilesCount.set_text(str(investigatedFiles))
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
                image = env.shelf.getImage(
                    filepath, identifyByLocation=True)
                image.contentChanged()
            except ImageDoesNotExistError:
                self._error("Image does not exist: %s" % filepath)
            except MultipleImagesAtOneLocationError:
                # TODO: Handle this.
                pass
            except IOError, x:
                self._error("Error while reading %s: %s" % (
                    filepath, x))

    def _updateMovedImages(self, filepaths):
        for filepath in filepaths:
            try:
                image = env.shelf.getImage(filepath)
                image.locationChanged(filepath)
            except ImageDoesNotExistError:
                self._error("Image does not exist: %s" % filepath)
            except MultipleImagesAtOneLocationError:
                # TODO: Handle this.
                pass
            except IOError, x:
                self._error("Error while reading %s: %s" % (
                    filepath, x))
