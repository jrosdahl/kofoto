import gtk
import gobject
import gtk

from environment import env
from images import Images
from kofoto.search import *
from kofoto.shelf import *

class Categories:
    _COLUMN_CATEGORY_ID  = 0
    _COLUMN_TAG          = 1
    _COLUMN_DESCRIPTION  = 2
    _COLUMN_CONNECTED    = 3
    _COLUMN_INCONSISTENT = 4
    _model = None
    _toggleColumn = None
    _ignoreSelectEvent = gtk.FALSE
    _selectedCategories = []
    
    def __init__(self):
        self._model = gtk.TreeStore(gobject.TYPE_INT,      # CATEGORY_ID
                                    gobject.TYPE_PYOBJECT, # TAG
                                    gobject.TYPE_STRING,   # DESCRIPTION
                                    gobject.TYPE_BOOLEAN,  # CONNECTED
                                    gobject.TYPE_BOOLEAN)  # INCONSISTENT
        categoryView = env.widgets["categoryView"]
        categoryView.set_model(self._model)

        # Create columns
        renderer = gtk.CellRendererToggle()
        renderer.connect("toggled", self._connectionToggled)
        self._toggleColumn = gtk.TreeViewColumn("",
                                          renderer,
                                          active=self._COLUMN_CONNECTED,
                                          inconsistent=self._COLUMN_INCONSISTENT)
        categoryView.append_column(self._toggleColumn)
        
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Category", renderer, text=self._COLUMN_DESCRIPTION)
        categoryView.append_column(column)
        categoryView.set_expander_column(column)

        # Create context menu
        self._contextMenu = gtk.Menu()

        self._copyItem = gtk.MenuItem("Copy")
        self._copyItem.show()
        self._copyItem.set_sensitive(gtk.FALSE)
        self._contextMenu.append(self._copyItem)
        
        self._pastItem = gtk.MenuItem("Paste")
        self._pastItem.show()
        self._pastItem.set_sensitive(gtk.FALSE)
        self._contextMenu.append(self._pastItem)

        self._createChildItem = gtk.MenuItem("Create child")
        self._createChildItem.show()
        self._createChildItem.connect("activate", self._createChildCategory, None)
        self._contextMenu.append(self._createChildItem)
        
        self._createItem = gtk.MenuItem("Create")
        self._createItem.show()
        self._createItem.connect("activate", self._createCategory, None)
        self._contextMenu.append(self._createItem)
        
        self._removeItem = gtk.MenuItem("Remove selected")
        self._removeItem.show()
        self._removeItem.connect("activate", self._removeCategory, None)
        self._contextMenu.append(self._removeItem)

        self._propertiesItem = gtk.MenuItem("Properties")
        self._propertiesItem.show()
        self._propertiesItem.set_sensitive(gtk.FALSE)
        self._contextMenu.append(self._propertiesItem)

        self._updateContextMenu()

        # Init selection functions
        categorySelection = categoryView.get_selection()
        categorySelection.set_mode(gtk.SELECTION_MULTIPLE)
        categorySelection.set_select_function(self._selectionFunction, None)
        categorySelection.connect('changed', self._queryUpdated)

        # Connect events
        categoryView.connect("button_press_event", self._button_pressed)
        categoryView.connect("button_release_event", self._button_released)
        categoryView.connect("row-activated", self._rowActivated)
        env.widgets["categoriesOr"].connect('toggled', self._queryUpdated)

        # Load data into model
        self.reload()
    
    def reload(self):
        self._model.clear()
        self._buildModel(None, env.shelf.getRootCategories())

    def _buildModel(self, parent, categories):
        for c in categories:
            iter = self._model.insert_before(parent, None)
            self._model.set_value(iter, self._COLUMN_CATEGORY_ID, c.getId())
            self._model.set_value(iter, self._COLUMN_TAG, c.getTag())
            self._model.set_value(iter, self._COLUMN_DESCRIPTION, c.getDescription())
            self._model.set_value(iter, self._COLUMN_CONNECTED, gtk.FALSE)
            self._model.set_value(iter, self._COLUMN_INCONSISTENT, gtk.FALSE)
            self._buildModel(iter, c.getChildren())

    def _queryUpdated(self, garbage):
        selection = env.widgets["categoryView"].get_selection()
        self._selectedCategories = []
        query = self._buildQuery(self._model, selection, "")
        self._updateContextMenu()
        images = []
        if query:
            parser = Parser(env.shelf)
            for child in env.shelf.search(parser.parse(query)):
                if not child.isAlbum():
                    images.append(child)
        env.controller.loadImages(images, "query://" + query)

    def _buildQuery(self, categoryList, selection, query):
        for row in categoryList:
            if selection.iter_is_selected(row.iter):
                self._selectedCategories.append(row)
                query = self._addToQuery(query, row[self._COLUMN_TAG])
            childQuery = self._buildQuery(row.iterchildren(), selection, "")
            query = self._addToQuery(query, childQuery)
        return query

    def _addToQuery(self, query, addition):
        if addition == "":
            return query
        elif query == "":
            return addition
        else:
            if env.widgets["categoriesOr"].get_active():
                operator = "or"
            else:
                operator = "and"
            return query + " " + operator + " " + addition
    
    def _updateContextMenu(self):
        if len(self._selectedCategories) == 0:
            self._removeItem.set_sensitive(gtk.FALSE)
            self._createChildItem.set_sensitive(gtk.FALSE)
        else:
            self._removeItem.set_sensitive(gtk.TRUE)
            self._createChildItem.set_sensitive(gtk.TRUE)
    
    def imagesSelected(self, imageModel):
        nrSelectedImagesInCategory = {}
        nrSelectedImages = 0
        # find out which categories are connected, not connected or
        # partitionally connected to selected images
        for image in imageModel:
            imageId = image[Images.COLUMN_IMAGE_ID]
            if imageId in env.controller.selection:
                nrSelectedImages += 1
                image = env.shelf.getImage(imageId)
                for category in image.getCategories():
                    categoryId = category.getId()
                    try:
                        nrSelectedImagesInCategory[categoryId] += 1
                    except(KeyError):
                        nrSelectedImagesInCategory[categoryId] = 1
        for categoryRow in self._model:
            self._updateCategoryModel(categoryRow, nrSelectedImagesInCategory, nrSelectedImages)

    def _updateCategoryModel(self, categoryRow, nrSelectedImagesInCategory, nrSelectedImages):
        # Expand/collapse categories
        expand = gtk.FALSE
        collapse = gtk.FALSE
        for child in categoryRow.iterchildren():
            if self._updateCategoryModel(child, nrSelectedImagesInCategory, nrSelectedImages):
                expand = gtk.TRUE
                collapse = gtk.FALSE
            elif not expand:
                collapse = gtk.TRUE
        if expand:
            if env.widgets["autoExpand"].get_active():
                env.widgets["categoryView"].expand_row(categoryRow.path, gtk.FALSE)
        elif collapse:
            if env.widgets["autoCollapse"].get_active() and nrSelectedImages > 0 and categoryRow[self._COLUMN_CATEGORY_ID] not in nrSelectedImagesInCategory:
                env.widgets["categoryView"].collapse_row(categoryRow.path)
        # Update the checkbox indicating if the selected images are connected
        # to the category or not. 
        categoryId = categoryRow[self._COLUMN_CATEGORY_ID]
        try:
            if nrSelectedImagesInCategory[categoryId] < nrSelectedImages:
                # Some of the selected images are connected to the category
                categoryRow[self._COLUMN_CONNECTED] = gtk.FALSE
                categoryRow[self._COLUMN_INCONSISTENT] = gtk.TRUE
                return 1
            else:
                # All of the selected images are connected to the category
                categoryRow[self._COLUMN_CONNECTED] = gtk.TRUE
                categoryRow[self._COLUMN_INCONSISTENT] = gtk.FALSE
                return 1
        except(KeyError):
            # None of the selected images are connected to the category
            categoryRow[self._COLUMN_CONNECTED] = gtk.FALSE
            categoryRow[self._COLUMN_INCONSISTENT] = gtk.FALSE
            return 0
                
    def _connectionToggled(self, renderer, path):
        categoryRow = self._model[path]
        category = env.shelf.getCategory(categoryRow[self._COLUMN_CATEGORY_ID])
        if categoryRow[self._COLUMN_INCONSISTENT]:
            for imageId in env.controller.selection:
                try:
                    env.shelf.getObject(imageId).addCategory(category)
                except(CategoryPresentError):
                    pass
            categoryRow[self._COLUMN_INCONSISTENT] = gtk.FALSE
            categoryRow[self._COLUMN_CONNECTED] = gtk.TRUE
        elif categoryRow[self._COLUMN_CONNECTED]:
            for imageId in env.controller.selection:
                env.shelf.getObject(imageId).removeCategory(category)
            categoryRow[self._COLUMN_CONNECTED] = gtk.FALSE
        else:
            for imageId in env.controller.selection:
                env.shelf.getObject(imageId).addCategory(category)
                categoryRow[self._COLUMN_CONNECTED] = gtk.TRUE

    def _button_pressed(self, treeView, event):
        if event.button == 3:
            self._contextMenu.popup(None,None,None,event.button,event.time)
            return gtk.TRUE
        rec = env.widgets["categoryView"].get_cell_area(0, self._toggleColumn)
        if event.x <= (rec.x + rec.width):
            self._ignoreSelectEvent = gtk.TRUE
        return gtk.FALSE

    def _button_released(self, treeView, event):
        self._ignoreSelectEvent = gtk.FALSE
        return gtk.FALSE
        
    def _rowActivated(self, a, b, c):
        print "not yet implemented!"
            
    def _createCategory(self, item, data):
        print "create category not yet imlemented!"

    def _createChildCategory(self, item, data):
        print "create child category not yet imlemented"

    def _removeCategory(self, item, data):
        print "remove category not yet imlemented"
        #for categoryRow in self._selectedCategories:
        #    env.shelf.deleteCategory(categoryRow[self._COLUMN_CATEGORY_ID])
        #    del self._model[categoryRow.path]
        #self.reload()
        
    def _selectionFunction(self, path, b):
        if self._ignoreSelectEvent:
            return gtk.FALSE
        else:
            return gtk.TRUE

 
