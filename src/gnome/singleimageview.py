# -*- coding: iso-8859-1 -*-

import gtk
import sys

from environment import env
from images import *
from imageview import *

# TODO: Prenumerera på model changes för att veta när tex en bild roterats

class SingleImageView(ImageView):
    _modelConnections = []
    
    def __init__(self, loadedImages, selectedImages, contextMenu):
        ImageView.__init__(self)
        self._locked = gtk.FALSE
        self._freezed = gtk.FALSE
        env.widgets["imageView"].add(self)
        self.show_all()
        self._selectedImages = selectedImages
        self._contextMenu = contextMenu
        env.widgets["nextButton"].connect("clicked", self._goto, 1)
        env.widgets["previousButton"].connect("clicked", self._goto, -1)
        env.widgets["zoomToFit"].connect("clicked", self.fitToWindow)
        env.widgets["zoom100"].connect("clicked", self.zoom100)
        env.widgets["zoomIn"].connect("clicked", self.zoomIn)
        env.widgets["zoomOut"].connect("clicked", self.zoomOut)
        self.connect("button_press_event", self._button_pressed)
        self.setModel(loadedImages)
    
    def setModel(self, loadedImages):
        for c in self._modelConnections:
            self._model.disconnect(c)
        del self._modelConnections[:]
        self._model = loadedImages.model
        c = self._model.connect("row_inserted", self._modelRowsChanged)
        self._modelConnections.append(c)
        c = self._model.connect("row_changed", self.selectionUpdated)
        self._modelConnections.append(c)
        c = self._model.connect("row_deleted", self._modelRowsChanged)
        self._modelConnections.append(c)
        self._modelRowsChanged()

    def _modelRowsChanged(self, *foo):
        if len(self._selectedImages) != 0:
            self._selectedImages.clear()
        self.selectionUpdated()
        
    def selectionUpdated(self, *foo):
        if not self._freezed and not self._locked:
            self._locked = gtk.TRUE
            try:
                if len(self._selectedImages) == 0:
                    imageId = self._model[0][Images.COLUMN_IMAGE_ID]
                    self._selectedImages.set([imageId])
                else:
                    imageId = list(self._selectedImages)[0]
                    self._selectedImages.set([imageId])
                self._imageId = imageId
                self._updateButtons(self._getRow())
                self._loadImage()
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
            self._imageId = self._model[row][Images.COLUMN_IMAGE_ID]
            self._loadImage()
            self._selectedImages.set([self._imageId])
            self._locked = gtk.FALSE

    def _getRow(self):
        for image in self._model:
            if image[Images.COLUMN_IMAGE_ID] == self._imageId:
                return image.path[0]
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
            
    def _loadImage(self):
        image = env.shelf.getImage(self._imageId)
        self.loadFile(image.getLocation())
        
    def freeze(self):
        self._freezed = gtk.TRUE

    def thaw(self):
        self._freezed = gtk.FALSE
        self.selectionUpdated()

    def show(self):
        self.thaw()
        env.widgets["imageView"].show()
        env.widgets["imageView"].grab_focus()
        env.widgets["zoom100"].set_sensitive(gtk.TRUE)
        env.widgets["zoomToFit"].set_sensitive(gtk.TRUE)
        env.widgets["zoomIn"].set_sensitive(gtk.TRUE)
        env.widgets["zoomOut"].set_sensitive(gtk.TRUE)
        self.thaw()

    def hide(self):
        self.freeze()
        self.clear()
        env.widgets["imageView"].hide()
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
