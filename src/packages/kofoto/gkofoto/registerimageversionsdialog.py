import os
import re

import gtk

from kofoto.gkofoto.environment import env
from kofoto.shelf import \
    ImageVersionDoesNotExistError, \
    ImageVersionExistsError, \
    ImageVersionType, \
    NotAnImageFileError

class RegisterImageVersionsDialog:
    def __init__(self, model):
        self._image = None
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
        files = set()
        for imageversion in image.getImageVersions():
            base, filename = os.path.split(imageversion.getLocation())
            prefix, _ = os.path.splitext(filename)
            for candidateFilename in os.listdir(base):
                if re.match("%s[^a-zA-Z0-9].*" % prefix, candidateFilename):
                    candidatePath = os.path.join(base, candidateFilename)
                    if os.path.isfile(candidatePath):
                        try:
                            env.shelf.getImageVersionByLocation(candidatePath)
                        except ImageVersionDoesNotExistError:
                            files.add(candidatePath)
        self.__setFiles(files)
        self._dialog.run()

    def _onCancel(self, *unused):
        self._dialog.destroy()

    def _onOk(self, *unused):
        selection = self._fileListView.get_selection()
        _, selectedRows = selection.get_selected_rows()
        changed = False
        for path in selectedRows:
            treeiter = self._fileListStore.get_iter(path)
            location = \
                self._fileListStore.get_value(treeiter, 0).decode("utf-8")
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
            filenames = [x.decode("utf-8") for x in dialog.get_filenames()]
            self.__setFiles(filenames)
        dialog.destroy()

    def __setFiles(self, filenames):
        self._fileListStore.clear()
        for filename in filenames:
            self._fileListStore.append([filename])
        self._fileListView.get_selection().select_all()
