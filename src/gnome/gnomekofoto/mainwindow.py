import gtk
import gtk.gdk
import os

from gnomekofoto.categories import *
from gnomekofoto.albums import *
from environment import env
from gnomekofoto.tableview import *
from gnomekofoto.thumbnailview import *
from gnomekofoto.singleobjectview import *

class MainWindow(gtk.Window):
    # TODO add public & private headers
    
    def __init__(self, objectCollection):
        self._toggleLock = gtk.FALSE

        env.widgets["expandViewToggleButton"].connect("toggled", self._toggleExpandView)
        env.widgets["expandViewToggleButton"].get_child().add(self.getIconImage("fullscreen-24.png"))
        env.widgets["thumbnailsViewToggleButton"].connect("clicked", self._toggleThumbnailsView)
        env.widgets["objectViewToggleButton"].connect("clicked", self._toggleObjectView)
        env.widgets["tableViewToggleButton"].connect("clicked", self._toggleTableView)
        env.widgets["save"].connect("activate", env.controller.save)
        env.widgets["revert"].connect("activate", env.controller.revert)
        env.widgets["quit"].connect("activate", env.controller.quit)

        env.widgets["save"].set_sensitive(gtk.FALSE)
        env.widgets["revert"].set_sensitive(gtk.FALSE)

        # Gray out not yet implemented stuff...
        env.widgets["new"].set_sensitive(gtk.FALSE)
        env.widgets["open"].set_sensitive(gtk.FALSE)
        env.widgets["save_as"].set_sensitive(gtk.FALSE)

        env.shelf.registerModificationCallback(self._shelfModificationChangedCallback)

        self.__albums = Albums()
        self.__categories = Categories(objectCollection)
        self.__thumbnailView = ThumbnailView(objectCollection)
        self.__tableView = TableView(objectCollection)
        self.__singleObjectView = SingleObjectView(objectCollection)
        self.__showThumbnailView()

    def setObjectCollection(self, objectCollection):
        self.__categories.setCollection(objectCollection)
        self.__thumbnailView.setObjectCollection(objectCollection)
        self.__tableView.setObjectCollection(objectCollection)
        self.__singleObjectView.setObjectCollection(objectCollection)

    def getIconImage(self, name):
        pixbuf = gtk.gdk.pixbuf_new_from_file(os.path.join(env.iconDir, name))
        image = gtk.Image()
        image.set_from_pixbuf(pixbuf)
        image.show()
        return image

    def _viewChanged(self):
        # TODO
        for hiddenView in self._hiddenViews:
            hiddenView.hide()        
        self._currentView.show()

    def __showTableView(self):
        # TODO        
        self._currentView = self.__tableView
        self._hiddenViews = [self.__thumbnailView, self.__singleObjectView]
        self._viewChanged()

    def __showThumbnailView(self):
        # TODO
        self._currentView = self.__thumbnailView
        self._hiddenViews = [self.__tableView, self.__singleObjectView]
        self._viewChanged()

    def __showSingleObjectView(self):
        # TODO        
        self._currentView = self.__singleObjectView
        self._hiddenViews = [self.__tableView, self.__thumbnailView]
        self._viewChanged()    

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
            self.__showThumbnailView()
            self._toggleLock = gtk.FALSE

    def _toggleObjectView(self, button):
        if not self._toggleLock:
            self._toggleLock = gtk.TRUE
            button.set_active(gtk.TRUE)
            env.widgets["tableViewToggleButton"].set_active(gtk.FALSE)
            env.widgets["thumbnailsViewToggleButton"].set_active(gtk.FALSE)
            self.__showSingleObjectView()
            self._toggleLock = gtk.FALSE

    def _toggleTableView(self, button):
        if not self._toggleLock:
            self._toggleLock = gtk.TRUE
            button.set_active(gtk.TRUE)
            env.widgets["thumbnailsViewToggleButton"].set_active(gtk.FALSE)
            env.widgets["objectViewToggleButton"].set_active(gtk.FALSE)
            self.__showTableView()
            self._toggleLock = gtk.FALSE

    def _shelfModificationChangedCallback(self, modified):
        env.widgets["revert"].set_sensitive(modified)
        env.widgets["save"].set_sensitive(modified)
