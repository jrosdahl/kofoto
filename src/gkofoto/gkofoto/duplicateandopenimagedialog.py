import glob
import os
import shutil

import gtk

from environment import env

class DuplicateAndOpenImageDialog:
    def __init__(self):
        self._widgets = gtk.glade.XML(
            env.gladeFile, "duplicateAndOpenImageDialog")
        self._dialog = self._widgets.get_widget("duplicateAndOpenImageDialog")
        self._cancelButton = self._widgets.get_widget("cancelButton")
        self._okButton = self._widgets.get_widget("okButton")
        self._browseButton = self._widgets.get_widget("browseButton")
        self._fileEntry = self._widgets.get_widget("fileEntry")

        self._cancelButton.connect("clicked", self._onCancel)
        self._okButton.connect("clicked", self._onOk)
        self._browseButton.connect("clicked", self._onBrowse)

    def run(self, imageversion):
        self._imageversion = imageversion
        location = imageversion.getLocation()
        prefix, suffix = os.path.splitext(location)
        duplicateLocation = "%s+fix%s" % (prefix, suffix)
        self.__setFile(duplicateLocation)
        self._fileEntry.select_region(len(prefix) + 1, len(prefix + "fix") + 1)
        self._dialog.run()

    def _onCancel(self, *unused):
        self._dialog.destroy()

    def _onOk(self, *unused):
        duplicateLocation = self._fileEntry.get_text()
        if os.path.exists(duplicateLocation):
            dialog = gtk.MessageDialog(
                self._dialog,
                gtk.DIALOG_MODAL,
                gtk.MESSAGE_ERROR,
                gtk.BUTTONS_OK,
                "File already exists: %s" % duplicateLocation)
            dialog.run()
            dialog.destroy()
        else:
            shutil.copyfile(
                self._imageversion.getLocation(),
                duplicateLocation)
            command = env.openCommand % {"locations": duplicateLocation}
            result = os.system(command + " &")
            if result != 0:
                dialog = gtk.MessageDialog(
                    self._dialog,
                    gtk.DIALOG_MODAL,
                    gtk.MESSAGE_ERROR,
                    gtk.BUTTONS_OK,
                    "Failed to execute command: \"%s\"" % command)
                dialog.run()
                dialog.destroy()
        self._dialog.destroy()

    def _onBrowse(self, *unused):
        dialog = gtk.FileChooserDialog(
            "Choose name of duplicate image",
            self._dialog,
            gtk.FILE_CHOOSER_ACTION_SAVE,
            (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
             gtk.STOCK_OK, gtk.RESPONSE_OK))
        if dialog.run() == gtk.RESPONSE_OK:
            self.__setFile(dialog.get_filename())
        dialog.destroy()

    def __setFile(self, location):
        self._fileEntry.set_text(location)
        self._fileEntry.set_position(-1)  # Last.
