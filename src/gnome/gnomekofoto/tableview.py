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

    def setObjectCollection(self, objectCollection):
        self.__configureColumns(objectCollection)
        self._viewWidget.set_model(objectCollection.getModel())
        # self._contextMenu.update(objectCollection)
            
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
