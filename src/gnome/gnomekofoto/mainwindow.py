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
    def __init__(self, objectCollection):
        self._toggleLock = False
        self.__currentObjectCollection = None
        self._currentView = None
        env.widgets["expandViewToggleButton"].connect("toggled", self._toggleExpandView)
        env.widgets["expandViewToggleButton"].get_child().add(self.getIconImage("fullscreen-24.png"))
        env.widgets["thumbnailsViewToggleButton"].connect("clicked", self._toggleThumbnailsView)
        env.widgets["objectViewToggleButton"].connect("clicked", self._toggleObjectView)
        env.widgets["tableViewToggleButton"].connect("clicked", self._toggleTableView)
        env.widgets["save"].connect("activate", env.controller.save)
        env.widgets["revert"].connect("activate", env.controller.revert)
        env.widgets["quit"].connect("activate", env.controller.quit)
        env.widgets["save"].set_sensitive(False)
        env.widgets["revert"].set_sensitive(False)

        # Gray out not yet implemented stuff...
        env.widgets["new"].set_sensitive(False)
        env.widgets["open"].set_sensitive(False)
        env.widgets["save_as"].set_sensitive(False)

        env.shelf.registerModificationCallback(self._shelfModificationChangedCallback)

        self.__albums = Albums()
        self.__categories = Categories(objectCollection)
        self.__thumbnailView = ThumbnailView()
        self.__tableView = TableView()
        self.__singleObjectView = SingleObjectView()
        self.setObjectCollection(objectCollection)
        self.__showThumbnailView()

    def setObjectCollection(self, objectCollection):
        if self.__currentObjectCollection != objectCollection:
            env.debug("MainWindow is propagating a new ObjectCollection")
            self.__currentObjectCollection = objectCollection
            self.__categories.setCollection(objectCollection)
            if self._currentView is not None:
                self._currentView.setObjectCollection(objectCollection)

    def getIconImage(self, name):
        pixbuf = gtk.gdk.pixbuf_new_from_file(os.path.join(env.iconDir, name))
        image = gtk.Image()
        image.set_from_pixbuf(pixbuf)
        image.show()
        return image

    def _viewChanged(self):
        for hiddenView in self._hiddenViews:
            hiddenView.hide()
        self._currentView.show(self.__currentObjectCollection)

    def __showTableView(self):
        self._currentView = self.__tableView
        self._hiddenViews = [self.__thumbnailView, self.__singleObjectView]
        self._viewChanged()

    def __showThumbnailView(self):
        self._currentView = self.__thumbnailView
        self._hiddenViews = [self.__tableView, self.__singleObjectView]
        self._viewChanged()

    def __showSingleObjectView(self):
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
            self._toggleLock = True
            button.set_active(True)
            env.widgets["objectViewToggleButton"].set_active(False)
            env.widgets["tableViewToggleButton"].set_active(False)
            self.__showThumbnailView()
            self._toggleLock = False

    def _toggleObjectView(self, button):
        if not self._toggleLock:
            self._toggleLock = True
            button.set_active(True)
            env.widgets["tableViewToggleButton"].set_active(False)
            env.widgets["thumbnailsViewToggleButton"].set_active(False)
            self.__showSingleObjectView()
            self._toggleLock = False

    def _toggleTableView(self, button):
        if not self._toggleLock:
            self._toggleLock = True
            button.set_active(True)
            env.widgets["thumbnailsViewToggleButton"].set_active(False)
            env.widgets["objectViewToggleButton"].set_active(False)
            self.__showTableView()
            self._toggleLock = False

    def _shelfModificationChangedCallback(self, modified):
        env.widgets["revert"].set_sensitive(modified)
        env.widgets["save"].set_sensitive(modified)
