import gtk
import gtk.gdk
import os

from gnomekofoto.categories import *
from gnomekofoto.albums import *
from environment import env
from gnomekofoto.tableview import *
from gnomekofoto.thumbnailview import *
from gnomekofoto.singleobjectview import *
from gnomekofoto.objectcollectionfactory import *
from gnomekofoto.objectcollection import *

class MainWindow(gtk.Window):
    def __init__(self):
        self._toggleLock = False
        self.__currentObjectCollection = None
        self._currentView = None
        self.__sourceEntry = env.widgets["sourceEntry"]
        env.widgets["expandViewToggleButton"].connect("toggled", self._toggleExpandView)
        env.widgets["expandViewToggleButton"].get_child().add(self.getIconImage("fullscreen-24.png"))
#        env.widgets["thumbnailsViewToggleButton"].connect("clicked", self._toggleThumbnailsView)
        env.widgets["thumbnailsViewToggleButton"].get_child().add(self.getIconImage("thumbnailsview.png"))
        env.widgets["objectViewToggleButton"].connect("clicked", self._toggleObjectView)
        env.widgets["objectViewToggleButton"].get_child().add(self.getIconImage("objectview.png"))
        env.widgets["tableViewToggleButton"].connect("clicked", self._toggleTableView)
        env.widgets["tableViewToggleButton"].get_child().add(self.getIconImage("tableview.png"))
        env.widgets["save"].connect("activate", env.controller.save)
        env.widgets["revert"].connect("activate", env.controller.revert)
        env.widgets["quit"].connect("activate", env.controller.quit)
        env.widgets["save"].set_sensitive(False)
        env.widgets["revert"].set_sensitive(False)
        self.__sourceEntry.connect("activate", self._sourceEntryActivated)

        env.shelf.registerModificationCallback(self._shelfModificationChangedCallback)

        self.__albums = Albums(self)
        self.__categories = Categories(self)
        self.__thumbnailView = ThumbnailView()
        self.__tableView = TableView()
        self.__singleObjectView = SingleObjectView()
        self.__factory = ObjectCollectionFactory()
        self.loadUrl("album://" + str(env.shelf.getRootAlbum().getTag()))
        self.__showTableView()

    def _sourceEntryActivated(self, widget):
        self.__setObjectCollection(self.__factory.getObjectCollection(widget.get_text()))
        self.__sourceEntry.grab_remove()
        
    def setUrl(self, url):
        self.__url = url
        self.__sourceEntry.set_text(url)
        
    def loadUrl(self, url):
        self.setUrl(url)
        self.__setObjectCollection(self.__factory.getObjectCollection(url))

    def reload(self):
        self.__albums.loadAlbumTree()
        self.__categories.loadCategoryTree()
        self.loadUrl(self.__url)
        
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

    def __setObjectCollection(self, objectCollection):
        if self.__currentObjectCollection != objectCollection:
            env.debug("MainWindow is propagating a new ObjectCollection")
            self.__currentObjectCollection = objectCollection
            self.__categories.setCollection(objectCollection)
            if self._currentView is not None:
                self._currentView.setObjectCollection(objectCollection)

        
