import gtk
import gtk.gdk
import os

from environment import env

class MainWindow(gtk.Window):
    def __init__(self):
        self._toggleLock = gtk.FALSE

        env.widgets["expandViewToggleButton"].connect("toggled", self._toggleExpandView)
        env.widgets["expandViewToggleButton"].get_child().add(self.getIconImage("fullscreen-24.png"))
        env.widgets["thumbnailsViewToggleButton"].connect("clicked", self._toggleThumbnailsView)
        env.widgets["objectViewToggleButton"].connect("clicked", self._toggleObjectView)
        env.widgets["tableViewToggleButton"].connect("clicked", self._toggleTableView)
        env.widgets["save"].connect("activate", env.controller.save)
        env.widgets["quit"].connect("activate", env.controller.quit)

        # Gray out not yet implemented stuff...
        env.widgets["new"].set_sensitive(gtk.FALSE)
        env.widgets["open"].set_sensitive(gtk.FALSE)
        env.widgets["save_as"].set_sensitive(gtk.FALSE)
        env.widgets["revert"].set_sensitive(gtk.FALSE)

    def getIconImage(self, name):
        pixbuf = gtk.gdk.pixbuf_new_from_file(os.path.join(env.iconDir, name))
        image = gtk.Image()
        image.set_from_pixbuf(pixbuf)
        image.show()
        return image

    def _toggleExpandView(self, button):
        if button.get_active():
            env.widgets["sourceNotebook"].hide()
        else:
            env.widgets["sourceNotebook"].show()

    def _toggleThumbnailsView(self, button):
        if not self._toggleLock:
            self._toggleLock = gtk.TRUE
            button.set_active(gtk.TRUE)
            env.widgets["objectViewToggleButton"].set_active(gtk.FALSE)
            env.widgets["tableViewToggleButton"].set_active(gtk.FALSE)
            env.controller.showThumbnailView()
            self._toggleLock = gtk.FALSE

    def _toggleObjectView(self, button):
        if not self._toggleLock:
            self._toggleLock = gtk.TRUE
            button.set_active(gtk.TRUE)
            env.widgets["tableViewToggleButton"].set_active(gtk.FALSE)
            env.widgets["thumbnailsViewToggleButton"].set_active(gtk.FALSE)
            env.controller.showSingleImageView()
            self._toggleLock = gtk.FALSE

    def _toggleTableView(self, button):
        if not self._toggleLock:
            self._toggleLock = gtk.TRUE
            button.set_active(gtk.TRUE)
            env.widgets["thumbnailsViewToggleButton"].set_active(gtk.FALSE)
            env.widgets["objectViewToggleButton"].set_active(gtk.FALSE)
            env.controller.showTableView()
            self._toggleLock = gtk.FALSE
