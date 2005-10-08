# pylint: disable-msg=F0203, E0201

import gtk
import time
from kofoto.gkofoto.environment import env
from kofoto.shelf import \
    ImageVersionExistsError, ImageVersionType, NotAnImageFileError
from kofoto.clientutils import walk_files

class RegisterImagesDialog(gtk.FileChooserDialog):
    def __init__(self, albumToAddTo=None):
        gtk.FileChooserDialog.__init__(
            self,
            title="Register images",
            action=gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER,
            buttons=(
                gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                gtk.STOCK_OK, gtk.RESPONSE_OK))
        self.__albumToAddTo = albumToAddTo
        self.connect("response", self._response)

    def _response(self, unused, responseId):
        self.hide()
        if responseId != gtk.RESPONSE_OK:
            return
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
        registrationTimeString = unicode(time.strftime("%Y-%m-%d %H:%M:%S"))
        for filepath in walk_files([self.get_filename()]):
            try:
                try:
                    filepath = filepath.decode("utf-8")
                except UnicodeDecodeError:
                    filepath = filepath.decode("latin1")
                image = env.shelf.createImage()
                env.shelf.createImageVersion(
                    image, filepath, ImageVersionType.Original)
                image.setAttribute(u"registered", registrationTimeString)
                images.append(image)
                newImages += 1
                newImagesCount.set_text(str(newImages))
            except ImageVersionExistsError:
                alreadyRegisteredImages += 1
                alreadyRegisteredImagesCount.set_text(str(alreadyRegisteredImages))
                env.shelf.deleteImage(image.getId())
            except NotAnImageFileError:
                nonImages += 1
                nonImagesCount.set_text(str(nonImages))
                env.shelf.deleteImage(image.getId())
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
