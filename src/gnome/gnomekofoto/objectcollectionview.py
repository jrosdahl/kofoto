import gtk
from environment import env
from menuhandler import *
from objectcollection import *

class ObjectCollectionView:

###############################################################################            
### Public
    
    def __init__(self, view):
        self._viewWidget = view
        self._objectCollection = None
        self._contextMenu = None
        self.__objectCollectionLoaded = False
        self.__hidden = True
        self.__connections = []        
        view.connect("button_press_event", self._mouse_button_pressed)

    def freeze(self):
        pass

    def thaw(self):
        pass
        
    def show(self, objectCollection):
        if self.__hidden:
            self.__hidden = False
            self._connectObjectCollection(objectCollection)
        else:
            self.setObjectCollection(objectCollection)
        
    def hide(self):
        if not self.__hidden:
            self.__hidden = True
            self._disconnectObjectCollection()
    
    def setObjectCollection(self, objectCollection):
        if not self.__hidden:
            env.debug("ObjectCollectionView sets object collection")
            self._connectObjectCollection(objectCollection)

    def sortOrderChanged(self, sortOrder):
        env.debug("Sort order is " + str(sortOrder))
        self.__sortMenuGroup[sortOrder].activate()
        
    def sortColumnChanged(self, sortColumn):
        env.debug("Sort column is " + str(sortColumn))
        self.__sortMenuGroup[sortColumn].activate()

    def fieldsDisabled(self, fields):
        pass
        
    def fieldsEnabled(self, fields):
        pass

    def _mouse_button_pressed(self, widget, event):
        if event.button == 3:
            self._contextMenu.popup(None, None, None, event.button, event.time)
            return True
        
##############################################################################
### Methods used by and overloaded by subbclasses

    def _connectObjectCollection(self, objectCollection):
        if self._objectCollection != None:
            self._disconnectObjectCollection()
        self._objectCollection = objectCollection
        self._createContextMenu(objectCollection)
        self._objectCollection.registerView(self)

    def _disconnectObjectCollection(self):
        if self._objectCollection is not None:
            self._objectCollection.unRegisterView(self)
            self._clearContextMenu()
            self._objectCollection = None
        
    def _connect(self, object, signal, function):
        id = object.connect(signal, function)
        self.__connections.append((object, id))

    def _clearAllConnections(self):
        for (object, id) in self.__connections:
            object.disconnect(id)
        self.__connections = []

    def _createContextMenu(self, objectCollection):
        env.debug("Creating view context menu")
        self._contextMenu = gtk.Menu()
        self.__sortMenuGroup = self.__createSortMenuGroup(objectCollection)
        self._contextMenu.add(self.__sortMenuGroup.createGroupMenuItem())

    def _clearContextMenu(self):
        env.debug("Clearing view context menu")
        self._contextMenu = None
        self.__sortMenuGroup = None

###############################################################################        
### Private

    def __createSortMenuGroup(self, objectCollection):
        menuGroup = MenuGroup("Sort by")
        if objectCollection.isSortable():
            env.debug("Creating sort menu group for sortable log collection")
            menuGroup.addRadioMenuItem("Ascending",
                                       objectCollection.setSortOrder,
                                       gtk.SORT_ASCENDING)
            menuGroup.addRadioMenuItem("Descending",
                                       objectCollection.setSortOrder,                            
                                       gtk.SORT_DESCENDING)
            menuGroup.addSeparator()
            objectMetadataMap = objectCollection.getObjectMetadataMap()
            columnNames = list(objectMetadataMap.keys())
            columnNames.sort()
            for columnName in columnNames:
                if objectMetadataMap[columnName][ObjectCollection.TYPE] != gtk.gdk.Pixbuf:
                    menuGroup.addRadioMenuItem(columnName,
                                               objectCollection.setSortColumnName,
                                               columnName)
        return menuGroup
