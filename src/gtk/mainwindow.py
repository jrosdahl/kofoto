import gtk
import gtk.gdk

from environment import env

class MainWindow(gtk.Window):
    def _toggleExpandView(self, button):
        if button.get_active():
            env.widgets["notebook"].hide()
        else:
            env.widgets["notebook"].show()

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
            env.widgets["thumbnailView"].show()
            env.widgets["imageView"].hide()
            env.widgets["tableViewScroll"].hide()
            self._toggleLock = gtk.FALSE

    def _toggleImageView(self, button):
        if not self._toggleLock:
            self._toggleLock = gtk.TRUE
            button.set_active(gtk.TRUE)
            env.widgets["tableViewToggleButton"].set_active(gtk.FALSE)
            env.widgets["thumbnailsViewToggleButton"].set_active(gtk.FALSE)
            env.widgets["imageView"].show()
            env.widgets["tableViewScroll"].hide()        
            env.widgets["thumbnailView"].hide()
            self._toggleLock = gtk.FALSE
            
    def _toggleTableView(self, button):
        if not self._toggleLock:
            self._toggleLock = gtk.TRUE
            button.set_active(gtk.TRUE)
            env.widgets["thumbnailsViewToggleButton"].set_active(gtk.FALSE)
            env.widgets["imageViewToggleButton"].set_active(gtk.FALSE)
            env.widgets["tableViewScroll"].show()
            env.widgets["thumbnailView"].hide()
            env.widgets["imageView"].hide()
            self._toggleLock = gtk.FALSE
        
            
    def __init__(self):
        expandViewToggleButton = env.widgets["expandViewToggleButton"]
        expandViewToggleButton.connect("toggled", self._toggleExpandView)
        expandViewToggleButton.get_child().add(self.getIconImage("fullscreen-24.png"))

        expandViewToggleButton = env.widgets["attributeToggleButton"]
        expandViewToggleButton.connect("toggled", self._toggleAttributesView)

        self._toggleLock = gtk.FALSE
        env.widgets["thumbnailsViewToggleButton"].connect("clicked", self._toggleThumbnailsView)
        env.widgets["imageViewToggleButton"].connect("clicked", self._toggleImageView)
        env.widgets["tableViewToggleButton"].connect("clicked", self._toggleTableView)

    def getIconImage(self, name):
        pixbuf = gtk.gdk.pixbuf_new_from_file(env.iconDir + name)
        image = gtk.Image()
        image.set_from_pixbuf(pixbuf)
        image.show()
        return image





    
