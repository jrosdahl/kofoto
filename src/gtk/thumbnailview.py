import gtk

from environment import env
from images import *

class ThumbnailView:
    _maxWidth = 0
    _thumbnailList = None
    
    def setModel(self, model):
        self._thumbnailList = env.widgets["thumbnailList"]
        self._thumbnailList.clear()
        model.connect("row_inserted", self.on_row_inserted)
        model.connect("row_changed", self.on_row_changed)
        model.connect("row_deleted", self.on_row_deleted)
        iter = model.get_iter_first()
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
