import gtk
import gobject
import gtk
import string

from environment import env
from images import Images
from categorydialog import CategoryDialog
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
    _selectedCategories = {}
    
    def __init__(self, loadedImages, selectedImages):
        self._model = gtk.TreeStore(gobject.TYPE_INT,      # CATEGORY_ID
                                    gobject.TYPE_PYOBJECT, # TAG
                                    gobject.TYPE_STRING,   # DESCRIPTION
                                    gobject.TYPE_BOOLEAN,  # CONNECTED
                                    gobject.TYPE_BOOLEAN)  # INCONSISTENT
        categoryView = env.widgets["categoryView"]
        categoryView.realize()
        self._loadedImages = loadedImages
        self._selectedImages = selectedImages
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
        self._copyItem.connect("activate", self._copyCategory, None)
        self._contextMenu.append(self._copyItem)

        self._cutItem = gtk.MenuItem("Cut")
        self._cutItem.show()
        self._cutItem.connect("activate", self._cutCategory, None)
        self._contextMenu.append(self._cutItem)
        
        self._pasteItem = gtk.MenuItem("Paste")
        self._pasteItem.show()
        self._pasteItem.connect("activate", self._pasteCategory, None)
        self._contextMenu.append(self._pasteItem)

        self._createChildItem = gtk.MenuItem("Create child category")
        self._createChildItem.show()
        self._createChildItem.connect("activate", self._createChildCategory, None)
        self._contextMenu.append(self._createChildItem)
        
        self._createRootItem = gtk.MenuItem("Create root category")
        self._createRootItem.show()
        self._createRootItem.connect("activate", self._createRootCategory, None)
        self._contextMenu.append(self._createRootItem)
        
        self._deleteItem = gtk.MenuItem("Delete selected categories")
        self._deleteItem.show()
        self._deleteItem.connect("activate", self._deleteCategory, None)
        self._contextMenu.append(self._deleteItem)

        self._disconnectItem = gtk.MenuItem("Disconnect selected categories")
        self._disconnectItem.show()
        self._disconnectItem.connect("activate", self._disconnectCategory, None)
        self._contextMenu.append(self._disconnectItem)

        self._propertiesItem = gtk.MenuItem("Properties")
        self._propertiesItem.show()
        self._propertiesItem.connect("activate", self._editProperties, None)
        self._contextMenu.append(self._propertiesItem)

        self.updateContextMenu()

        # Init selection functions
        categorySelection = categoryView.get_selection()
        categorySelection.set_mode(gtk.SELECTION_MULTIPLE)
        categorySelection.set_select_function(self._selectionFunction, None)

        # Connect events
        categoryView.connect("button_press_event", self._button_pressed)
        categoryView.connect("button_release_event", self._button_released)
        categoryView.connect("row-activated", self._rowActivated)
                                            
        # Connect search button
        env.widgets["categorySearchButton"].connect('clicked', self._queryUpdated)
        
        # Load data into model
        self.reload()
    
    def reload(self):
        self._model.clear()
        env.shelf.flushCategoryCache()
        for category in env.shelf.getRootCategories():
            self._populateModel(None, category)

    def _populateModel(self, parent, category):
        iter = self._model.append(parent)
        self._model.set_value(iter, self._COLUMN_CATEGORY_ID, category.getId())
        self._model.set_value(iter, self._COLUMN_TAG, category.getTag())
        self._model.set_value(iter, self._COLUMN_DESCRIPTION, category.getDescription())
        self._model.set_value(iter, self._COLUMN_CONNECTED, gtk.FALSE)
        self._model.set_value(iter, self._COLUMN_INCONSISTENT, gtk.FALSE)
        for child in category.getChildren():
            self._populateModel(iter, child)

    def _queryUpdated(self, garbage):
        selection = env.widgets["categoryView"].get_selection()
        self._selectedCategories = {}
        query = self._buildQuery(self._model, None, selection, "")
        self.updateContextMenu()
        images = []
        if query:
            parser = Parser(env.shelf)
            for child in env.shelf.search(parser.parse(query)):
                if not child.isAlbum():
                    images.append(child)
        env.controller.loadImages(images, "query://" + query)

    def _buildQuery(self, categoryList, parent, selection, query):
        for row in categoryList:
            categoryId = row[self._COLUMN_CATEGORY_ID]
            if selection.iter_is_selected(row.iter):
                if categoryId in self._selectedCategories:
                    self._selectedCategories[categoryId].append(parent)
                else:
                    self._selectedCategories[categoryId] = [parent]
                    query = self._addToQuery(query, row[self._COLUMN_TAG])
            childQuery = self._buildQuery(row.iterchildren(), categoryId, selection, "")
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
    
    def updateContextMenu(self):
        if len(self._selectedCategories) == 0:
            self._deleteItem.set_sensitive(gtk.FALSE)
            self._createChildItem.set_sensitive(gtk.FALSE)
            self._copyItem.set_sensitive(gtk.FALSE)
            self._cutItem.set_sensitive(gtk.FALSE)
            self._pasteItem.set_sensitive(gtk.FALSE)
            self._disconnectItem.set_sensitive(gtk.FALSE)
        else:
            self._deleteItem.set_sensitive(gtk.TRUE)
            self._createChildItem.set_sensitive(gtk.TRUE)
            self._copyItem.set_sensitive(gtk.TRUE)
            self._cutItem.set_sensitive(gtk.TRUE)
            if env.controller.clipboardHasCategory():
                self._pasteItem.set_sensitive(gtk.TRUE)
            else:
                self._pasteItem.set_sensitive(gtk.FALSE)
            self._disconnectItem.set_sensitive(gtk.TRUE)
        if len(self._selectedCategories) == 1:
            self._propertiesItem.set_sensitive(gtk.TRUE)
        else:
            self._propertiesItem.set_sensitive(gtk.FALSE)
            
    def updateView(self, doNotAutoCollapse=gtk.FALSE):
        nrSelectedImagesInCategory = {}
        nrSelectedImages = 0
        # find out which categories are connected, not connected or
        # partitionally connected to selected images
        for image in self._loadedImages.model:
            imageId = image[Images.COLUMN_IMAGE_ID]
            if imageId in self._selectedImages:
                nrSelectedImages += 1
                image = env.shelf.getImage(imageId)
                for category in image.getCategories():
                    categoryId = category.getId()
                    try:
                        nrSelectedImagesInCategory[categoryId] += 1
                    except(KeyError):
                        nrSelectedImagesInCategory[categoryId] = 1
        pathsToExpand = self._updateViewHelper(self._model,
                                           nrSelectedImagesInCategory,
                                           nrSelectedImages,
                                           doNotAutoCollapse)[0]
        if env.widgets["autoExpand"].get_active():
            pathsToExpand.reverse()
            for path in pathsToExpand:
                env.widgets["categoryView"].expand_row(path, gtk.FALSE)  
            
    def _updateViewHelper(self, categories, nrSelectedImagesInCategory, nrSelectedImages, doNotAutoCollapse):
        pathsToExpand = []
        expandParent = gtk.FALSE
        for categoryRow in categories:
            childPathsToExpand, expandThis = self._updateViewHelper(categoryRow.iterchildren(),
                                                                nrSelectedImagesInCategory,
                                                                nrSelectedImages,
                                                                doNotAutoCollapse)
            pathsToExpand.extend(childPathsToExpand)
            if expandThis:
                pathsToExpand.append(categoryRow.path)
                expandParent = gtk.TRUE
            if categoryRow[self._COLUMN_CATEGORY_ID] in self._selectedCategories:
                # Dont auto collapse selected categories
                expandParent = gtk.TRUE
            categoryId = categoryRow[self._COLUMN_CATEGORY_ID]
            if categoryId in nrSelectedImagesInCategory:
                expandParent = gtk.TRUE
                if nrSelectedImagesInCategory[categoryId] < nrSelectedImages:
                    # Some of the selected images are connected to the category
                    categoryRow[self._COLUMN_CONNECTED] = gtk.FALSE
                    categoryRow[self._COLUMN_INCONSISTENT] = gtk.TRUE
                else:
                    # All of the selected images are connected to the category
                    categoryRow[self._COLUMN_CONNECTED] = gtk.TRUE
                    categoryRow[self._COLUMN_INCONSISTENT] = gtk.FALSE
            else:
                # None of the selected images are connected to the category
                categoryRow[self._COLUMN_CONNECTED] = gtk.FALSE
                categoryRow[self._COLUMN_INCONSISTENT] = gtk.FALSE
            if (not expandThis) and (not doNotAutoCollapse) and env.widgets["autoCollapse"].get_active():
                env.widgets["categoryView"].collapse_row(categoryRow.path)
        return pathsToExpand, expandParent
                
    def _connectionToggled(self, renderer, path):
        categoryRow = self._model[path]
        category = env.shelf.getCategory(categoryRow[self._COLUMN_CATEGORY_ID])
        if categoryRow[self._COLUMN_INCONSISTENT]:
            for imageId in self._selectedImages:
                try:
                    env.shelf.getObject(imageId).addCategory(category)
                except(CategoryPresentError):
                    pass
            categoryRow[self._COLUMN_INCONSISTENT] = gtk.FALSE
            categoryRow[self._COLUMN_CONNECTED] = gtk.TRUE
        elif categoryRow[self._COLUMN_CONNECTED]:
            for imageId in self._selectedImages:
                env.shelf.getObject(imageId).removeCategory(category)
            categoryRow[self._COLUMN_CONNECTED] = gtk.FALSE
        else:
            for imageId in self._selectedImages:
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

    def _copyCategory(self, item, data):
        cc = ClipboardCategories()
        cc.type = cc.COPY
        cc.categories = self._selectedCategories
        env.controller.clipboardSet(cc)

    def _cutCategory(self, item, data):
        cc = ClipboardCategories()
        cc.type = cc.CUT
        cc.categories = self._selectedCategories
        env.controller.clipboardSet(cc)

    def _pasteCategory(self, item, data):
        clipboardCategories = env.controller.clipboardPop()
        try:
            for (categoryId, parentIds) in clipboardCategories.categories.items():
                for selectedCategoryId in self._selectedCategories:
                    self._connectChild(selectedCategoryId, categoryId)
                    self._expandCategory(selectedCategoryId, self._model)
                if clipboardCategories.type == ClipboardCategories.CUT:
                    for parentId in parentIds:
                        if parentId != None:
                            self._disconnectChild(parentId, categoryId)
        except(CategoryLoopError):
            print "Error: Category loop detected"
            # TODO: Show dialog box with error message
        self.updateView(doNotAutoCollapse = gtk.TRUE)

    def _expandCategory(self, categoryId, categories):
        for c in categories:
            if c[self._COLUMN_CATEGORY_ID] == categoryId:
                env.widgets["categoryView"].expand_row(c.path, gtk.FALSE)
            self._expandCategory(categoryId, c.iterchildren())
        
    def _createRootCategory(self, item, data):
        dialog = CategoryDialog("Create root category")
        dialog.run(self._createRootCategoryHelper)
       
    def _createRootCategoryHelper(self, tag, desc):
        category = env.shelf.createCategory(tag, desc)
        self._populateModel(None, category)
        self.updateView(doNotAutoCollapse = gtk.TRUE)

    def _createChildCategory(self, item, data):
        dialog = CategoryDialog("Create child category")
        dialog.run(self._createChildCategoryHelper)

    def _createChildCategoryHelper(self, tag, desc):
        newCategory = env.shelf.createCategory(tag, desc)
        for selectedCategoryId in self._selectedCategories:
            self._connectChild(selectedCategoryId, newCategory.getId())
        self.updateView(doNotAutoCollapse = gtk.TRUE)
        
    def _deleteCategory(self, item, data):
        # TODO: Add confirmation dialog box
        for categoryId in self._selectedCategories:
            category = env.shelf.getCategory(categoryId)
            for child in list(category.getChildren()):
                # The backend automatically disconnects childs when a category
                # is deleted, but we do it outself to make sure that the
                # treeview widget is updated
                self._disconnectChild(categoryId, child.getId())
            env.shelf.deleteCategory(categoryId)
            env.shelf.flushCategoryCache()
            self._deleteCategoryHelper(self._model, categoryId)
        self.updateView(doNotAutoCollapse = gtk.TRUE)

    def _deleteCategoryHelper(self, categories, categoryId):
         for c in categories:
            if c[self._COLUMN_CATEGORY_ID] == categoryId:
                self._model.remove(c.iter)
            self._deleteCategoryHelper(c.iterchildren(), categoryId)

    def _disconnectCategory(self, item, data):
        for (categoryId, parentIds) in self._selectedCategories.items():
            for parentId in parentIds:
                if not parentId == None:
                    self._disconnectChild(parentId, categoryId)
        self.updateView(doNotAutoCollapse = gtk.TRUE)

    def _editProperties(self, item, data):
        for category in self._selectedCategories:
            dialog = CategoryDialog("Change properties", category)
            dialog.run(self._editPropertiesHelper, data=category)

    def _editPropertiesHelper(self, tag, desc, categoryId):
         category = env.shelf.getCategory(categoryId)
         category.setTag(tag)
         category.setDescription(desc)
         self._updateProperties(categoryId, self._model)

    def _updateProperties(self, categoryId, categories):
        for row in categories:
            if row[self._COLUMN_CATEGORY_ID] == categoryId:
                c = env.shelf.getCategory(categoryId)
                row[self._COLUMN_TAG] = c.getTag()
                row[self._COLUMN_DESCRIPTION] = c.getDescription()
            self._updateProperties(categoryId, row.iterchildren())
        
    def _selectionFunction(self, path, b):
        if self._ignoreSelectEvent:
            return gtk.FALSE
        else:
            return gtk.TRUE

    def _connectChild(self, parentId, childId):
        childCategory = env.shelf.getCategory(childId)
        parentCategory = env.shelf.getCategory(parentId)
        parentCategory.connectChild(childCategory)
        self._connectChildHelper(self._model, parentId, childCategory)
        for category in self._model:
            if category[self._COLUMN_CATEGORY_ID] == childId:
                self._model.remove(category.iter)
        
    def _connectChildHelper(self, categories, parentId, child):
        for c in categories:
            if c[self._COLUMN_CATEGORY_ID] == parentId:
                self._populateModel(c.iter, child)
            self._connectChildHelper(c.iterchildren(), parentId, child)

    def _disconnectChild(self, parentId, childId):
        childCategory = env.shelf.getCategory(childId)
        parentCategory = env.shelf.getCategory(parentId)
        parentCategory.disconnectChild(childCategory)
        self._disconnectChildHelper(self._model, None, childId, parentId)
        if len(list(childCategory.getParents())) == 0:
            self._populateModel(None, childCategory)
        
    def _disconnectChildHelper(self, categories, parent, childId, parentId):
        for c in categories:
            id = c[self._COLUMN_CATEGORY_ID]
            if id == childId and parent == parentId:
                self._model.remove(c.iter)
            self._disconnectChildHelper(c.iterchildren(), id, childId, parentId)

class ClipboardCategories:
    COPY = 1
    CUT = 2
    categories = None
    type = None

