import gtk

from environment import env
from objects import *
from sets import Set

class TableView:
    _ALBUM_TAG_COLUMN_NAME = u"Album tag"
    _modelConnections = []

    def __init__(self, loadedObjects, selectedObjects, contextMenu):
        self._locked = gtk.FALSE
        self._tableView = env.widgets["tableView"]
        selection = self._tableView.get_selection()
        selection.set_mode(gtk.SELECTION_MULTIPLE)
        self._contextMenu = contextMenu
        self._selectedObjects = selectedObjects
        self._tableView.connect("button_press_event", self._button_pressed)
        selection.connect('changed', self._widgetSelectionUpdated)
        self.setModel(loadedObjects)
        self._loadedObjects = loadedObjects

    def setModel(self, loadedObjects):
        self._model = loadedObjects.model
        self._tableView.set_model(self._model)
        for column in self._tableView.get_columns():
            self._tableView.remove_column(column)
        self._createThumbnailColumn()
        self._createIdColumn()
        self._createLocationColumn()
        self._createAlbumTagColumn()
        self._createAttributeColumns(loadedObjects.attributeNamesMap)
        for c in self._modelConnections:
            self._model.disconnect(c)
        del self._modelConnections[:]
        self._model = loadedObjects.model
        c = self._model.connect("row_inserted", self._updateAlbumTagColumn)
        self._modelConnections.append(c)
        c = self._model.connect("row_deleted", self._updateAlbumTagColumn)
        self._modelConnections.append(c)
        

    def _createThumbnailColumn(self):
        renderer = gtk.CellRendererPixbuf()
        column = gtk.TreeViewColumn("", renderer, pixbuf=Objects.COLUMN_THUMBNAIL)
        column.set_reorderable(gtk.TRUE)
        self._tableView.append_column(column)

    def _createAlbumTagColumn(self):
        renderer = gtk.CellRendererText()
        columnName = self._ALBUM_TAG_COLUMN_NAME
        column = gtk.TreeViewColumn(columnName, renderer, text=Objects.COLUMN_ALBUM_TAG)
        column.set_reorderable(gtk.TRUE)
        column.set_resizable(gtk.TRUE)
        self._contextMenu.addTableViewColumn(columnName, Objects.COLUMN_ALBUM_TAG, column)
        self._tableView.append_column(column)

    def _createIdColumn(self):
        renderer = gtk.CellRendererText()
        columnName = u"ObjectId"
        column = gtk.TreeViewColumn(columnName, renderer, text=Objects.COLUMN_OBJECT_ID)
        column.set_resizable(gtk.TRUE)
        column.set_reorderable(gtk.TRUE)
        self._contextMenu.addTableViewColumn(columnName, Objects.COLUMN_OBJECT_ID, column)
        self._tableView.append_column(column)

    def _createLocationColumn(self):
        renderer = gtk.CellRendererText()
        columnName = u"Location"
        column = gtk.TreeViewColumn(columnName, renderer,
                                    text=Objects.COLUMN_LOCATION)
        column.set_resizable(gtk.TRUE)
        column.set_reorderable(gtk.TRUE)
        self._contextMenu.addTableViewColumn(columnName, Objects.COLUMN_LOCATION, column)
        self._tableView.append_column(column)        

    def _createAttributeColumns(self, attributeNamesMap):
        allAttributeNames = attributeNamesMap.keys()
        allAttributeNames.sort()
        for attributeName in allAttributeNames:
            columnNumber = attributeNamesMap[attributeName]
            renderer = gtk.CellRendererText()
            column = gtk.TreeViewColumn(attributeName,
                                        renderer,
                                        text=columnNumber,
                                        editable=Objects.COLUMN_ROW_EDITABLE)
            column.set_resizable(gtk.TRUE)
            column.set_reorderable(gtk.TRUE)
            renderer.connect("edited", self._attribute_editing_done,
                             columnNumber,
                             attributeName)
            self._contextMenu.addTableViewColumn(attributeName, columnNumber, column)
            self._tableView.append_column(column)

    def _attribute_editing_done(self, renderer, path, value, column, attributeName):
        iter = self._model.get_iter(path)
        oldValue = self._model.get_value(iter, column)
        if not oldValue:
            oldValue = u""
        value = unicode(value, "utf-8")
        if oldValue != value:
            # TODO Show dialog and ask for confirmation?
            objectId = self._model.get_value(iter, Objects.COLUMN_OBJECT_ID)
            object = env.shelf.getObject(objectId)
            object.setAttribute(attributeName, value)
            self._model.set_value(iter, column, value)
            
    def freeze(self):
        pass

    def thaw(self):
        pass

    def show(self):
        env.widgets["tableViewScroll"].show()
        self._contextMenu.tableViewViewItem.show()
        self._tableView.grab_focus()
        for object in self._model:
            if object[Objects.COLUMN_OBJECT_ID] in self._selectedObjects:
                self._tableView.scroll_to_cell(object.path, None, gtk.TRUE, 0, 0)
                break
        self._updateAlbumTagColumn()

    def _updateAlbumTagColumn(self, *foo):
        viewItem = self._contextMenu.viewMenuItems[self._ALBUM_TAG_COLUMN_NAME]
        if self._loadedObjects.albumsInList:
            viewItem.set_active(gtk.TRUE)
        else:
            viewItem.set_active(gtk.FALSE)
            
    def hide(self):
        env.widgets["tableViewScroll"].hide()
        self._contextMenu.tableViewViewItem.hide()
        
    def selectionUpdated(self):
        if not self._locked:
            self._locked = gtk.TRUE
            selection = self._tableView.get_selection()
            selection.unselect_all()
            iter = self._model.get_iter_first()
            index = 0
            while iter:
                objectId = self._model.get_value(iter, Objects.COLUMN_OBJECT_ID)
                if objectId in self._selectedObjects:
                    selection.select_path(index)
                index = index + 1
                iter =  self._model.iter_next(iter)
            self._locked = gtk.FALSE

    def _widgetSelectionUpdated(self, selection):
        if not self._locked:
            self._locked = gtk.TRUE
            iter = self._model.get_iter_first()
            objectIdList = []
            while iter:
                if selection.iter_is_selected(iter):
                    objectId = self._model.get_value(iter, Objects.COLUMN_OBJECT_ID)
                    objectIdList.append(objectId)
                iter = self._model.iter_next(iter)
            self._selectedObjects.set(objectIdList)
            self._locked = gtk.FALSE
        
    def _button_pressed(self, widget, event):
        if event.button == 3:
            self._contextMenu.popup(None,None,None,event.button,event.time)
            return gtk.TRUE
