import gtk
import os
from environment import env
from kofoto.shelf import ImageExistsError, NotAnImageError, makeValidTag
from kofoto.clientutils import walk_files

class RegisterImagesDialog(gtk.FileSelection):
    def __init__(self):
        gtk.FileSelection.__init__(self, title="Register images")
        self.set_select_multiple(True)
        self.ok_button.connect("clicked", self._ok)
        self.cancel_button.connect("clicked", self._cancel)

    def _ok(self, widget):
        for filepath in walk_files(self.get_selections()):
            try:
                env.shelf.createImage(filepath.decode("utf-8"))
            except (NotAnImageError, ImageExistsError):
                pass
        self.hide()

    def _cancel(self, widget):
        self.destroy()
