import gtk

from environment import env
from sets import Set
from gnomekofoto.objectcollectionview import *
# from tablecontextmenu import *
from objectcollection import *
class TableView(ObjectCollectionView):

###############################################################################            
### Public
    
    def __init__(self, objectCollection):
        ObjectCollectionView.__init__(self,
                                      objectCollection,
                                      env.widgets["tableView"],
                                      None) # TODO create & pass context menu
        selection = self._viewWidget.get_selection()
        selection.set_mode(gtk.SELECTION_MULTIPLE)
        selection.connect('changed', self._widgetSelectionChanged)
        self._viewWidget.connect("drag_data_received", self._onDragDataReceived)
        self._viewWidget.connect("drag-data-get", self._onDragDataGet)

    def setObjectCollection(self, objectCollection):
        ObjectCollectionView.setObjectCollection(self, objectCollection)
        self.__configureColumns(objectCollection)
        self._viewWidget.set_model(objectCollection.getModel())
        if objectCollection.isReorderable() and not objectCollection.isSortable():
            targetEntries = [("STRING", gtk.TARGET_SAME_WIDGET, 0)]
            self._viewWidget.enable_model_drag_source(gtk.gdk.BUTTON1_MASK, targetEntries, gtk.gdk.ACTION_MOVE)
            self._viewWidget.enable_model_drag_dest(targetEntries, gtk.gdk.ACTION_COPY)
        else:
            self._viewWidget.unset_rows_drag_source()
            self._viewWidget.unset_rows_drag_dest()
            
    def show(self):
        env.widgets["tableViewScroll"].show()
        self._viewWidget.grab_focus()
        self.__importSelection()
        self.__selectionLocked = gtk.FALSE
        for row in self._objectCollection.getModel():
            if row[ObjectCollection.COLUMN_OBJECT_ID] in self._objectCollection.getSelectedIds():
                self._viewWidget.scroll_to_cell(row.path, None, gtk.TRUE, 0, 0)
                break
            
    def hide(self):
        self.__selectionLocked = gtk.TRUE       
        env.widgets["tableViewScroll"].hide()

###############################################################################
### Callback functions registered by this class but invoked from other classes.

    def _widgetSelectionChanged(self, selection):
        if not self.__selectionLocked:
            self._objectCollection.unselectAll(gtk.FALSE)
            selectedRows = []
            # TODO replace with "get_selected_rows()" when it is introduced in Pygtk 2.2 API                
            selection.selected_foreach(lambda model,
                                       path,
                                       iter:
                                       selectedRows.append(model[path]))
            for row in selectedRows:
                self._objectCollection.selectRow(row, gtk.FALSE)
            self._objectCollection.sendSelectionChangedSignal()

            
    def _onDragDataGet(self, widget, dragContext, selection, info, timestamp):
        selectedRows = []
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

            
    def _onDragDataReceived(self, treeview, dragContext, x, y, selection, info, eventtime):
        targetData = treeview.get_dest_row_at_pos(x, y)
        if targetData == None or selection.get_text() == None:
            dragContext.finish(gtk.FALSE, gtk.FALSE, eventtime)
        else:
            targetPath, dropPosition = targetData
            sourceRowNumber = int(selection.get_text())
            model = self._objectCollection.getModel()
            if sourceRowNumber == targetPath[0]:
                # dropped on itself
                dragContext.finish(gtk.FALSE, gtk.FALSE, eventtime)
            else:
                # The continer must have a getChildren() and a setChildren()
                # method as for example the album class has.
                container = self._objectCollection.getContainer()
                children = list(container.getChildren())
                sourceRow = model[sourceRowNumber]
                targetIter = model.get_iter(targetPath)
                if dropPosition == gtk.TREE_VIEW_DROP_INTO_OR_BEFORE or dropPosition == gtk.TREE_VIEW_DROP_BEFORE:
                    container.setChildren(self.__moveListItem(children, sourceRowNumber, targetPath[0]))
                    model.insert_before(sibling=targetIter, row=sourceRow)
                    model.remove(sourceRow.iter)
                elif dropPosition == gtk.TREE_VIEW_DROP_INTO_OR_AFTER or dropPosition == gtk.TREE_VIEW_DROP_AFTER:
                    container.setChildren(self.__moveListItem(children, sourceRowNumber, targetPath[0] + 1))
                    model.insert_after(sibling=targetIter, row=sourceRow)
                    model.remove(sourceRow.iter)
                # I've experienced that the drag-data-delete signal isn't
                # always emitted when I drag & drop rapidly in the TreeView.
                # And when it is missing the source row is not removed as is
                # should. It is probably an bug in gtk+ (or maybe in pygtk).
                # It only happens sometimes and I have not managed to reproduce
                # it with a simpler example. Hence we remove the row ourself
                # and are not relying on the drag-data-delete-signal.
                removeSourceRowAutomatically = gtk.FALSE
                dragContext.finish(gtk.TRUE, removeSourceRowAutomatically, eventtime)
            
            
###############################################################################        
### Private
            
    __selectionLocked = gtk.FALSE
    
    def __importSelection(self):
        selection = self._viewWidget.get_selection()
        selection.unselect_all()
        for row in self._objectCollection.getSelectedRows():
            selection.select_path(row.path[0])

    def __configureColumns(self, objectCollection):
        # TODO Make it possible to configure column order somehow?
        # TODO Where should env.defaultTableViewColumns be handled?
        for column in self._viewWidget.get_columns():
            self._viewWidget.remove_column(column)        
        for name, data in objectCollection.getAttributes().items():
            self.__createColumn(name, data)
        for name, data in objectCollection.getNonAttributes().items():
            self.__createColumn(name, data)            
           
    def __createColumn(self, name, (type, column, editedCallback, editedCallbackData)):
        if type == gtk.gdk.Pixbuf:
            renderer = gtk.CellRendererPixbuf()
            column = gtk.TreeViewColumn("", renderer, pixbuf=column)
        elif type == gobject.TYPE_STRING or type == gobject.TYPE_INT:
            renderer = gtk.CellRendererText()
            column = gtk.TreeViewColumn(name,
                                        renderer,
                                        text=column,
                                        editable=ObjectCollection.COLUMN_ROW_EDITABLE)
            column.set_resizable(gtk.TRUE)
            if editedCallback:
                renderer.connect("edited",
                                 editedCallback,
                                 column,
                                 editedCallbackData)
        else:
            print "Warning, unsupported type for column ", name
            return
        column.set_reorderable(gtk.TRUE)
        self._viewWidget.append_column(column)
        
    def __moveListItem(self, list, currentIndex, newIndex):
        if currentIndex == newIndex:
            return list
        if currentIndex < newIndex:
            newIndex -= 1
        movingChild = list[currentIndex]
        del list[currentIndex]
        return list[:newIndex] + [movingChild] + list[newIndex:]

            
        
