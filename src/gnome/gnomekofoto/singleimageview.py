# -*- coding: iso-8859-1 -*-

import gtk
import sys

from environment import env
from objects import *
from imageview import *

# TODO: Prenumerera på model changes för att veta när tex en bild roterats

class SingleImageView(ImageView):
    _modelConnections = []
    
    def __init__(self, loadedObjects, selectedObjects, contextMenu):
        ImageView.__init__(self)
        self._locked = gtk.FALSE
        self._freezed = gtk.FALSE
        env.widgets["objectView"].add(self)
        self.show_all()
        self._selectedObjects = selectedObjects
        self._contextMenu = contextMenu
        env.widgets["nextButton"].connect("clicked", self._goto, 1)
        env.widgets["previousButton"].connect("clicked", self._goto, -1)
        env.widgets["zoomToFit"].connect("clicked", self.fitToWindow)
        env.widgets["zoom100"].connect("clicked", self.zoom100)
        env.widgets["zoomIn"].connect("clicked", self.zoomIn)
        env.widgets["zoomOut"].connect("clicked", self.zoomOut)
        self.connect("button_press_event", self._button_pressed)
        self.setModel(loadedObjects)
    
    def setModel(self, loadedObjects):
        for c in self._modelConnections:
            self._model.disconnect(c)
        del self._modelConnections[:]
        self._model = loadedObjects.model
        c = self._model.connect("row_inserted", self._modelRowsChanged)
        self._modelConnections.append(c)
        c = self._model.connect("row_changed", self.selectionUpdated)
        self._modelConnections.append(c)
        c = self._model.connect("row_deleted", self._modelRowsChanged)
        self._modelConnections.append(c)
        self._modelRowsChanged()

    def _modelRowsChanged(self, *foo):
        if len(self._selectedObjects) != 0:
            self._selectedObjects.clear()
        self.selectionUpdated()
        
    def selectionUpdated(self, *foo):
        if not self._freezed and not self._locked:
            self._locked = gtk.TRUE
            try:
                if len(self._selectedObjects) == 0:
                    objectId = self._model[0][Objects.COLUMN_OBJECT_ID]
                    self._selectedObjects.set([objectId])
                else:
                    objectId = list(self._selectedObjects)[0]
                    self._selectedObjects.set([objectId])
                self._objectId = objectId
                self._updateButtons(self._getRow())
                self._loadObject()
            except(IndexError):
                self.clear()
                env.widgets["previousButton"].set_sensitive(gtk.FALSE)
                env.widgets["nextButton"].set_sensitive(gtk.FALSE)
            self._locked = gtk.FALSE

    def _goto(self, button, direction):
        if not self._locked:
            self._locked = gtk.TRUE        
            row = self._getRow() + direction
            self._updateButtons(row)
            self._objectId = self._model[row][Objects.COLUMN_OBJECT_ID]
            self._loadObject()
            self._selectedObjects.set([self._objectId])
            self._locked = gtk.FALSE

    def _getRow(self):
        for object in self._model:
            if object[Objects.COLUMN_OBJECT_ID] == self._objectId:
                return object.path[0]
        raise IndexError

    def _updateButtons(self, row):
        if row <= 0:
            env.widgets["previousButton"].set_sensitive(gtk.FALSE)
        else: 
            env.widgets["previousButton"].set_sensitive(gtk.TRUE)
        if row >= len(self._model) - 1:
            env.widgets["nextButton"].set_sensitive(gtk.FALSE)
        else:
            env.widgets["nextButton"].set_sensitive(gtk.TRUE)
            
    def _loadObject(self):
        object = env.shelf.getObject(self._objectId)
        if object.isAlbum():
            self.loadFile(env.albumIconFileName)
        else:
            self.loadFile(object.getLocation())
        
    def freeze(self):
        self._freezed = gtk.TRUE

    def thaw(self):
        self._freezed = gtk.FALSE
        self.selectionUpdated()

    def show(self):
        self.thaw()
        env.widgets["objectView"].show()
        env.widgets["objectView"].grab_focus()
        env.widgets["zoom100"].set_sensitive(gtk.TRUE)
        env.widgets["zoomToFit"].set_sensitive(gtk.TRUE)
        env.widgets["zoomIn"].set_sensitive(gtk.TRUE)
        env.widgets["zoomOut"].set_sensitive(gtk.TRUE)
        self.thaw()

    def hide(self):
        self.freeze()
        self.clear()
        env.widgets["objectView"].hide()
        env.widgets["previousButton"].set_sensitive(gtk.FALSE)
        env.widgets["nextButton"].set_sensitive(gtk.FALSE)
        env.widgets["zoom100"].set_sensitive(gtk.FALSE)
        env.widgets["zoomToFit"].set_sensitive(gtk.FALSE)
        env.widgets["zoomIn"].set_sensitive(gtk.FALSE)
        env.widgets["zoomOut"].set_sensitive(gtk.FALSE)
        self.freeze()

    def _button_pressed(self, widget, event):
        if event.button == 3:
            if self._contextMenu:
                self._contextMenu.popup(None,None,None,event.button,event.time)
            return gtk.TRUE
