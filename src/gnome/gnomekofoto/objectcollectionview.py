import gtk

from environment import env
from sets import Set

class ObjectCollectionView:

###############################################################################            
### Public
    
    def __init__(self, objectCollection, view, contextMenu):
        self._objectCollection = objectCollection
        self._contextMenu = contextMenu
        self._viewWidget = view
        self.setObjectCollection(objectCollection)
        view.connect("button_press_event", self._button_pressed)

    def freeze(self):
        pass

    def thaw(self):
        pass

    def setObjectCollection(self, objectCollection):
        self._clearAllConnections
        self._objectCollection = objectCollection
    
###############################################################################
### Only for subbclasses

    _objectCollection = None
    _contextMenu = None
    _viewWidget = None
    
    def _connect(self, signal, function):
        model = self._objectCollection.getModel()
        c = model.connect(signal, function)
        self.__connections.append(c)

    def _clearAllConnections(self):
        model = self._objectCollection.getModel()
        for c in self.__connections:
            model.disconnect(c)
        self.__connections = []

        
###############################################################################
### Callback functions registered by this class but invoked from other classes.
        
    def _button_pressed(self, widget, event):
        if event.button == 3:
            self._contextMenu.popup(None, None, None, event.button, event.time)
            return gtk.TRUE    

        
###############################################################################        
### Private
        
    __connections = []
