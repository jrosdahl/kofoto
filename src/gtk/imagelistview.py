import gtk
import gtk.gdk
from imagelistmodel import *

class ImageListView(gtk.TreeView):
    def __init__(self, imageListModel, imageListColumns):
        gtk.TreeView.__init__(self, imageListModel)
        self.createColumns(imageListColumns)

    def createColumns(self, imageListColumns):
        for name in imageListColumns.map:
            columnNumber, visible = imageListColumns.map[name]
            if visible == gtk.TRUE:
                self.createTextColumn(name, columnNumber)

    def createTextColumn(self, heading, columnNumber):
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn(heading, renderer, text=columnNumber)
        self.append_column(column)
