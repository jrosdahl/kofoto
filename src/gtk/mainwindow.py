# TODO: How should a default size be set up for whole main window and its containg widgets? I have not managed to specify a default size for the scrollable ImageView widget.

import gtk

from albumview import *
class MainWindow(gtk.Window):
    _imageView = None
    _albumView = None

    def __init__(self, albumModel, albumView, imagelistModel, imageListView, imageView):
        gtk.Window.__init__(self)
        self.set_default_size(300, 200)
        self.set_resizable(gtk.TRUE)
        self.add_events(gtk.gdk.KEY_PRESS_MASK)
        self.connect("key_press_event", self.keyPressEventHandler)
        hpanedMain = gtk.HPaned()
        hpanedSelection = gtk.HPaned()
        hpanedMain.pack1(hpanedSelection, gtk.FALSE, gtk.TRUE)
        self.add(hpanedMain)

        # image view
        self._imageView = imageView
        hpanedMain.pack2(imageView, gtk.FALSE, gtk.TRUE)
                
        # image list
        self._imageListView = imageListView
        scrolledImageListView = gtk.ScrolledWindow()
        scrolledImageListView.add(imageListView)
        scrolledImageListView.set_size_request(400, 200)
        hpanedSelection.pack2(scrolledImageListView, gtk.TRUE, gtk.TRUE )

        # notebook
        hpanedSelection.pack1(self._create_notebook(albumView), gtk.TRUE, gtk.TRUE)

    def _create_notebook(self, albumView):
        notebook = gtk.Notebook()

        # Album view
        self._albumView = albumView
        self._new_notebook_page(notebook, albumView, '_Albums')

        # TODO...
        self._new_notebook_page(notebook, gtk.Label("Directories..."), '_Directories')
        self._new_notebook_page(notebook, gtk.Label("Search..."), '_Search')
        return notebook
    
    def _new_notebook_page(self, notebook, widget, label):
        l = gtk.Label('')
        l.set_text_with_mnemonic(label)
        notebook.append_page(widget, l)
        
    def keyPressEventHandler(self, widget, gdkEvent):
        if gdkEvent.type == gtk.gdk.KEY_PRESS:
            if gdkEvent.keyval == gtk.keysyms.z:
                self._imageView.fitToWindow()
            if gdkEvent.keyval == gtk.keysyms.plus or gdkEvent.keyval == 65451:
                self._imageView.zoomIn()
            if gdkEvent.keyval == gtk.keysyms.minus or gdkEvent.keyval == 65453:
                self._imageView.zoomOut()
        return gtk.FALSE
