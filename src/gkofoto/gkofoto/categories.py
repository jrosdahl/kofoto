import gobject
import gtk
import string

from environment import env
from categorydialog import CategoryDialog
from menuhandler import *
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
        self.__categoryView.connect("focus-in-event", self._categoryViewFocusInEvent)
        self.__categoryView.connect("focus-out-event", self._categoryViewFocusOutEvent)
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

        self._contextMenuGroup = MenuGroup()
        self._contextMenuGroup.addStockImageMenuItem(
            self.__cutCategoryLabel,
            gtk.STOCK_CUT,
            self._cutCategory)
        self._contextMenuGroup.addStockImageMenuItem(
            self.__copyCategoryLabel,
            gtk.STOCK_COPY,
            self._copyCategory)
        self._contextMenuGroup.addStockImageMenuItem(
            self.__pasteCategoryLabel,
            gtk.STOCK_PASTE,
            self._pasteCategory)
        self._contextMenuGroup.addStockImageMenuItem(
            self.__destroyCategoryLabel,
            gtk.STOCK_DELETE,
            self._deleteCategories)
        self._contextMenuGroup.addMenuItem(
            self.__disconnectCategoryLabel,
            self._disconnectCategory)
        self._contextMenuGroup.addMenuItem(
            self.__createChildCategoryLabel,
            self._createChildCategory)
        self._contextMenuGroup.addMenuItem(
            self.__createRootCategoryLabel,
            self._createRootCategory)
        self._contextMenuGroup.addStockImageMenuItem(
            self.__propertiesLabel,
            gtk.STOCK_PROPERTIES,
            self._editProperties)

        for item in self._contextMenuGroup:
            self._contextMenu.append(item)

        env.widgets["categorySearchButton"].set_sensitive(False)

        # Init menubar items.
        env.widgets["menubarDisconnectFromParent"].connect(
            "activate", self._disconnectCategory, None)
        env.widgets["menubarCreateChild"].connect(
            "activate", self._createChildCategory, None)
        env.widgets["menubarCreateRoot"].connect(
            "activate", self._createRootCategory, None)

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
        for category in self.__sortCategories(env.shelf.getRootCategories()):
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
            self.__mainWindow.loadQuery(query)

    def _categoryViewFocusInEvent(self, widget, event):
        self._menubarOids = []
        for widgetName, function in [
                ("menubarCut", lambda *x: self._cutCategory(None, None)),
                ("menubarCopy", lambda *x: self._copyCategory(None, None)),
                ("menubarPaste", lambda *x: self._pasteCategory(None, None)),
                ("menubarDestroy", lambda *x: self._deleteCategories(None, None)),
                ("menubarClear", lambda *x: widget.get_selection().unselect_all()),
                ("menubarSelectAll", lambda *x: widget.get_selection().select_all()),
                ("menubarProperties", lambda *x: self._editProperties(None, None)),
                ]:
            w = env.widgets[widgetName]
            oid = w.connect("activate", function)
            self._menubarOids.append((w, oid))
        self.__updateContextMenu()

    def _categoryViewFocusOutEvent(self, widget, event):
        for (widget, oid) in self._menubarOids:
            widget.disconnect(oid)

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
            cid = categoryRow[self.__COLUMN_CATEGORY_ID]
            # row.parent method gives assertion failed, dont know why. Using workaround instead.
            parentPath = categoryRow.path[:-1]
            if parentPath:
                parentId = categoryRow.model[parentPath][self.__COLUMN_CATEGORY_ID]
            else:
                parentId = None
            try:
                 self.__selectedCategoriesIds[cid].append(parentId)
            except KeyError:
                 self.__selectedCategoriesIds[cid] = [parentId]
        self.__updateContextMenu()
        env.widgets["categorySearchButton"].set_sensitive(
            len(selectedCategoryRows) > 0)

    def _connectionToggled(self, renderer, path):
        categoryRow = self.__categoryModel[path]
        category = env.shelf.getCategory(categoryRow[self.__COLUMN_CATEGORY_ID])
        if categoryRow[self.__COLUMN_INCONSISTENT] \
               or not categoryRow[self.__COLUMN_CONNECTED]:
            for obj in self.__objectCollection.getObjectSelection().getSelectedObjects():
                try:
                    obj.addCategory(category)
                except CategoryPresentError:
                    # The object was already connected to the category
                    pass
            categoryRow[self.__COLUMN_INCONSISTENT] = False
            categoryRow[self.__COLUMN_CONNECTED] = True
        else:
            for obj in self.__objectCollection.getObjectSelection().getSelectedObjects():
                obj.removeCategory(category)
            categoryRow[self.__COLUMN_CONNECTED] = False
            categoryRow[self.__COLUMN_INCONSISTENT] = False
        self.__updateToggleColumn()

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
        assert env.clipboard.hasCategories()
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
            dialog = gtk.MessageDialog(
                type=gtk.MESSAGE_ERROR,
                buttons=gtk.BUTTONS_OK,
                message_format="Category loop detected.")
            dialog.run()
            dialog.destroy()
        self.__expandAndCollapseRows(False, False)

    def _createRootCategory(self, item, data):
        dialog = CategoryDialog("Create top-level category")
        dialog.run(self._createRootCategoryHelper)

    def _createRootCategoryHelper(self, tag, desc):
        category = env.shelf.createCategory(tag, desc)
        self.__loadCategorySubTree(None, category)

    def _createChildCategory(self, item, data):
        dialog = CategoryDialog("Create subcategory")
        dialog.run(self._createChildCategoryHelper)

    def _createChildCategoryHelper(self, tag, desc):
        newCategory = env.shelf.createCategory(tag, desc)
        for selectedCategoryId in self.__selectedCategoriesIds:
            self.__connectChildToCategory(newCategory.getId(), selectedCategoryId)
        self.__expandAndCollapseRows(False, False)

    def _deleteCategories(self, item, data):
        dialogId = "destroyCategoriesDialog"
        widgets = gtk.glade.XML(env.gladeFile, dialogId)
        dialog = widgets.get_widget(dialogId)
        result = dialog.run()
        if result == gtk.RESPONSE_OK:
            for categoryId in self.__selectedCategoriesIds:
                category = env.shelf.getCategory(categoryId)
                for child in list(category.getChildren()):
                    # The backend automatically disconnects childs
                    # when a category is deleted, but we do it ourself
                    # to make sure that the treeview widget is
                    # updated.
                    self.__disconnectChild(child.getId(), categoryId)
                env.shelf.deleteCategory(categoryId)
                env.shelf.flushCategoryCache()
                self.__forEachCategoryRow(
                    self.__deleteCategoriesHelper, categoryId)
        dialog.destroy()

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

    __cutCategoryLabel = "Cut"
    __copyCategoryLabel = "Copy"
    __pasteCategoryLabel = "Paste as child(ren)"
    __destroyCategoryLabel = "Destroy..."
    __disconnectCategoryLabel = "Disconnect from parent"
    __createChildCategoryLabel = "Create subcategory..."
    __createRootCategoryLabel = "Create top-level category..."
    __propertiesLabel = "Properties"

    __COLUMN_CATEGORY_ID  = 0
    __COLUMN_DESCRIPTION  = 1
    __COLUMN_CONNECTED    = 2
    __COLUMN_INCONSISTENT = 3

    def __loadCategorySubTree(self, parent, category):
        # TODO Do we have to use iterators here or can we use pygtks simplified syntax?
        iterator = self.__categoryModel.iter_children(parent)
        while (iterator != None and
               self.__categoryModel.get_value(iterator, self.__COLUMN_DESCRIPTION) <
                   category.getDescription()):
            iterator = self.__categoryModel.iter_next(iterator)
        iterator = self.__categoryModel.insert_before(parent, iterator)
        self.__categoryModel.set_value(iterator, self.__COLUMN_CATEGORY_ID, category.getId())
        self.__categoryModel.set_value(iterator, self.__COLUMN_DESCRIPTION, category.getDescription())
        self.__categoryModel.set_value(iterator, self.__COLUMN_CONNECTED, False)
        self.__categoryModel.set_value(iterator, self.__COLUMN_INCONSISTENT, False)
        for child in self.__sortCategories(category.getChildren()):
            self.__loadCategorySubTree(iterator, child)

    def __buildQueryFromSelection(self):
        if env.widgets["categoriesOr"].get_active():
            operator = " or "
        else:
            operator = " and "
        return operator.join([env.shelf.getCategory(x).getTag()
                              for x in self.__selectedCategoriesIds])

    def __updateContextMenu(self):
        # TODO Create helper functions to use from this method
        menubarWidgetNames = [
                "menubarCut",
                "menubarCopy",
                "menubarPaste",
                "menubarDestroy",
                "menubarProperties",
                "menubarDisconnectFromParent",
                "menubarCreateChild",
                "menubarCreateRoot",
                ]
        if len(self.__selectedCategoriesIds) == 0:
            self._contextMenuGroup.disable()
            for widgetName in menubarWidgetNames:
                env.widgets[widgetName].set_sensitive(False)
            self._contextMenuGroup[
                self.__createRootCategoryLabel].set_sensitive(True)
            env.widgets["menubarCreateRoot"].set_sensitive(True)
        else:
            self._contextMenuGroup.enable()
            for widgetName in menubarWidgetNames:
                env.widgets[widgetName].set_sensitive(True)
            if not env.clipboard.hasCategories():
                self._contextMenuGroup[
                    self.__pasteCategoryLabel].set_sensitive(False)
                env.widgets["menubarPaste"].set_sensitive(False)
        propertiesItem = self._contextMenuGroup[self.__propertiesLabel]
        propertiesItemSensitive = len(self.__selectedCategoriesIds) == 1
        propertiesItem.set_sensitive(propertiesItemSensitive)
        env.widgets["menubarProperties"].set_sensitive(propertiesItemSensitive)

    def __updateToggleColumn(self):
        # find out which categories are connected, not connected or
        # partitionally connected to selected objects
        nrSelectedObjectsInCategory = {}
        nrSelectedObjects = 0
        for obj in self.__objectCollection.getObjectSelection().getSelectedObjects():
            nrSelectedObjects += 1
            for category in obj.getCategories():
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
                for a in range(len(categoryRow.path)):
                    self.__categoryView.expand_row(categoryRow.path[:a+1], False)
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
            # This is okay.
            pass

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
            cid = categoryRow[self.__COLUMN_CATEGORY_ID]
            if cid == wantedChildId and parentId == wantedParentId:
                self.__categoryModel.remove(categoryRow.iter)
            self.__disconnectChildHelper(wantedChildId, wantedParentId, cid, categoryRow.iterchildren())

    def __updatePropertiesFromShelf(self, categoryRow, categoryId):
        if categoryRow[self.__COLUMN_CATEGORY_ID] == categoryId:
            category = env.shelf.getCategory(categoryId)
            categoryRow[self.__COLUMN_DESCRIPTION] = category.getDescription()

    def __sortCategories(self, categoryIter):
        categories = list(categoryIter)
        categories.sort(lambda x, y: cmp(x.getDescription(), y.getDescription()))
        return categories

class ClipboardCategories:
    COPY = 1
    CUT = 2
    categories = None
    type = None
