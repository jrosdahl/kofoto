import gtk
import gtk.gdk
import os

from environment import env

class MainWindow(gtk.Window):
    def __init__(self):
        self._toggleLock = gtk.FALSE
        
        env.widgets["expandViewToggleButton"].connect("toggled", self._toggleExpandView)
        env.widgets["expandViewToggleButton"].get_child().add(self.getIconImage("fullscreen-24.png"))
        env.widgets["attributeToggleButton"].connect("toggled", self._toggleAttributesView)
        env.widgets["thumbnailsViewToggleButton"].connect("clicked", self._toggleThumbnailsView)
        env.widgets["imageViewToggleButton"].connect("clicked", self._toggleImageView)
        env.widgets["tableViewToggleButton"].connect("clicked", self._toggleTableView)
        env.widgets["save"].connect("activate", env.controller.save)
        env.widgets["quit"].connect("activate", env.controller.quit)

        # Gray out not yet implemented stuff...
        env.widgets["revert"].set_sensitive(gtk.FALSE)
        env.widgets["copy"].set_sensitive(gtk.FALSE)
        env.widgets["paste"].set_sensitive(gtk.FALSE)
        env.widgets["preferences"].set_sensitive(gtk.FALSE)
        
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

    def _toggleAttributesView(self, button):
        if button.get_active():
            env.widgets["attributeView"].show()
        else:
            env.widgets["attributeView"].hide()

    def _toggleThumbnailsView(self, button):
        if not self._toggleLock:
            self._toggleLock = gtk.TRUE
            button.set_active(gtk.TRUE)
            env.widgets["imageViewToggleButton"].set_active(gtk.FALSE)
            env.widgets["tableViewToggleButton"].set_active(gtk.FALSE)
            env.controller.showThumbnailView()
            self._toggleLock = gtk.FALSE

    def _toggleImageView(self, button):
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
            env.widgets["imageViewToggleButton"].set_active(gtk.FALSE)
            env.controller.showTableView()
            self._toggleLock = gtk.FALSE
