import gtk
import sys

from environment import env
from images import *

class ThumbnailView:
    _maxWidth = 0
    _thumbnailList = None
    _selectSignalHandler = None
    _unselectSignalHandler = None
    _model = None
    
    def __init__(self):
        widget = env.widgets["thumbnailList"]
        self._selectSignalHandler = widget.connect("select_icon", self._iconSelected)
        self._unSelectSignalHandler = widget.connect("unselect_icon", self._iconUnselected)
    
    def setModel(self, model):
        self._thumbnailList = env.widgets["thumbnailList"]
        self._thumbnailList.clear()
        model.connect("row_inserted", self.on_row_inserted)
        model.connect("row_changed", self.on_row_changed)
        model.connect("row_deleted", self.on_row_deleted)
        iter = model.get_iter_first()
        self._model = model
        for pos in range(model.iter_n_children(iter)):
            self._thumbnailList.updateThumbnail(model, iter, pos)
            model.iter_next(iter)

    def _updateThumbnail(self, model, iter, pos):
        pixbuf = model.get_value(iter, Images.COLUMN_THUMBNAIL)
        imageId = model.get_value(iter, Images.COLUMN_IMAGE_ID)
        if pixbuf:
            self._maxWidth = max(self._maxWidth, pixbuf.get_width())
            self._thumbnailList.set_icon_width(self._maxWidth)
            self._thumbnailList.insert_pixbuf(pos, pixbuf, "filnamn", str(imageId))

    def freeze(self):
        self._thumbnailList.freeze()

    def thaw(self):
        self._thumbnailList.thaw()

    def show(self):
        env.widgets["thumbnailView"].show()
        env.widgets["thumbnailList"].grab_focus()

    def hide(self):
        env.widgets["thumbnailView"].hide()
        
    def setAttributes(self, attributeNamesMap):
        pass

    def on_row_changed(self, model, path, iter):
        self._updateThumbnail(model, iter, path[0])

    def on_row_inserted(self, model, path, iter):
        self._updateThumbnail(model, iter, path[0])

    def on_row_has_child_toggled(self, path, iter):
        pass
    
    def on_row_deleted(self, model, path):
        self._thumbnailList.remove(path[0])
        
    def on_rows_reordered(self, path, iter, new_order):
        pass

    def _iconSelected(self, widget, index, event):
        iter = self._model.get_iter(index)
        imageId = self._model.get_value(iter, Images.COLUMN_IMAGE_ID)
        env.controller.selection.add(imageId)
        env.controller.selectionUpdated()

    def _iconUnselected(self, widget, index, event):
        iter = self._model.get_iter(index)
        imageId = self._model.get_value(iter, Images.COLUMN_IMAGE_ID)
        try:
            env.controller.selection.remove(imageId)
            env.controller.selectionUpdated()
        except(KeyError):
            pass

    def loadNewSelection(self):
        self._thumbnailList.handler_block(self._selectSignalHandler)
        self._thumbnailList.handler_block(self._unSelectSignalHandler)
        self._thumbnailList.unselect_all()
        indices = xrange(sys.maxint)
        for image, index in zip(self._model, indices):
            if image[Images.COLUMN_IMAGE_ID] in env.controller.selection:
                self._thumbnailList.select_icon(index)
        self._thumbnailList.handler_unblock(self._selectSignalHandler)
        self._thumbnailList.handler_unblock(self._unSelectSignalHandler)

