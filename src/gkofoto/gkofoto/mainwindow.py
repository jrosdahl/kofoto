import gtk
import gtk.gdk
import os

from gkofoto.categories import *
from gkofoto.albums import *
from environment import env
from gkofoto.tableview import *
from gkofoto.thumbnailview import *
from gkofoto.singleobjectview import *
from gkofoto.objectcollectionfactory import *
from gkofoto.objectcollection import *
from gkofoto.registerimagesdialog import RegisterImagesDialog
from gkofoto.handleimagesdialog import HandleImagesDialog
from gkofoto.generatehtmldialog import GenerateHTMLDialog
from gkofoto.persistentstate import PersistentState
from gkofoto.imagepreloader import ImagePreloader

class MainWindow(gtk.Window):
    def __init__(self):
        env.mainwindow = self
        self._toggleLock = False
        self.__currentObjectCollection = None
        self._currentView = None
        self.__persistentState = PersistentState()
        self.__imagePreloader = ImagePreloader(env.codeset, env.debug)
        self.__sourceEntry = env.widgets["sourceEntry"]
        self.__filterEntry = env.widgets["filterEntry"]
        self.__filterEntry.set_text(self.__persistentState.filterText)
        self.__isFilterEnabledCheckbox = env.widgets["isFilterEnabledCheckbox"]
        env.widgets["expandViewToggleButton"].connect("toggled", self._toggleExpandView)
        env.widgets["expandViewToggleButton"].get_child().add(self.getIconImage("fullscreen-24.png"))
#        env.widgets["thumbnailsViewToggleButton"].connect("clicked", self._toggleThumbnailsView)
        env.widgets["thumbnailsViewToggleButton"].hide()
        env.widgets["thumbnailsViewToggleButton"].set_sensitive(False)
        env.widgets["thumbnailsViewToggleButton"].get_child().add(self.getIconImage("thumbnailsview.png"))
        env.widgets["objectViewToggleButton"].connect("clicked", self._toggleObjectView)
        env.widgets["objectViewToggleButton"].get_child().add(self.getIconImage("objectview.png"))
        env.widgets["menubarObjectView"].connect("activate", self._toggleObjectView)
        env.widgets["tableViewToggleButton"].connect("clicked", self._toggleTableView)
        env.widgets["tableViewToggleButton"].get_child().add(self.getIconImage("tableview.png"))
        env.widgets["menubarTableView"].connect("activate", self._toggleTableView)
        env.widgets["previousButton"].set_sensitive(False)
        env.widgets["nextButton"].set_sensitive(False)
        env.widgets["zoom100"].set_sensitive(False)
        env.widgets["zoomToFit"].set_sensitive(False)
        env.widgets["zoomIn"].set_sensitive(False)
        env.widgets["zoomOut"].set_sensitive(False)

        env.widgets["menubarSave"].connect("activate", env.controller.save)
        env.widgets["menubarSave"].set_sensitive(False)
        env.widgets["menubarRevert"].connect("activate", env.controller.revert)
        env.widgets["menubarRevert"].set_sensitive(False)
        env.widgets["menubarQuit"].connect("activate", env.controller.quit)

        env.widgets["menubarThumbnailsView"].hide()

        env.widgets["menubarNextImage"].set_sensitive(False)
        env.widgets["menubarPreviousImage"].set_sensitive(False)
        env.widgets["menubarZoom"].set_sensitive(False)

        env.widgets["menubarRegisterImages"].connect("activate", self.registerImages, None)
        env.widgets["menubarHandleModifiedOrRenamedImages"].connect(
            "activate", self.handleModifiedOrRenamedImages, None)

        env.widgets["menubarRotateLeft"].get_children()[1].set_from_pixbuf(
            gtk.gdk.pixbuf_new_from_file(os.path.join(env.iconDir, "rotateleft.png")))
        env.widgets["menubarRotateRight"].get_children()[1].set_from_pixbuf(
            gtk.gdk.pixbuf_new_from_file(os.path.join(env.iconDir, "rotateright.png")))
        env.widgets["menubarAbout"].get_children()[1].set_from_pixbuf(
            gtk.gdk.pixbuf_new_from_file(os.path.join(env.iconDir, "about-icon.png")))

        env.widgets["menubarAbout"].connect("activate", self.showAboutBox)

        self.__sourceEntry.connect("activate", self._queryChanged)
        self.__filterEntry.connect("activate", self._queryChanged)
        self.__isFilterEnabledCheckbox.connect("toggled", self._queryChanged)

        env.shelf.registerModificationCallback(self._shelfModificationChangedCallback)

        self.__factory = ObjectCollectionFactory()
        self.__categories = Categories(self)
        self.__albums = Albums(self)
        self.__thumbnailView = ThumbnailView()
        self.__tableView = TableView()
        self.__singleObjectView = SingleObjectView()
        self.__showTableView()

    def saveState(self):
        self.__persistentState.save()

    def _queryChanged(self, *foo):
        query = self.__sourceEntry.get_text().decode("utf-8")
        self.loadQuery(query)
        self.__sourceEntry.grab_remove()
        self.__persistentState.filterText = self.__filterEntry.get_text()

    def loadQuery(self, query):
        self.__query = query
        self.__sourceEntry.set_text(query)
        useFilter = self.__isFilterEnabledCheckbox.get_active()
        self.__filterEntry.set_sensitive(useFilter)
        if useFilter:
            filterText = self.__filterEntry.get_text().decode("utf-8")
        else:
            filterText = ""
        self.__setObjectCollection(
            self.__factory.getObjectCollection(query, filterText))

    def reload(self):
        self.__albums.loadAlbumTree()
        self.__categories.loadCategoryTree()
        self.loadQuery(self.__query)

    def reloadObjectList(self):
        self.loadQuery(self.__query)

    def reloadAlbumTree(self):
        self.__albums.loadAlbumTree()

    def unselectAlbumTree(self):
        self.__albums.unselect()

    def registerImages(self, widget, data):
        dialog = RegisterImagesDialog()
        if dialog.run() == gtk.RESPONSE_OK:
            self.reload() # TODO: don't reload everything.
        dialog.destroy()

    def handleModifiedOrRenamedImages(self, widget, data):
        dialog = HandleImagesDialog()
        dialog.run()
        dialog.destroy()

    def showAboutBox(self, *unused):
        widgets = gtk.glade.XML(env.gladeFile, "aboutDialog")
        aboutDialog = widgets.get_widget("aboutDialog")
        nameAndVersionLabel = widgets.get_widget("nameAndVersionLabel")
        nameAndVersionLabel.set_text("Kofoto %s" % env.version)
        aboutDialog.run()
        aboutDialog.destroy()

    def generateHtml(self, album):
        dialog = GenerateHTMLDialog(album)
        dialog.run()

    def getIconImage(self, name):
        pixbuf = gtk.gdk.pixbuf_new_from_file(os.path.join(env.iconDir, name))
        image = gtk.Image()
        image.set_from_pixbuf(pixbuf)
        image.show()
        return image

    def getImagePreloader(self):
        return self.__imagePreloader

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
            env.widgets["thumbnailsViewToggleButton"].set_active(True)
            env.widgets["objectViewToggleButton"].set_active(False)
            env.widgets["tableViewToggleButton"].set_active(False)
            env.widgets["menubarThumbnailsView"].set_active(True)
            env.widgets["menubarObjectView"].set_active(False)
            env.widgets["menubarTableView"].set_active(False)
            self.__showThumbnailView()
            self._toggleLock = False

    def _toggleObjectView(self, button):
        if not self._toggleLock:
            self._toggleLock = True
            button.set_active(True)
            env.widgets["thumbnailsViewToggleButton"].set_active(False)
            env.widgets["objectViewToggleButton"].set_active(True)
            env.widgets["tableViewToggleButton"].set_active(False)
            env.widgets["menubarThumbnailsView"].set_active(False)
            env.widgets["menubarObjectView"].set_active(True)
            env.widgets["menubarTableView"].set_active(False)
            self.__showSingleObjectView()
            self._toggleLock = False

    def _toggleTableView(self, button):
        if not self._toggleLock:
            self._toggleLock = True
            button.set_active(True)
            env.widgets["thumbnailsViewToggleButton"].set_active(False)
            env.widgets["objectViewToggleButton"].set_active(False)
            env.widgets["tableViewToggleButton"].set_active(True)
            env.widgets["menubarThumbnailsView"].set_active(False)
            env.widgets["menubarObjectView"].set_active(False)
            env.widgets["menubarTableView"].set_active(True)
            self.__showTableView()
            self._toggleLock = False

    def _shelfModificationChangedCallback(self, modified):
        env.widgets["menubarRevert"].set_sensitive(modified)
        env.widgets["menubarSave"].set_sensitive(modified)
        env.widgets["statusbarModified"].pop(1)
        if modified:
            env.widgets["statusbarModified"].push(1, "Modified")

    def __setObjectCollection(self, objectCollection):
        if self.__currentObjectCollection != objectCollection:
            env.debug("MainWindow is propagating a new ObjectCollection")
            self.__currentObjectCollection = objectCollection
            self.__categories.setCollection(objectCollection)
            if self._currentView is not None:
                self._currentView.setObjectCollection(objectCollection)
