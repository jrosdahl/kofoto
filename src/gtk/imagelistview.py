import gtk
import gtk.gdk
from imagelistmodel import *

class ImageListView(gtk.TreeView):
    def __init__(self, imageListModel):
        gtk.TreeView.__init__(self, imageListModel)
        self.createThumbnailColumn()
        self.createIdColumn()
        self.createLocationColumn()
        self.createAttributeColumns(imageListModel)
        
    def createThumbnailColumn(self):
        renderer = gtk.CellRendererPixbuf()
        column = gtk.TreeViewColumn("Thumbnail", renderer, pixbuf=ImageListModel.COLUMN_THUMBNAIL)
        self.append_column(column)

    def createIdColumn(self):
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn("imageId", renderer, text=ImageListModel.COLUMN_IMAGE_ID)
        self.append_column(column)

    def createLocationColumn(self):
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Location", renderer, text=ImageListModel.COLUMN_LOCATION)
        self.append_column(column)        

    def createAttributeColumns(self, imageListModel):
        for attributeName, value in imageListModel.attributeNamesMap.items():
            renderer = gtk.CellRendererText()
            column = gtk.TreeViewColumn(attributeName,
                                        renderer,
                                        text=imageListModel.attributeNamesMap[attributeName])
            self.append_column(column)
