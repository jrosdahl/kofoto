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
        widgets = gtk.glade.XML(env.gladeFile, "registrationProgressDialog")
        registrationProgressDialog = widgets.get_widget(
            "registrationProgressDialog")
        newImagesCount = widgets.get_widget(
            "newImagesCount")
        alreadyRegisteredImagesCount = widgets.get_widget(
            "alreadyRegisteredImagesCount")
        nonImagesCount = widgets.get_widget(
            "nonImagesCount")
        filesInvestigatedCount = widgets.get_widget(
            "filesInvestigatedCount")
        okButton = widgets.get_widget("okButton")
        okButton.set_sensitive(False)

        registrationProgressDialog.show()

        newImages = 0
        alreadyRegisteredImages = 0
        nonImages = 0
        filesInvestigated = 0
        images = []
        for filepath in walk_files(self.get_selections()):
            try:
                try:
                    filepath = filepath.decode("utf-8")
                except UnicodeDecodeError:
                    filepath = filepath.decode("latin1")
                image = env.shelf.createImage(filepath)
                images.append(image)
                newImages += 1
                newImagesCount.set_text(str(newImages))
            except ImageExistsError:
                alreadyRegisteredImages += 1
                alreadyRegisteredImagesCount.set_text(str(alreadyRegisteredImages))
            except NotAnImageError:
                nonImages += 1
                nonImagesCount.set_text(str(nonImages))
            filesInvestigated += 1
            filesInvestigatedCount.set_text(str(filesInvestigated))
            while gtk.events_pending():
                gtk.main_iteration()
        if self.__albumToAddTo:
            children = list(self.__albumToAddTo.getChildren())
            self.__albumToAddTo.setChildren(children + images)

        okButton.set_sensitive(True)
        registrationProgressDialog.run()
        registrationProgressDialog.destroy()
