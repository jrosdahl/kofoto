import gtk
import sys

from environment import env
from images import *
from imageview import *

class SingleImageView(ImageView):
    _model = None
    
    def __init__(self):
        ImageView.__init__(self)
        self._locked = gtk.FALSE
        env.widgets["imageView"].add(self)
        self.show_all()
        env.widgets["nextButton"].connect("clicked", self._next)
        env.widgets["previousButton"].connect("clicked", self._previous)
        env.widgets["zoomToFit"].connect("clicked", self.fitToWindow)
        env.widgets["zoom100"].connect("clicked", self.zoom100)
        env.widgets["zoomIn"].connect("clicked", self.zoomIn)
        env.widgets["zoomOut"].connect("clicked", self.zoomOut)
    
    def setModel(self, model):
        self._model = model

    def loadNewSelection(self):
        if not self._locked:
            self._locked = gtk.TRUE
            try:
                if len(env.controller.selection) == 0:
                    imageId = self._model[0][Images.COLUMN_IMAGE_ID]
                    self._updateSelection(imageId)
                else:
                    imageId = env.controller.selection.pop()
                    self._updateSelection(imageId)
                self._imageId = imageId
                self._updateButtons(self._getRow())
                self._loadImage()
            except(IndexError):
                self.clear()
                env.widgets["previousButton"].set_sensitive(gtk.FALSE)
                env.widgets["nextButton"].set_sensitive(gtk.FALSE)
            self._locked = gtk.FALSE

    def _updateSelection(self, imageId):
        self._locked = gtk.TRUE
        env.controller.selection.clear()
        env.controller.selection.add(imageId)
        env.controller.selectionUpdated()
        self._locked = gtk.FALSE
            
    def _next(self, button):
        row = self._getRow() + 1
        self._updateButtons(row)
        self._imageId = self._model[row][Images.COLUMN_IMAGE_ID]
        self._loadImage()
        self._updateSelection(self._imageId)

    def _previous(self, button):
        row = self._getRow() - 1
        self._updateButtons(row)
        self._imageId = self._model[row][Images.COLUMN_IMAGE_ID]
        self._loadImage()
        self._updateSelection(self._imageId)

    def _getRow(self):
        for image in self._model:
            if image[Images.COLUMN_IMAGE_ID] == self._imageId:
                return image.path[0]
        return None

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
        pass

    def thaw(self):
        pass

    def show(self):
        env.widgets["imageView"].show()
        env.widgets["imageView"].grab_focus()
        env.widgets["zoom100"].set_sensitive(gtk.TRUE)
        env.widgets["zoomToFit"].set_sensitive(gtk.TRUE)
        env.widgets["zoomIn"].set_sensitive(gtk.TRUE)
        env.widgets["zoomOut"].set_sensitive(gtk.TRUE)

    def hide(self):
        self.clear()
        env.widgets["imageView"].hide()
        env.widgets["previousButton"].set_sensitive(gtk.FALSE)
        env.widgets["nextButton"].set_sensitive(gtk.FALSE)
        env.widgets["zoom100"].set_sensitive(gtk.FALSE)
        env.widgets["zoomToFit"].set_sensitive(gtk.FALSE)
        env.widgets["zoomIn"].set_sensitive(gtk.FALSE)
        env.widgets["zoomOut"].set_sensitive(gtk.FALSE)
