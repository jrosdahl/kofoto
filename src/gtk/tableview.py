import gtk

from environment import env
from images import *

class TableView:
    def setModel(self, model):
        env.widgets["tableView"].set_model(model)
        self._createThumbnailColumn()
        self._createIdColumn()
        self._createLocationColumn()

    def setAttributes(self, attributeNamesMap):
        for attributeName, value in attributeNamesMap.items():
            renderer = gtk.CellRendererText()
            column = gtk.TreeViewColumn(attributeName,
                                        renderer,
                                        text=attributeNamesMap[attributeName])
            env.widgets["tableView"].append_column(column)


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
