import gtk
import sys

from environment import env
from objects import *

class ThumbnailView:
    _maxWidth = 0
    _modelConnections = []
    _blockedConnections = []
    _freezed = gtk.FALSE
    
    def __init__(self, loadedObjects, selectedObjects, contextMenu):
        self._locked = gtk.FALSE
        self._contextMenu = contextMenu
        self._selectedObjects = selectedObjects
        widget = env.widgets["thumbnailList"]
        self._thumbnailList = env.widgets["thumbnailList"]        
        widget.connect("select_icon", self._widgetIconSelected)
        widget.connect("unselect_icon", self._widgetIconUnselected)
        widget.connect("button_press_event", self._button_pressed)
        self.setModel(loadedObjects)
        
    def setModel(self, loadedObjects):
        for c in self._modelConnections:
            self._model.disconnect(c)
        del self._modelConnections[:]
        del self._blockedConnections[:]
        self._model = loadedObjects.model
        self._initFromModel()
        c = self._model.connect("row_inserted", self._initFromModel)
        self._modelConnections.append(c)
        c = self._model.connect("row_changed", self.on_row_changed)
        self._modelConnections.append(c)
        c = self._model.connect("row_deleted", self._initFromModel)
        self._modelConnections.append(c)
        c = self._model.connect("rows_reordered", self._initFromModel)
        self._modelConnections.append(c)

    def _initFromModel(self, *garbage):
        self._thumbnailList.clear()
        iter = self._model.get_iter_first()
        for pos in range(self._model.iter_n_children(None)):
            self._loadThumbnail(self._model, iter, pos)
            iter = self._model.iter_next(iter)
        self.selectionUpdated()
        
    def _blockModel(self):
        for c in self._modelConnections:
            self._model.handler_block(c)
            self._blockedConnections.append(c)

    def _unblockModel(self):
        self._initFromModel()
        for c in self._blockedConnections:
            self._model.handler_unblock(c)
        del self._blockedConnections[:]

    def _loadThumbnail(self, model, iter, pos):
        isAlbum = model.get_value(iter, Objects.COLUMN_IS_ALBUM)
        if isAlbum:
            text = model.get_value(iter, Objects.COLUMN_ALBUM_TAG)
        else:
            text = model.get_value(iter, Objects.COLUMN_OBJECT_ID)
        pixbuf = model.get_value(iter, Objects.COLUMN_THUMBNAIL)
        self._thumbnailList.insert_pixbuf(pos, pixbuf, "", str(text))
        self._maxWidth = max(self._maxWidth, pixbuf.get_width())
        self._thumbnailList.set_icon_width(self._maxWidth)

        

    def freeze(self):
        self._thumbnailList.freeze()
        self._blockModel()

    def thaw(self):
        self._thumbnailList.thaw()
        self._unblockModel()

    def show(self):
        self._locked = gtk.TRUE
        self._thumbnailList.unselect_all()
        self._locked = gtk.FALSE
        env.widgets["thumbnailView"].show()
        env.widgets["thumbnailList"].grab_focus()
        self._unblockModel()
        for object in self._model:
            if object[Objects.COLUMN_OBJECT_ID] in self._selectedObjects:
                env.widgets["thumbnailList"].moveto(object.path[0], 0.0)
                break

    def hide(self):
        env.widgets["thumbnailView"].hide()
        self._blockModel()
        
    def on_row_changed(self, model, path, iter):
        self._locked = gtk.TRUE
        self._thumbnailList.remove(path[0])
        self._loadThumbnail(model, iter, path[0])
        self._locked = gtk.FALSE
        self.selectionUpdated()
        
    def _widgetIconSelected(self, widget, index, event):
        if not self._locked:
            self._locked = gtk.TRUE
            iter = self._model.get_iter(index)
            objectId = self._model.get_value(iter, Objects.COLUMN_OBJECT_ID)
            self._selectedObjects.add(objectId)
            self._locked = gtk.FALSE

    def _widgetIconUnselected(self, widget, index, event):
        if not self._locked:
            self._locked = gtk.TRUE        
            iter = self._model.get_iter(index)
            objectId = self._model.get_value(iter, Objects.COLUMN_OBJECT_ID)
            try:
                self._selectedObjects.remove(objectId)
            except(KeyError):
                pass
            self._locked = gtk.FALSE

    def selectionUpdated(self):
        if not self._locked:
            self._locked = gtk.TRUE        
            self._thumbnailList.unselect_all()
            if len(self._model) > 0:
                indices = xrange(sys.maxint)                
                for object, index in zip(self._model, indices):
                    if object[Objects.COLUMN_OBJECT_ID] in self._selectedObjects:
                        self._thumbnailList.select_icon(index)
            self._locked = gtk.FALSE            

    def _button_pressed(self, widget, event):
        if event.button == 3:
            if self._contextMenu:
                self._contextMenu.popup(None,None,None,event.button,event.time)
            return gtk.FALSE
