import gtk
import gobject
import gtk

from environment import env

class Categories:
    _COLUMN_CATEGORY_ID  = 0
    _COLUMN_TAG          = 1
    _COLUMN_DESCRIPTION  = 2
    _COLUMN_OBJECT       = 3
    _COLUMN_CONNECTED_TO_SELECTED = 4

    _model = None
    
    def __init__(self):
        self._model = gtk.TreeStore(gobject.TYPE_INT,      # CATEGORY_ID
                                    gobject.TYPE_STRING,   # TAG
                                    gobject.TYPE_STRING,   # DESCRIPTION
                                    gobject.TYPE_PYOBJECT, # OBJECT
                                    gobject.TYPE_BOOLEAN)  # CONNECTED_TO_SELECTED
        categoryView = env.widgets["categoryView"]
        categoryView.set_model(self._model)

        renderer = gtk.CellRendererToggle()
        column = gtk.TreeViewColumn("Categorys", renderer, active=self._COLUMN_CONNECTED_TO_SELECTED)
        column.set_clickable(gtk.TRUE)
        categoryView.append_column(column)
        
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Categorys", renderer, text=self._COLUMN_DESCRIPTION)
        column.set_clickable(gtk.TRUE)
        categoryView.append_column(column)
        categoryView.set_expander_column(column)
        
        categorySelection = categoryView.get_selection()
        categorySelection.connect('changed', self._categorySelectionHandler)
        self.reload()
        
    def reload(self):
        env.shelf.begin()
        self._buildModel(None, env.shelf.getRootCategories())
        env.shelf.rollback()

    def _buildModel(self, parent, categories):
        for c in categories:
            iter = self._model.insert_before(parent, None)
            self._model.set_value(iter, self._COLUMN_CATEGORY_ID, c.getId())
            self._model.set_value(iter, self._COLUMN_TAG, c.getTag())
            self._model.set_value(iter, self._COLUMN_DESCRIPTION, c.getDescription())
            self._model.set_value(iter, self._COLUMN_OBJECT, c)
            self._model.set_value(iter, self._COLUMN_CONNECTED_TO_SELECTED, gtk.FALSE)
            self._buildModel(iter, c.getChildren())

    def _categorySelectionHandler(self, selection):
        env.shelf.begin()
        categoryModel, iter = selection.get_selected()
        if iter:
            category = categoryModel.get_value(iter, self._COLUMN_OBJECT)
            selectedImages = []
            for child in env.shelf.getObjectsForCategory(category):
                if not child.isAlbum():
                    selectedImages.append(child)
        env.shelf.rollback()
        if iter:
            env.controller.loadImages(selectedImages, "Category")
