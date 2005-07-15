import glob
import os

import gtk

from environment import env
from kofoto.shelf import \
    ImageVersionDoesNotExistError, \
    ImageVersionExistsError, \
    ImageVersionType, \
    NotAnImageFileError

class RegisterImageVersionsDialog:
    def __init__(self, model):
        self._model = model
        self._widgets = gtk.glade.XML(
            env.gladeFile, "registerImageVersionsDialog")
        self._dialog = self._widgets.get_widget("registerImageVersionsDialog")
        self._cancelButton = self._widgets.get_widget("cancelButton")
        self._okButton = self._widgets.get_widget("okButton")
        self._browseButton = self._widgets.get_widget("browseButton")
        self._fileListView = self._widgets.get_widget("fileList")

        self._cancelButton.connect("clicked", self._onCancel)
        self._okButton.connect("clicked", self._onOk)
        self._browseButton.connect("clicked", self._onBrowse)

        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Image filename", renderer, text=0)
        self._fileListView.append_column(column)
        self._fileListView.get_selection().set_mode(gtk.SELECTION_MULTIPLE)

        self._fileListStore = gtk.ListStore(str)
        self._fileListView.set_model(self._fileListStore)

    def run(self, image):
        self._image = image
        location = image.getPrimaryVersion().getLocation()
        prefix, suffix = os.path.splitext(location)
        candidates = glob.glob("%s?*%s" % (prefix, suffix))
        files = []
        for candidate in candidates:
            try:
                env.shelf.getImageVersionByLocation(candidate)
            except ImageVersionDoesNotExistError:
                files.append(candidate)
        self.__setFiles(files)
        self._dialog.run()

    def _onCancel(self, *unused):
        self._dialog.destroy()

    def _onOk(self, *unused):
        selection = self._fileListView.get_selection()
        model, selectedRows = selection.get_selected_rows()
        changed = False
        for path in selectedRows:
            treeiter = self._fileListStore.get_iter(path)
            location = self._fileListStore.get_value(treeiter, 0)
            try:
                imageVersion = env.shelf.createImageVersion(
                    self._image, location, ImageVersionType.Other)
                changed = True
            except NotAnImageFileError:
                dialog = gtk.MessageDialog(
                    self._dialog,
                    gtk.DIALOG_MODAL,
                    gtk.MESSAGE_ERROR,
                    gtk.BUTTONS_OK,
                    "Not an image: %s" % location)
                dialog.run()
                dialog.destroy()
            except ImageVersionExistsError:
                dialog = gtk.MessageDialog(
                    self._dialog,
                    gtk.DIALOG_MODAL,
                    gtk.MESSAGE_ERROR,
                    gtk.BUTTONS_OK,
                    "Already registered: %s" % location)
                dialog.run()
                dialog.destroy()
        if changed:
            imageVersion.makePrimary()
            self._model.reloadSelectedRows()
        self._dialog.destroy()

    def _onBrowse(self, *unused):
        dialog = gtk.FileChooserDialog(
            "Choose image version files",
            self._dialog,
            gtk.FILE_CHOOSER_ACTION_OPEN,
            (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
             gtk.STOCK_OK, gtk.RESPONSE_OK))
        dialog.set_select_multiple(True)
        if dialog.run() == gtk.RESPONSE_OK:
            self.__setFiles(dialog.get_filenames())
        dialog.destroy()

    def __setFiles(self, filenames):
        self._fileListStore.clear()
        for filename in filenames:
            self._fileListStore.append([filename])
        self._fileListView.get_selection().select_all()
