import gtk

from environment import env
from images import *
from kofoto.sets import *

class TableView:
    _selectionSignalHandler = None
    
    def __init__(self):
        selection = env.widgets["tableView"].get_selection()
        selection.set_mode(gtk.SELECTION_MULTIPLE)
        self._selectionSignalHandler = selection.connect('changed', self._selectionUpdated)
    
    def setModel(self, model):
        env.widgets["tableView"].set_model(model)
        self._model = model
        self._createThumbnailColumn()
        self._createIdColumn()
        self._createLocationColumn()

    def _createThumbnailColumn(self):
        renderer = gtk.CellRendererPixbuf()
        column = gtk.TreeViewColumn("Thumbnail", renderer, pixbuf=Images.COLUMN_THUMBNAIL)
        env.widgets["tableView"].append_column(column)

    def _createIdColumn(self):
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn("imageId", renderer, text=Images.COLUMN_IMAGE_ID)
        env.widgets["tableView"].append_column(column)

    def _createLocationColumn(self):
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Location", renderer, text=Images.COLUMN_LOCATION)
        env.widgets["tableView"].append_column(column)        

    def setAttributes(self, attributeNamesMap):
        for attributeName, value in attributeNamesMap.items():
            renderer = gtk.CellRendererText()
            column = gtk.TreeViewColumn(attributeName,
                                        renderer,
                                        text=attributeNamesMap[attributeName])
            env.widgets["tableView"].append_column(column)
        
    def loadNewSelection(self):
        selection = env.widgets["tableView"].get_selection()
        selection.handler_block(self._selectionSignalHandler)
        selection.unselect_all()
        iter = self._model.get_iter_first()
        index = 0
        while iter:
            imageId = self._model.get_value(iter, Images.COLUMN_IMAGE_ID)
            if imageId in env.controller.selection:
                selection.select_path(index)
            index = index + 1
            iter =  self._model.iter_next(iter)
        selection.handler_unblock(self._selectionSignalHandler)

    def _selectionUpdated(self, selection):
        env.controller.selection = Set()
        iter = self._model.get_iter_first()
        while iter:
            if selection.iter_is_selected(iter):
                imageId = self._model.get_value(iter, Images.COLUMN_IMAGE_ID)
                env.controller.selection.add(imageId)
            iter = self._model.iter_next(iter)
        env.controller.selectionUpdated()
        
