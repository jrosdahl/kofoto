import gtk
import sys
from environment import env
from gnomekofoto.imageview import *
from gnomekofoto.objectcollectionview import *
# from gnomekofoto.singleobjectcontextmenu import *

class SingleObjectView(ObjectCollectionView, ImageView):

###############################################################################            
### Public
    
    def __init__(self, objectCollection):
        ObjectCollectionView.__init__(self,
                                      objectCollection,
                                      env.widgets["objectView"],
                                      None) # TODO create & pass context menu
        ImageView.__init__(self)
        self._viewWidget.add(self)
        self.show_all()
        env.widgets["nextButton"].connect("clicked", self._goto, 1)
        env.widgets["previousButton"].connect("clicked", self._goto, -1)
        env.widgets["zoomToFit"].connect("clicked", self.fitToWindow)
        env.widgets["zoom100"].connect("clicked", self.zoom100)
        env.widgets["zoomIn"].connect("clicked", self.zoomIn)
        env.widgets["zoomOut"].connect("clicked", self.zoomOut)
        self.connect("button_press_event", self._button_pressed)

    def setObjectCollection(self, objectCollection):
        self._clearAllConnections()
        self._objectCollection = objectCollection
        self._connect("row_changed", self.__importSelection)
        self._connect("row_inserted", self.__importSelection)
        self._connect("row_deleted", self.__importSelection)
        self.__importSelection()

    def show(self):
        env.widgets["objectView"].show()
        env.widgets["objectView"].grab_focus()
        env.widgets["zoom100"].set_sensitive(gtk.TRUE)
        env.widgets["zoomToFit"].set_sensitive(gtk.TRUE)
        env.widgets["zoomIn"].set_sensitive(gtk.TRUE)
        env.widgets["zoomOut"].set_sensitive(gtk.TRUE)
        self.__importSelection()

    def hide(self):
        env.widgets["objectView"].hide()
        env.widgets["previousButton"].set_sensitive(gtk.FALSE)
        env.widgets["nextButton"].set_sensitive(gtk.FALSE)
        env.widgets["zoom100"].set_sensitive(gtk.FALSE)
        env.widgets["zoomToFit"].set_sensitive(gtk.FALSE)
        env.widgets["zoomIn"].set_sensitive(gtk.FALSE)
        env.widgets["zoomOut"].set_sensitive(gtk.FALSE)

        
###############################################################################        
### Private        

    def __importSelection(self):
        rows = self._objectCollection.getSelectedRows()
        if rows:
            self.__row = rows[0]
            self._objectCollection.unselectAll(gtk.FALSE)
            self._objectCollection.selectRow(self.__row)
            self.__path = self.__row.path[0]
            object = self._objectCollection.getSelectedObjects()[0]
            if object.isAlbum():
                self.loadFile(env.albumIconFileName)
            else:
                self.loadFile(object.getLocation())
        else:
            self.__row = None
            self.clear()
            self.__path = 0
        if self.__path <= 0:
            env.widgets["previousButton"].set_sensitive(gtk.FALSE)
        else: 
            env.widgets["previousButton"].set_sensitive(gtk.TRUE)
        if self.__path >= len(self._objectCollection.getModel()) - 1:
            env.widgets["nextButton"].set_sensitive(gtk.FALSE)
        else:
            env.widgets["nextButton"].set_sensitive(gtk.TRUE)

    def _goto(self, button, direction):
        newRow = self._objectCollection.getModel()[self.__path + direction]
        self._objectCollection.unselectAll(gtk.FALSE)
        self._objectCollection.selectRow(newRow)
        self.__importSelection()
