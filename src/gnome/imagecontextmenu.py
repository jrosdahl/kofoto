import gtk
import gobject
import gtk

from environment import env

class ImageContextMenu(gtk.Menu):

    def __init__(self, images, selectedImages):
        gtk.Menu.__init__(self)

        self._unregisterItem = gtk.MenuItem("Unregister")
        self._unregisterItem.show()
        self._unregisterItem.connect("activate", images.unregisterImages, None)
        self.append(self._unregisterItem)

        self._rotateLeftItem = gtk.MenuItem("Rotate left")
        self._rotateLeftItem.show()
        self._rotateLeftItem.connect("activate", images.rotate, 270)
        self.append(self._rotateLeftItem)
        
        self._rotateRightItem = gtk.MenuItem("Rotate right")
        self._rotateRightItem.show()
        self._rotateRightItem.connect("activate", images.rotate, 90)
        self.append(self._rotateRightItem)

        self._selectedImages = selectedImages
        self.updateContextMenu()

    def updateContextMenu(self):
        if len(self._selectedImages) == 0:
            self._unregisterItem.set_sensitive(gtk.FALSE)
            self._rotateLeftItem.set_sensitive(gtk.FALSE)
            self._rotateRightItem.set_sensitive(gtk.FALSE)
        else:
            self._unregisterItem.set_sensitive(gtk.TRUE)
            self._rotateLeftItem.set_sensitive(gtk.TRUE)
            self._rotateRightItem.set_sensitive(gtk.TRUE)
