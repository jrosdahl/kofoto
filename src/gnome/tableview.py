import gtk

from environment import env
from images import *
from kofoto.sets import *

class TableView:

    def __init__(self, loadedImages, selectedImages, contextMenu):
        self._locked = gtk.FALSE
        self._tableView = env.widgets["tableView"]
        selection = self._tableView.get_selection()
        selection.set_mode(gtk.SELECTION_MULTIPLE)
        self._contextMenu = contextMenu
        self._selectedImages = selectedImages
        self._tableView.connect("button_press_event", self._button_pressed)
        selection.connect('changed', self._widgetSelectionUpdated)
        self.setModel(loadedImages)

    def setModel(self, loadedImages):
        self._model = loadedImages.model
        self._tableView.set_model(self._model)
        for column in self._tableView.get_columns():
            self._tableView.remove_column(column)
        self._createThumbnailColumn()
        self._createIdColumn()
        self._createLocationColumn()
        self._createAttributeColumns(loadedImages.attributeNamesMap)

    def _createThumbnailColumn(self):
        renderer = gtk.CellRendererPixbuf()
        column = gtk.TreeViewColumn("Thumbnail", renderer, pixbuf=Images.COLUMN_THUMBNAIL)
        column.set_reorderable(gtk.TRUE)
        self._tableView.append_column(column)

    def _createIdColumn(self):
        renderer = gtk.CellRendererText()
        columnName = u"ImageId"
        column = gtk.TreeViewColumn(columnName, renderer, text=Images.COLUMN_IMAGE_ID)
        column.set_resizable(gtk.TRUE)
        column.set_reorderable(gtk.TRUE)
        self._contextMenu.addTableViewColumn(columnName, Images.COLUMN_IMAGE_ID, column)
        self._tableView.append_column(column)

    def _createLocationColumn(self):
        renderer = gtk.CellRendererText()
        columnName = u"Location"
        column = gtk.TreeViewColumn(columnName, renderer,
                                    text=Images.COLUMN_LOCATION)
        column.set_resizable(gtk.TRUE)
        column.set_reorderable(gtk.TRUE)
        self._contextMenu.addTableViewColumn(columnName, Images.COLUMN_LOCATION, column)
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
                                        editable=Images.COLUMN_ROW_EDITABLE)
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
            imageId = self._model.get_value(iter, Images.COLUMN_IMAGE_ID)
            image = env.shelf.getImage(imageId)
            image.setAttribute(attributeName, value)
            self._model.set_value(iter, column, value)
            
    def freeze(self):
        pass

    def thaw(self):
        pass

    def show(self):
        env.widgets["tableViewScroll"].show()
        self._contextMenu.tableViewViewItem.show()
        self._tableView.grab_focus()
        for image in self._model:
            if image[Images.COLUMN_IMAGE_ID] in self._selectedImages:
                self._tableView.scroll_to_cell(image.path, None, gtk.TRUE, 0, 0)
                break

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
                imageId = self._model.get_value(iter, Images.COLUMN_IMAGE_ID)
                if imageId in self._selectedImages:
                    selection.select_path(index)
                index = index + 1
                iter =  self._model.iter_next(iter)
            self._locked = gtk.FALSE

    def _widgetSelectionUpdated(self, selection):
        if not self._locked:
            self._locked = gtk.TRUE
            iter = self._model.get_iter_first()
            imageIdList = []
            while iter:
                if selection.iter_is_selected(iter):
                    imageId = self._model.get_value(iter, Images.COLUMN_IMAGE_ID)
                    imageIdList.append(imageId)
                iter = self._model.iter_next(iter)
            self._selectedImages.set(imageIdList)
            self._locked = gtk.FALSE
        
    def _button_pressed(self, widget, event):
        if event.button == 3:
            self._contextMenu.popup(None,None,None,event.button,event.time)
            return gtk.TRUE
