import gtk
import os
from environment import env
from kofoto.shelf import ImageExistsError, NotAnImageError, makeValidTag
from kofoto.clientutils import walk_files

class RegisterImagesDialog(gtk.FileSelection):
    def __init__(self, albumToAddTo=None):
        gtk.FileSelection.__init__(self, title="Register images")
        self.__albumToAddTo = albumToAddTo
        self.set_select_multiple(True)
        self.ok_button.connect("clicked", self._ok)

    def _ok(self, widget):
        images = []
        for filepath in walk_files(self.get_selections()):
            try:
                image = env.shelf.createImage(filepath.decode("utf-8"))
                images.append(image)
            except (NotAnImageError, ImageExistsError):
                pass
        if self.__albumToAddTo:
            children = list(self.__albumToAddTo.getChildren())
            self.__albumToAddTo.setChildren(children + images)
