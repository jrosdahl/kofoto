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
        self._tableView.set_model(loadedImages.model)
        self._model = loadedImages.model
        for column in self._tableView.get_columns():
            self._tableView.remove_column(column)
        self._createThumbnailColumn()
        self._createIdColumn()
        self._createLocationColumn()
        self._createAttributeColumns(loadedImages.attributeNamesMap)

    def _createThumbnailColumn(self):
        renderer = gtk.CellRendererPixbuf()
        column = gtk.TreeViewColumn("Thumbnail", renderer, pixbuf=Images.COLUMN_THUMBNAIL)
        self._tableView.append_column(column)

    def _createIdColumn(self):
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn("ImageId", renderer, text=Images.COLUMN_IMAGE_ID)
        self._tableView.append_column(column)

    def _createLocationColumn(self):
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Location", renderer, text=Images.COLUMN_LOCATION)
        self._tableView.append_column(column)        

    def _createAttributeColumns(self, attributeNamesMap):
        for attributeName, value in attributeNamesMap.items():
            renderer = gtk.CellRendererText()
            column = gtk.TreeViewColumn(attributeName,
                                        renderer,
                                        text=attributeNamesMap[attributeName])
            self._tableView.append_column(column)
        
    def freeze(self):
        pass

    def thaw(self):
        pass

    def show(self):
        env.widgets["tableViewScroll"].show()
        self._tableView.grab_focus()
        for image in self._model:
            if image[Images.COLUMN_IMAGE_ID] in self._selectedImages:
                self._tableView.scroll_to_cell(image.path, None, gtk.TRUE, 0, 0)
                break

    def hide(self):
        env.widgets["tableViewScroll"].hide()
        
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
            return gtk.FALSE
