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

    def show(self, objectCollection):
        if self.__hidden:
            self.__hidden = False
            self.__connectObjectCollection(objectCollection)
            self._showHelper()            
        else:
            self.setObjectCollection(objectCollection)
        
    def hide(self):
        if not self.__hidden:
            self.__hidden = True
            self._hideHelper()
            self.__disconnectObjectCollection()
    
    def setObjectCollection(self, objectCollection):
        if not self.__hidden:
            env.debug("ObjectCollectionView sets object collection")
            self.__connectObjectCollection(objectCollection)
        
    def freeze(self):
        self._freezeHelper()
        self._objectCollection.getObjectSelection().removeChangedCallback(self.importSelection)
        env.clipboard.removeChangedCallback(self._updateContextMenu)        

    def thaw(self):
        self._thawHelper()
        self._objectCollection.getObjectSelection().addChangedCallback(self.importSelection)
        env.clipboard.addChangedCallback(self._updateContextMenu)
        self.importSelection(self._objectCollection.getObjectSelection())
        # importSelection makes an implicit _updateContextMenu()

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
        self.__clipboardMenuGroup = self.__createClipboardMenuGroup(objectCollection)
        for item in self.__clipboardMenuGroup:
            self._contextMenu.add(item)
        self.__sortMenuGroup = self.__createSortMenuGroup(objectCollection)
        self._contextMenu.add(self.__sortMenuGroup.createGroupMenuItem())
        
    def _clearContextMenu(self):
        env.debug("Clearing view context menu")
        self._contextMenu = None
        self.__sortMenuGroup = None
        self.__clipboardMenuGroup = None

    def _updateContextMenu(self, *foo):
        env.debug("Updating context menu")
        mutable = self._objectCollection.isMutable()
        if env.clipboard.hasObjects():
            self.__clipboardMenuGroup[self._objectCollection.getPasteLabel()].set_sensitive(mutable)
        else:
            self.__clipboardMenuGroup[self._objectCollection.getPasteLabel()].set_sensitive(False)
        if len(self._objectCollection.getObjectSelection()) > 0:
            self.__clipboardMenuGroup[self._objectCollection.getCopyLabel()].set_sensitive(True)
            self.__clipboardMenuGroup[self._objectCollection.getCutLabel()].set_sensitive(mutable)
            self.__clipboardMenuGroup[self._objectCollection.getDeleteLabel()].set_sensitive(mutable)
        else:
            self.__clipboardMenuGroup[self._objectCollection.getCopyLabel()].set_sensitive(False)
            self.__clipboardMenuGroup[self._objectCollection.getCutLabel()].set_sensitive(False)
            self.__clipboardMenuGroup[self._objectCollection.getDeleteLabel()].set_sensitive(False)
            
###############################################################################        
### Private

    def __connectObjectCollection(self, objectCollection):
        if self._objectCollection != None:
            self.__disconnectObjectCollection()
        self._objectCollection = objectCollection
        self._createContextMenu(objectCollection)
        self._connectObjectCollectionHelper()
        self.thaw()
        self._objectCollection.registerView(self)

    def __disconnectObjectCollection(self):
        if self._objectCollection is not None:
            self._objectCollection.unRegisterView(self)
            self.freeze()
            self._disconnectObjectCollectionHelper()
            self._clearContextMenu()
            self._objectCollection = None
        
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
            objectMetadataMap = objectCollection.getObjectMetadataMap()
            columnNames = list(objectMetadataMap.keys())
            columnNames.sort()
            for columnName in columnNames:
                if objectMetadataMap[columnName][ObjectCollection.TYPE] != gtk.gdk.Pixbuf:
                    menuGroup.addRadioMenuItem(columnName,
                                               objectCollection.setSortColumnName,
                                               columnName)
        return menuGroup

    def __createClipboardMenuGroup(self, oc):
        menuGroup = MenuGroup()
        env.debug("Creating clipboard menu")
        menuGroup.addMenuItem(oc.getCutLabel(), oc.cut)
        menuGroup.addMenuItem(oc.getCopyLabel(), oc.copy)
        menuGroup.addMenuItem(oc.getPasteLabel(), oc.paste)
        menuGroup.addMenuItem(oc.getDeleteLabel(), oc.delete)
        menuGroup.addSeparator()
        return menuGroup    
