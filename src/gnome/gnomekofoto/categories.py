import gobject
import gtk
import string

from environment import env
from categorydialog import CategoryDialog
from kofoto.search import *
from kofoto.shelf import *

class Categories:

######################################################################
### Public
    
    def __init__(self, mainWindow):
        self.__toggleColumn = None
        self.__objectCollection = None
        self.__ignoreSelectEvent = False
        self.__selectedCategoriesIds  = {}
        self.__categoryModel = gtk.TreeStore(gobject.TYPE_INT,      # CATEGORY_ID
                                             gobject.TYPE_STRING,   # DESCRIPTION
                                             gobject.TYPE_BOOLEAN,  # CONNECTED
                                             gobject.TYPE_BOOLEAN)  # INCONSISTENT
        self.__categoryView = env.widgets["categoryView"]
        self.__categoryView.realize()
        self.__categoryView.set_model(self.__categoryModel)
        self.__mainWindow = mainWindow
        
        # Create toggle column
        toggleRenderer = gtk.CellRendererToggle()
        toggleRenderer.connect("toggled", self._connectionToggled)
        self.__toggleColumn = gtk.TreeViewColumn("",
                                                 toggleRenderer,
                                                 active=self.__COLUMN_CONNECTED,
                                                 inconsistent=self.__COLUMN_INCONSISTENT)
        self.__categoryView.append_column(self.__toggleColumn)

        # Create text column
        textRenderer = gtk.CellRendererText()
        textColumn = gtk.TreeViewColumn("Category", textRenderer, text=self.__COLUMN_DESCRIPTION)
        self.__categoryView.append_column(textColumn)
        self.__categoryView.set_expander_column(textColumn)

        # Create context menu
        # TODO Is it possible to load a menu from a glade file instead?
        #      If not, create some helper functions to construct the menu...
        self._contextMenu = gtk.Menu()

        self._cutItem = gtk.MenuItem("Cut")
        self._cutItem.show()
        self._cutItem.connect("activate", self._cutCategory, None)
        self._contextMenu.append(self._cutItem)
        
        self._copyItem = gtk.MenuItem("Copy")
        self._copyItem.show()
        self._copyItem.connect("activate", self._copyCategory, None)
        self._contextMenu.append(self._copyItem)

        self._pasteItem = gtk.MenuItem("Paste")
        self._pasteItem.show()
        self._pasteItem.connect("activate", self._pasteCategory, None)
        self._contextMenu.append(self._pasteItem)

        self._deleteItem = gtk.MenuItem("Delete")
        self._deleteItem.show()
        self._deleteItem.connect("activate", self._deleteCategories, None)
        self._contextMenu.append(self._deleteItem)

        self._disconnectItem = gtk.MenuItem("Disconnect")
        self._disconnectItem.show()
        self._disconnectItem.connect("activate", self._disconnectCategory, None)
        self._contextMenu.append(self._disconnectItem)

        self._createChildItem = gtk.MenuItem("Create child")
        self._createChildItem.show()
        self._createChildItem.connect("activate", self._createChildCategory, None)
        self._contextMenu.append(self._createChildItem)
        
        self._createRootItem = gtk.MenuItem("Create root")
        self._createRootItem.show()
        self._createRootItem.connect("activate", self._createRootCategory, None)
        self._contextMenu.append(self._createRootItem)
        
        self._propertiesItem = gtk.MenuItem("Properties")
        self._propertiesItem.show()
        self._propertiesItem.connect("activate", self._editProperties, None)
        self._contextMenu.append(self._propertiesItem)

        # Init selection functions
        categorySelection = self.__categoryView.get_selection()
        categorySelection.set_mode(gtk.SELECTION_MULTIPLE)
        categorySelection.set_select_function(self._selectionFunction, None)
        categorySelection.connect("changed", self._categorySelectionChanged)

        # Connect the rest of the UI events
        self.__categoryView.connect("button_press_event", self._button_pressed)
        self.__categoryView.connect("button_release_event", self._button_released)
        self.__categoryView.connect("row-activated", self._rowActivated)
        env.widgets["categorySearchButton"].connect('clicked', self._executeQuery)

        self.loadCategoryTree()


    def loadCategoryTree(self):
        self.__categoryModel.clear()
        env.shelf.flushCategoryCache()
        for category in env.shelf.getRootCategories():
            self.__loadCategorySubTree(None, category)
        if self.__objectCollection is not None:
            self.objectSelectionChanged()

    def setCollection(self, objectCollection):
        if self.__objectCollection is not None:
            self.__objectCollection.getObjectSelection().removeChangedCallback(self.objectSelectionChanged)
        self.__objectCollection = objectCollection
        self.__objectCollection.getObjectSelection().addChangedCallback(self.objectSelectionChanged)        
        self.objectSelectionChanged()
        
    def objectSelectionChanged(self, objectSelection=None):
        self.__updateToggleColumn()
        self.__updateContextMenu()        
        self.__expandAndCollapseRows(env.widgets["autoExpand"].get_active(),
                                     env.widgets["autoCollapse"].get_active())

        
###############################################################################
### Callback functions registered by this class but invoked from other classes.

    def _executeQuery(self, *foo):
        query = self.__buildQueryFromSelection()
        if query:
            self.__mainWindow.loadUrl("query://" + query)

    def _categorySelectionChanged(self, selection):
        selectedCategoryRows = []
        selection = self.__categoryView.get_selection()
        # TODO replace with "get_selected_rows()" when it is introduced in Pygtk 2.2 API              
        selection.selected_foreach(lambda model,
                                   path,
                                   iter:
                                   selectedCategoryRows.append(model[path]))
        self.__selectedCategoriesIds  = {}

        for categoryRow in selectedCategoryRows:
            id = categoryRow[self.__COLUMN_CATEGORY_ID]
            # row.parent method gives assertion failed, dont know why. Using workaround instead.
            parentPath = categoryRow.path[:-1]
            if parentPath:
                parentId = categoryRow.model[parentPath][self.__COLUMN_CATEGORY_ID]
            else:
                parentId = None
            try:
                 self.__selectedCategoriesIds[id].append(parentId)
            except KeyError:
                 self.__selectedCategoriesIds[id] = [parentId]
        self.__updateContextMenu()
        
    def _connectionToggled(self, renderer, path):
        categoryRow = self.__categoryModel[path]
        category = env.shelf.getCategory(categoryRow[self.__COLUMN_CATEGORY_ID])
        if categoryRow[self.__COLUMN_INCONSISTENT] \
               or not categoryRow[self.__COLUMN_CONNECTED]:
            for object in self.__objectCollection.getObjectSelection().getSelectedObjects():
                try:
                    object.addCategory(category)
                except CategoryPresentError:
                    # The object was already connected to the category
                    pass
            categoryRow[self.__COLUMN_INCONSISTENT] = False
            categoryRow[self.__COLUMN_CONNECTED] = True
        else:
            for object in self.__objectCollection.getObjectSelection().getSelectedObjects():
                object.removeCategory(category)
            categoryRow[self.__COLUMN_CONNECTED] = False
            categoryRow[self.__COLUMN_INCONSISTENT] = False            

    def _button_pressed(self, treeView, event):
        if event.button == 3:
            self._contextMenu.popup(None,None,None,event.button,event.time)
            return True
        rec = self.__categoryView.get_cell_area(0, self.__toggleColumn)
        if event.x <= (rec.x + rec.width):
            # Ignore selection event since the user clicked on the toggleColumn.
            self.__ignoreSelectEvent = True
        return False

    def _button_released(self, treeView, event):
        self.__ignoreSelectEvent = False
        return False
        
    def _rowActivated(self, a, b, c):
        # TODO What should happen if the user dubble-click on a category?
        pass
    
    def _copyCategory(self, item, data):
        cc = ClipboardCategories()
        cc.type = cc.COPY
        cc.categories = self.__selectedCategoriesIds
        env.clipboard.setCategories(cc)

    def _cutCategory(self, item, data):
        cc = ClipboardCategories()
        cc.type = cc.CUT
        cc.categories = self.__selectedCategoriesIds
        env.clipboard.setCategories(cc)
        
    def _pasteCategory(self, item, data):
        if not env.clipboard.hasCategories():
            raise "No categories in clipboard" # TODO
        clipboardCategories = env.clipboard[0]
        env.clipboard.clear()
        try:
            for (categoryId, previousParentIds) in clipboardCategories.categories.items():
                for newParentId in self.__selectedCategoriesIds:
                    if clipboardCategories.type == ClipboardCategories.COPY:
                        self.__connectChildToCategory(categoryId, newParentId)
                        for parentId in previousParentIds:
                            if parentId is None:
                                self.__disconnectChildHelper(categoryId, None,
                                                             None, self.__categoryModel)
                    else:
                        if newParentId in previousParentIds:
                            previousParentIds.remove(newParentId)
                        else:
                            self.__connectChildToCategory(categoryId, newParentId)
                        for parentId in previousParentIds:
                            if parentId is None:
                                self.__disconnectChildHelper(categoryId, None,
                                                             None, self.__categoryModel)
                            else:
                                self.__disconnectChild(categoryId, parentId)
        except CategoryLoopError:
            print "Error: Category loop detected"
            # TODO: Show dialog box with error message
        self.__expandAndCollapseRows(False, False)
        
    def _createRootCategory(self, item, data):
        dialog = CategoryDialog("Create root category")
        dialog.run(self._createRootCategoryHelper)
       
    def _createRootCategoryHelper(self, tag, desc):
        category = env.shelf.createCategory(tag, desc)
        self.__loadCategorySubTree(None, category)

    def _createChildCategory(self, item, data):
        dialog = CategoryDialog("Create child category")
        dialog.run(self._createChildCategoryHelper)

    def _createChildCategoryHelper(self, tag, desc):
        newCategory = env.shelf.createCategory(tag, desc)
        for selectedCategoryId in self.__selectedCategoriesIds:
            self.__connectChildToCategory(newCategory.getId(), selectedCategoryId)
        self.__expandAndCollapseRows(False, False)

    def _deleteCategories(self, item, data):
        # TODO: Add confirmation dialog box
        for categoryId in self.__selectedCategoriesIds:
            category = env.shelf.getCategory(categoryId)
            for child in list(category.getChildren()):
                # The backend automatically disconnects childs when a category
                # is deleted, but we do it ourself to make sure that the
                # treeview widget is updated
                self.__disconnectChild(child.getId(), categoryId)
            env.shelf.deleteCategory(categoryId)
            env.shelf.flushCategoryCache()
            self.__forEachCategoryRow(self.__deleteCategoriesHelper, categoryId)

    def __deleteCategoriesHelper(self, categoryRow, categoryIdToDelete):
        if categoryRow[self.__COLUMN_CATEGORY_ID] == categoryIdToDelete:
            self.__categoryModel.remove(categoryRow.iter)

    def _disconnectCategory(self, item, data):
        for (categoryId, parentIds) in self.__selectedCategoriesIds.items():
            for parentId in parentIds:
                if not parentId == None: # Not possible to disconnect root categories
                    self.__disconnectChild(categoryId, parentId)

    def _editProperties(self, item, data):
        for categoryId in self.__selectedCategoriesIds:
            dialog = CategoryDialog("Change properties", categoryId)
            dialog.run(self._editPropertiesHelper, data=categoryId)

    def _editPropertiesHelper(self, tag, desc, categoryId):
         category = env.shelf.getCategory(categoryId)
         category.setTag(tag)
         category.setDescription(desc)
         env.shelf.flushCategoryCache()
         self.__forEachCategoryRow(self.__updatePropertiesFromShelf, categoryId)

    def _selectionFunction(self, path, b):
        return not self.__ignoreSelectEvent

        
######################################################################
### Private

    __COLUMN_CATEGORY_ID  = 0
    __COLUMN_DESCRIPTION  = 1
    __COLUMN_CONNECTED    = 2
    __COLUMN_INCONSISTENT = 3
        
    def __loadCategorySubTree(self, parent, category):
        # TODO Do we have to use iterators here or can we use pygtks simplified syntax?
        iter = self.__categoryModel.append(parent)
        self.__categoryModel.set_value(iter, self.__COLUMN_CATEGORY_ID, category.getId())
        self.__categoryModel.set_value(iter, self.__COLUMN_DESCRIPTION, category.getDescription())
        self.__categoryModel.set_value(iter, self.__COLUMN_CONNECTED, False)
        self.__categoryModel.set_value(iter, self.__COLUMN_INCONSISTENT, False)
        for child in category.getChildren():
            self.__loadCategorySubTree(iter, child)
            
    def __buildQueryFromSelection(self):
        if env.widgets["categoriesOr"].get_active():
            operator = " or "
        else:
            operator = " and "
        query = ""
        for categoryId in self.__selectedCategoriesIds:
            categoryTag = env.shelf.getCategory(categoryId).getTag()
            if query:
                query += operator
            query += categoryTag
        return query

    def __updateContextMenu(self):
        # TODO Create helper functions to use from this method
        if len(self.__selectedCategoriesIds) == 0:
            self._deleteItem.set_sensitive(False)
            self._createChildItem.set_sensitive(False)
            self._copyItem.set_sensitive(False)
            self._cutItem.set_sensitive(False)
            self._pasteItem.set_sensitive(False)
            self._disconnectItem.set_sensitive(False)
        else:
            self._deleteItem.set_sensitive(True)
            self._createChildItem.set_sensitive(True)
            self._copyItem.set_sensitive(True)
            self._cutItem.set_sensitive(True)
            if env.clipboard.hasCategories():
                self._pasteItem.set_sensitive(True)
            else:
                self._pasteItem.set_sensitive(False)
            self._disconnectItem.set_sensitive(True)
        if len(self.__selectedCategoriesIds) == 1:
            self._propertiesItem.set_sensitive(True)
        else:
            self._propertiesItem.set_sensitive(False)
        
    def __updateToggleColumn(self):
        # find out which categories are connected, not connected or
        # partitionally connected to selected objects
        nrSelectedObjectsInCategory = {}
        nrSelectedObjects = 0
        for object in self.__objectCollection.getObjectSelection().getSelectedObjects():
            nrSelectedObjects += 1
            for category in object.getCategories():
                categoryId = category.getId()
                try:
                    nrSelectedObjectsInCategory[categoryId] += 1
                except KeyError:
                        nrSelectedObjectsInCategory[categoryId] = 1
        self.__forEachCategoryRow(self.__updateToggleColumnHelper,
                                  (nrSelectedObjects, nrSelectedObjectsInCategory))

    def __updateToggleColumnHelper(self,
                                   categoryRow,
                                   (nrSelectedObjects, nrSelectedObjectsInCategory)):
        categoryId = categoryRow[self.__COLUMN_CATEGORY_ID]
        if categoryId in nrSelectedObjectsInCategory:
            if nrSelectedObjectsInCategory[categoryId] < nrSelectedObjects:
                # Some of the selected objects are connected to the category
                categoryRow[self.__COLUMN_CONNECTED] = False
                categoryRow[self.__COLUMN_INCONSISTENT] = True
            else:
                # All of the selected objects are connected to the category
                categoryRow[self.__COLUMN_CONNECTED] = True
                categoryRow[self.__COLUMN_INCONSISTENT] = False
        else:
            # None of the selected objects are connected to the category
            categoryRow[self.__COLUMN_CONNECTED] = False
            categoryRow[self.__COLUMN_INCONSISTENT] = False

    def __forEachCategoryRow(self, function, data=None, categoryRows=None):
        # We can't use gtk.TreeModel.foreach() since it does not pass a row
        # to the callback function.
        if not categoryRows:
            categoryRows=self.__categoryModel
        for categoryRow in categoryRows:
            function(categoryRow, data)
            self.__forEachCategoryRow(function, data, categoryRow.iterchildren())
        
    def __expandAndCollapseRows(self, autoExpand, autoCollapse, categoryRows=None):
        if categoryRows is None:
            categoryRows=self.__categoryModel
        someRowsExpanded = False
        for categoryRow in categoryRows:
            expandThisRow = False
            # Expand all rows that are selected or has expanded childs
            childRowsExpanded = self.__expandAndCollapseRows(autoExpand,
                                                            autoCollapse,
                                                            categoryRow.iterchildren())
            if (childRowsExpanded
                or self.__categoryView.get_selection().path_is_selected(categoryRow.path)):
                expandThisRow = True
            # Auto expand all rows that has a checked toggle
            if autoExpand:
                if (categoryRow[self.__COLUMN_CONNECTED]
                    or categoryRow[self.__COLUMN_INCONSISTENT]):
                    expandThisRow = True
            if expandThisRow:
                self.__categoryView.expand_row(categoryRow.path, False)
                someRowsExpanded = True
            # Auto collapse?
            elif autoCollapse:
                self.__categoryView.collapse_row(categoryRow.path)
        return someRowsExpanded
                
    def __connectChildToCategory(self, childId, parentId):
        try:
            # Update shelf
            childCategory = env.shelf.getCategory(childId)
            parentCategory = env.shelf.getCategory(parentId)
            parentCategory.connectChild(childCategory)
            env.shelf.flushCategoryCache()
            # Update widget modell
            # If we reload the whole category tree from the shelf, we would lose
            # the widgets information about current selected categories,
            # expanded categories and the widget's scroll position. Hence,
            # we update our previously loaded model instead.        
            self.__connectChildToCategoryHelper(parentId,
                                                childCategory,
                                                self.__categoryModel)
        except CategoriesAlreadyConnectedError:
            print "Error: Categories already connected"
            # TODO: Show dialog box with error message

    def __connectChildToCategoryHelper(self, parentId, childCategory, categoryRows):
        for categoryRow in categoryRows:
            if categoryRow[self.__COLUMN_CATEGORY_ID] == parentId:
                self.__loadCategorySubTree(categoryRow.iter, childCategory)
            else:
                self.__connectChildToCategoryHelper(parentId, childCategory, categoryRow.iterchildren())
                                     
    def __disconnectChild(self, childId, parentId):
        # Update shelf
        childCategory = env.shelf.getCategory(childId)
        parentCategory = env.shelf.getCategory(parentId)
        if childCategory in env.shelf.getRootCategories():
            alreadyWasRootCategory = True
        else:
            alreadyWasRootCategory = False
        parentCategory.disconnectChild(childCategory)
        env.shelf.flushCategoryCache()
        # Update widget modell.
        # If we reload the whole category tree from the shelf, we would lose
        # the widgets information about current selected categories,
        # expanded categories and the widget's scroll position. Hence,
        # we update our previously loaded model instead.
        self.__disconnectChildHelper(childId,
                                    parentId,
                                    None,
                                    self.__categoryModel)
        if not alreadyWasRootCategory:
            for c in env.shelf.getRootCategories():
                if c.getId() == childCategory.getId():
                    self.__loadCategorySubTree(None, childCategory)
                    break

    def __disconnectChildHelper(self, wantedChildId, wantedParentId,
                                parentId, categoryRows):
        for categoryRow in categoryRows:
            id = categoryRow[self.__COLUMN_CATEGORY_ID]
            if id == wantedChildId and parentId == wantedParentId:
                self.__categoryModel.remove(categoryRow.iter)
            self.__disconnectChildHelper(wantedChildId, wantedParentId, id, categoryRow.iterchildren())
            
    def __updatePropertiesFromShelf(self, categoryRow, categoryId):
        if categoryRow[self.__COLUMN_CATEGORY_ID] == categoryId:
            category = env.shelf.getCategory(categoryId)
            categoryRow[self.__COLUMN_DESCRIPTION] = category.getDescription()
    
class ClipboardCategories:
    COPY = 1
    CUT = 2
    categories = None
    type = None

