import gtk
from environment import env
from sets import Set
from gkofoto.objectcollectionview import *
from sets import Set
from objectcollection import *
from menuhandler import *

class TableView(ObjectCollectionView):

###############################################################################
### Public

    def __init__(self):
        env.debug("Init TableView")
        ObjectCollectionView.__init__(self, env.widgets["tableView"])
        selection = self._viewWidget.get_selection()
        selection.set_mode(gtk.SELECTION_MULTIPLE)
        self.__selectionLocked = False
        self._viewWidget.connect("drag_data_received", self._onDragDataReceived)
        self._viewWidget.connect("drag-data-get", self._onDragDataGet)
        self.__userChosenColumns = {}
        self.__createdColumns = {}
        self.__editedCallbacks = {}
        self._connectedOids = []
        self.__hasFocus = False
        # Import the users setting in the configuration file for
        # which columns that shall be shown.
        columnLocation = 0
        for columnName in env.defaultTableViewColumns:
            self.__userChosenColumns[columnName] = columnLocation
            columnLocation += 1

    def importSelection(self, objectSelection):
        if not self.__selectionLocked:
            env.debug("TableView is importing selection")
            self.__selectionLocked = True
            selection = self._viewWidget.get_selection()
            selection.unselect_all()
            for rowNr in objectSelection:
                selection.select_path(rowNr)
            rowNr = self._objectCollection.getObjectSelection().getLowestSelectedRowNr()
            if rowNr is not None:
                # Scroll to first selected object in view
                self._viewWidget.scroll_to_cell(rowNr, None, False, 0, 0)
            self.__selectionLocked = False
        self._updateContextMenu()
        self._updateMenubarSortMenu()

    def fieldsDisabled(self, fields):
        env.debug("Table view disable fields: " + str(fields))
        self.__removeColumnsAndUpdateLocation(fields)
        for columnName in fields:
            self.__viewGroup[columnName].set_sensitive(False)

    def fieldsEnabled(self, fields):
        env.debug("Table view enable fields: " + str(fields))
        objectMetadataMap = self._objectCollection.getObjectMetadataMap()
        for columnName in fields:
            self.__viewGroup[columnName].set_sensitive(True)
            if columnName not in self.__createdColumns:
                if columnName in self.__userChosenColumns:
                    self.__createColumn(columnName, objectMetadataMap, self.__userChosenColumns[columnName])

    def _showHelper(self):
        env.enter("TableView.showHelper()")
        env.widgets["tableViewScroll"].show()
        self._viewWidget.grab_focus()
        env.exit("TableView.showHelper()")

    def _hideHelper(self):
        env.enter("TableView.hideHelper()")
        env.widgets["tableViewScroll"].hide()
        env.exit("TableView.hideHelper()")

    def _connectObjectCollectionHelper(self):
        env.enter("Connecting TableView to object collection")
        # Set model
        self._viewWidget.set_model(self._objectCollection.getModel())
        # Create columns
        objectMetadataMap = self._objectCollection.getObjectMetadataMap()
        disabledFields = self._objectCollection.getDisabledFields()
        columnLocationList = self.__userChosenColumns.items()
        columnLocationList.sort(lambda x, y: cmp(x[1], y[1]))
        env.debug("Column locations: " + str(columnLocationList))
        for (columnName, columnLocation) in columnLocationList:
            if (columnName in objectMetadataMap and
                columnName not in disabledFields):
                self.__createColumn(columnName, objectMetadataMap)
                self.__viewGroup[columnName].activate()
        self.fieldsDisabled(self._objectCollection.getDisabledFields())
        env.exit("Connecting TableView to object collection")

    def _initDragAndDrop(self):
        # Init drag & drop
        if self._objectCollection.isReorderable() and not self._objectCollection.isSortable():
            targetEntries = [("STRING", gtk.TARGET_SAME_WIDGET, 0)]
            self._viewWidget.enable_model_drag_source(gtk.gdk.BUTTON1_MASK,
                                                      targetEntries,
                                                      gtk.gdk.ACTION_MOVE)
            self._viewWidget.enable_model_drag_dest(targetEntries, gtk.gdk.ACTION_COPY)
        else:
            self._viewWidget.unset_rows_drag_source()
            self._viewWidget.unset_rows_drag_dest()

    def _disconnectObjectCollectionHelper(self):
        env.enter("Disconnecting TableView from object collection")
        self.__removeColumnsAndUpdateLocation()
        self._viewWidget.set_model(None)
        env.exit("Disconnecting TableView from object collection")

    def _freezeHelper(self):
        env.enter("TableView.freezeHelper()")
        self._clearAllConnections()
        env.exit("TableView.freezeHelper()")

    def _thawHelper(self):
        env.enter("TableView.thawHelper()")
        self._initDragAndDrop()
        self._connect(self._viewWidget, "focus-in-event", self._treeViewFocusInEvent)
        self._connect(self._viewWidget, "focus-out-event", self._treeViewFocusOutEvent)
        self._connect(self._viewWidget.get_selection(), "changed", self._widgetSelectionChanged)
        env.exit("TableView.thawHelper()")

    def _createContextMenu(self, objectCollection):
        ObjectCollectionView._createContextMenu(self, objectCollection)
        self.__viewGroup = self.__createTableColumnsMenuGroup(objectCollection)
        self._contextMenu.add(self.__viewGroup.createGroupMenuItem())

    def __createTableColumnsMenuGroup(self, objectCollection):
        menuGroup = MenuGroup("View columns")
        columnNames = objectCollection.getObjectMetadataMap().keys()
        columnNames.sort()
        for columnName in columnNames:
            menuGroup.addCheckedMenuItem(
                columnName,
                self._viewColumnToggled,
                columnName)
        return menuGroup

    def _clearContextMenu(self):
        ObjectCollectionView._clearContextMenu(self)
        self.__viewGroup = None

    def _hasFocus(self):
        return self.__hasFocus

###############################################################################
### Callback functions registered by this class but invoked from other classes.

    def _treeViewFocusInEvent(self, widget, event, data):
        if self.__hasFocus:
            # Work-around for some bug that makes the focus-out signal
            # disappear.
            return
        self.__hasFocus = True
        oc = self._objectCollection
        for widgetName, function in [
                ("menubarCut", self._objectCollection.cut),
                ("menubarCopy", self._objectCollection.copy),
                ("menubarPaste", self._objectCollection.paste),
                ("menubarDelete", self._objectCollection.delete),
                ("menubarDestroy", oc.destroy),
                ("menubarClear", lambda x: widget.get_selection().unselect_all()),
                ("menubarSelectAll", lambda x: widget.get_selection().select_all()),
                ("menubarProperties", oc.albumProperties),
                ("menubarCreateAlbumChild", oc.createAlbumChild),
                ("menubarRegisterAndAddImages", oc.registerAndAddImages),
                ("menubarGenerateHtml", oc.generateHtml),
                ("menubarOpenImage", oc.openImage),
                ("menubarRotateLeft", oc.rotateImageLeft),
                ("menubarRotateRight", oc.rotateImageRight),
                ]:
            w = env.widgets[widgetName]
            oid = w.connect("activate", function)
            self._connectedOids.append((w, oid))

        self._updateContextMenu()

        for widgetName in [
                "menubarClear",
                "menubarSelectAll"
                ]:
            env.widgets[widgetName].set_sensitive(True)

    def _treeViewFocusOutEvent(self, widget, event, data):
        self.__hasFocus = False
        for (widget, oid) in self._connectedOids:
            widget.disconnect(oid)
        self._connectedOids = []
        for widgetName in [
                "menubarCut",
                "menubarCopy",
                "menubarPaste",
                "menubarDelete",
                "menubarDestroy",
                "menubarClear",
                "menubarSelectAll",
                "menubarProperties",
                "menubarCreateAlbumChild",
                "menubarRegisterAndAddImages",
                "menubarGenerateHtml",
                "menubarOpenImage",
                "menubarRotateLeft",
                "menubarRotateRight",
                ]:
            env.widgets[widgetName].set_sensitive(False)

    def _widgetSelectionChanged(self, selection, data):
        if not self.__selectionLocked:
            env.enter("TableView selection changed")
            self.__selectionLocked = True
            rowNrs = []
            selection.selected_foreach(lambda model,
                                       path,
                                       iter:
                                       rowNrs.append(path[0]))
            self._objectCollection.getObjectSelection().setSelection(rowNrs)
            self.__selectionLocked = False
            env.exit("TableView selection changed")

    def _onDragDataGet(self, widget, dragContext, selection, info, timestamp):
        selectedRows = []
        # TODO replace with "get_selected_rows()" when it is introduced in Pygtk 2.2 API
        self._viewWidget.get_selection().selected_foreach(lambda model,
                                                          path,
                                                          iter:
                                                          selectedRows.append(model[path]))
        if len(selectedRows) == 1:
            # Ignore drag & drop if zero or more then one row is selected
            # Drag & drop of multiple rows will probably come in gtk 2.4.
            # http://mail.gnome.org/archives/gtk-devel-list/2003-December/msg00160.html
            sourceRowNumber = str(selectedRows[0].path[0])
            selection.set_text(sourceRowNumber, len(sourceRowNumber))
        else:
            env.debug("Ignoring drag&drop when only one row is selected")


    def _onDragDataReceived(self, treeview, dragContext, x, y, selection, info, eventtime):
        targetData = treeview.get_dest_row_at_pos(x, y)
        if selection.get_text() == None:
            dragContext.finish(False, False, eventtime)
        else:
            model = self._objectCollection.getModel()
            if targetData == None:
                targetPath = (len(model) - 1,)
                dropPosition = gtk.TREE_VIEW_DROP_AFTER
            else:
                targetPath, dropPosition = targetData
            sourceRowNumber = int(selection.get_text())
            if sourceRowNumber == targetPath[0]:
                # dropped on itself
                dragContext.finish(False, False, eventtime)
            else:
                # The continer must have a getChildren() and a setChildren()
                # method as for example the album class has.
                container = self._objectCollection.getContainer()
                children = list(container.getChildren())
                sourceRow = model[sourceRowNumber]
                targetIter = model.get_iter(targetPath)
                objectSelection = self._objectCollection.getObjectSelection()
                if (dropPosition == gtk.TREE_VIEW_DROP_INTO_OR_BEFORE
                    or dropPosition == gtk.TREE_VIEW_DROP_BEFORE):
                    container.setChildren(self.__moveListItem(children,
                                                              sourceRowNumber,
                                                              targetPath[0]))
                    model.insert_before(sibling=targetIter, row=sourceRow)
                    self._objectCollection.signalRowInserted()
                    model.remove(sourceRow.iter)
                    # TODO update the album tree widget?
                elif (dropPosition == gtk.TREE_VIEW_DROP_INTO_OR_AFTER
                      or dropPosition == gtk.TREE_VIEW_DROP_AFTER):
                    container.setChildren(self.__moveListItem(children,
                                                              sourceRowNumber,
                                                              targetPath[0] + 1))
                    model.insert_after(sibling=targetIter, row=sourceRow)
                    model.remove(sourceRow.iter)
                    # TODO update the album tree widget?
                objectSelection.setSelection([targetPath[0]])
                # I've experienced that the drag-data-delete signal isn't
                # always emitted when I drag & drop rapidly in the TreeView.
                # And when it is missing the source row is not removed as is
                # should. It is probably an bug in gtk+ (or maybe in pygtk).
                # It only happens sometimes and I have not managed to reproduce
                # it with a simpler example. Hence we remove the row ourself
                # and are not relying on the drag-data-delete-signal.
                # http://bugzilla.gnome.org/show_bug.cgi?id=134997
                removeSourceRowAutomatically = False
                dragContext.finish(True, removeSourceRowAutomatically, eventtime)

    def _viewColumnToggled(self, checkMenuItem, columnName):
        if checkMenuItem.get_active():
            if columnName not in self.__createdColumns:
                self.__createColumn(columnName,
                                    self._objectCollection.getObjectMetadataMap())
                # The correct columnLocation is stored when the column is removed
                # there is no need to store the location when it is created
                # since the column order may be reordered later before it is removed.
        else:
            # Since the column has been removed explicitly by the user
            # we dont store the column's relative location.
            try:
                del self.__userChosenColumns[columnName]
            except KeyError:
                pass
            if columnName in self.__createdColumns:
                self.__removeColumn(columnName)

###############################################################################
### Private

    def __createColumn(self, columnName, objectMetadataMap, location=-1):
        (objtype, column, editedCallback, editedCallbackData) = objectMetadataMap[columnName]
        if objtype == gtk.gdk.Pixbuf:
            renderer = gtk.CellRendererPixbuf()
            column = gtk.TreeViewColumn(columnName, renderer, pixbuf=column)
            env.debug("Created a PixBuf column for " + columnName)
        elif objtype == gobject.TYPE_STRING or objtype == gobject.TYPE_INT:
            renderer = gtk.CellRendererText()
            column = gtk.TreeViewColumn(columnName,
                                        renderer,
                                        text=column,
                                        editable=ObjectCollection.COLUMN_ROW_EDITABLE)
            column.set_resizable(True)
            if editedCallback:
                cid = renderer.connect("edited",
                                       editedCallback,
                                       column,
                                       editedCallbackData)
                self.__editedCallbacks[columnName] = (cid, renderer)
                env.debug("Created a Text column with editing callback for " + columnName)
            else:
                env.debug("Created a Text column without editing callback for " + columnName)
        else:
            print "Warning, unsupported type for column ", columnName
            return
        column.set_reorderable(True)
        self._viewWidget.insert_column(column, location)
        self.__createdColumns[columnName] = column
        return column

    def __removeColumn(self, columnName):
        column = self.__createdColumns[columnName]
        self._viewWidget.remove_column(column)
        if columnName in self.__editedCallbacks:
            (cid, renderer) = self.__editedCallbacks[columnName]
            renderer.disconnect(cid)
            del self.__editedCallbacks[columnName]
        del self.__createdColumns[columnName]
        column.destroy()
        env.debug("Removed column " + columnName)

    def __removeColumnsAndUpdateLocation(self, columnNames=None):
       # Remove columns and store their relative locations for next time
       # they are re-created.
       columnLocation = 0
       for column in self._viewWidget.get_columns():
           columnName = column.get_title()
           # TODO Store the column width and reuse it when the column is
           #      recreated. I don't know how to store the width since
           #      column.get_width() return correct values for columns
           #      containing a gtk.CellRendererPixbuf but only 0 for all
           #      columns containing a gtk.CellRendererText. It is probably
           #      a bug in gtk och pygtk. I have not yet reported the bug.
           if columnNames is None or columnName in columnNames:
               if columnName in self.__createdColumns:
                   self.__removeColumn(columnName)
                   self.__userChosenColumns[columnName] = columnLocation
           columnLocation += 1

    def __moveListItem(self, list, currentIndex, newIndex):
        if currentIndex == newIndex:
            return list
        if currentIndex < newIndex:
            newIndex -= 1
        movingChild = list[currentIndex]
        del list[currentIndex]
        return list[:newIndex] + [movingChild] + list[newIndex:]
