import gtk
from albummodel import *

class AlbumView(gtk.TreeView):
    
    def __init__(self, albumModel):
        gtk.TreeView.__init__(self, albumModel)
        self.createColumns()

    def createColumns(self):
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Albums", renderer, text=AlbumModel.COLUMN_TAG)
        column.set_clickable(gtk.TRUE)
        self.append_column(column)

 
       
            

