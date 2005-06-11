import os
import gtk
from environment import env
from kofoto.shelf import ImageVersionType
from gkofoto.menuhandler import MenuGroup
from imageversionsdialog import ImageVersionsDialog
from sets import Set as set
from kofoto.alternative import Alternative

_imageVersionTypeToStringMap = {
    ImageVersionType.Important: "Important",
    ImageVersionType.Original: "Original",
    ImageVersionType.Other: "Other",
}

class ImageVersionsList(gtk.ScrolledWindow):
    def __init__(self):
        gtk.ScrolledWindow.__init__(self)
        self.__vbox = gtk.VBox()
        self.__vbox.set_border_width(5)
        self.__vbox.set_spacing(10)
        self.__vbox.show()
        self.add_with_viewport(self.__vbox)
        self.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.__contextMenu = self.__createContextMenu()
        self.__image = None
        self.__tooltips = gtk.Tooltips()
        self.__imageWidgetList = []
        self.__imageWidgetToImageVersion = {}
        self.__selectedImageWidgets = set()
        self.__recentlySelectedImageWidget = None
        self.connect("focus-in-event", self.__focusInEventHandler)
        self.connect("focus-out-event", self.__focusOutEventHandler)

    def clear(self):
        for widget in self.__vbox.get_children():
            self.__vbox.remove(widget)

    def loadImage(self, image):
        self.__image = image
        self.__tooltips.enable()
        for iv in image.getImageVersions():
            vbox = gtk.VBox()
            vbox.set_border_width(3)
            self.__vbox.pack_start(vbox, expand=False, fill=False)
            thumbnail = gtk.Image()
            try:
                thumbnailLocation = env.imageCache.get(iv, 128, 128)[0]
                thumbnail.set_from_file(thumbnailLocation.encode(env.codeset))
            except OSError:
                thumbnail.set_from_pixbuf(env.unknownImageIconPixbuf)
            alignment = gtk.Alignment(0.5, 0.5, 0.5, 0.5)
            alignment.add(thumbnail)
            alignment.set_padding(5, 5, 5, 5)
            eventbox = gtk.EventBox()
            eventbox.add(alignment)
            eventbox.connect(
                "button-press-event", self.__mouseButtonPressed)
            eventbox.connect_after(
                "expose-event", self.__imageWidgetExposed)
            tooltipText = "Location: " + iv.getLocation()
            if iv.getComment():
                tooltipText += "\nComment: " + iv.getComment()
            self.__tooltips.set_tip(eventbox, tooltipText)
            vbox.add(eventbox)
            if iv.isPrimary():
                vbox.add(gtk.Label("Primary"))
            vbox.add(gtk.Label(_imageVersionTypeToStringMap[iv.getType()]))
            self.__imageWidgetList.append(eventbox)
            self.__imageWidgetToImageVersion[eventbox] = iv
        self.__vbox.show_all()

    def __createContextMenu(self):
        menu = gtk.Menu()
        menugroup = MenuGroup()
        menugroup.addMenuItem(
            "View",
            self.__view)
        menugroup.addMenuItem(
            "Copy image location(s)",
            self.__copyImageLocation)
        menugroup.addStockImageMenuItem(
            "Open image in external program...",
            gtk.STOCK_OPEN,
            self.__open)
        menugroup.addMenuItem(
            "Duplicate as new version",
            self.__duplicate)
        menugroup.addMenuItem(
            "Split to independent image",
            self.__split)
        menugroup.addImageMenuItem(
            "Rotate left",
            os.path.join(env.iconDir, "rotateleft.png"),
            self.__rotateLeft)
        menugroup.addImageMenuItem(
            "Rotate right",
            os.path.join(env.iconDir, "rotateright.png"),
            self.__rotateRight)
        menugroup.addStockImageMenuItem(
            "Destroy...",
            gtk.STOCK_DELETE,
            self.__destroy)
        menugroup.addStockImageMenuItem(
            "Edit properties...",
            gtk.STOCK_PROPERTIES,
            self.__editProperties)
        for item in menugroup:
            menu.add(item)
        return menu

    def __mouseButtonPressed(self, widget, event):
        def selectWidget(widget):
            widget.set_state(gtk.STATE_SELECTED)
            self.__selectedImageWidgets.add(widget)
        def unselectWidget(widget):
            widget.set_state(gtk.STATE_NORMAL)
            self.__selectedImageWidgets.remove(widget)
        def selectOnlyThis():
            for x in list(self.__selectedImageWidgets):
                unselectWidget(x)
            selectWidget(widget)
        def selectThisToo():
            selectWidget(widget)
        def flipThis():
            if widget in self.__selectedImageWidgets:
                unselectWidget(widget)
            else:
                selectWidget(widget)
        def extendSelection():
            otherIndex = self.__imageWidgetList.index(
                self.__recentlySelectedImageWidget)
            thisIndex = self.__imageWidgetList.index(widget)
            for x in xrange(
                min(otherIndex, thisIndex), max(otherIndex, thisIndex) + 1):
                selectWidget(self.__imageWidgetList[x])

        self.grab_focus()
        if event.button == 1:
            if event.state & gtk.gdk.CONTROL_MASK:
                flipThis()
            elif event.state & gtk.gdk.SHIFT_MASK:
                extendSelection()
            else:
                selectOnlyThis()
        elif event.button == 3:
            if widget in self.__selectedImageWidgets:
                selectThisToo()
            else:
                selectOnlyThis()
            self.__contextMenu.popup(
                None, None, None, event.button, event.time)
        if self.__recentlySelectedImageWidget:
            self.__recentlySelectedImageWidget.queue_draw()
        self.__recentlySelectedImageWidget = widget

    def __imageWidgetExposed(self, widget, event):
        if widget == self.__recentlySelectedImageWidget:
            state = gtk.STATE_SELECTED
            allocation = widget.get_allocation()
            widget.style.paint_focus(
                widget.window, state, None, widget, "",
                2, 2, allocation.width - 4, allocation.height - 4)
        else:
            state = gtk.STATE_NORMAL

    def __view(self, *args):
        print "Not yet implemented."

    def __copyImageLocation(self, widget, param):
        clipboard = gtk.clipboard_get(gtk.gdk.SELECTION_CLIPBOARD)
        primary = gtk.clipboard_get(gtk.gdk.SELECTION_PRIMARY)
        location = "\n".join(
            [self.__imageWidgetToImageVersion[x].getLocation()
             for x in self.__selectedImageWidgets])
        clipboard.set_text(location)
        primary.set_text(location)

    def __open(self, *args):
        print "Not yet implemented."

    def __duplicate(self, *args):
        print "Not yet implemented."

    def __split(self, *args):
        print "Not yet implemented."

    def __rotateLeft(self, *args):
        print "Not yet implemented."

    def __rotateRight(self, *args):
        print "Not yet implemented."

    def __destroy(self, *args):
        print "Not yet implemented."

    def __editProperties(self, *args):
        dialog = ImageVersionsDialog()
        dialog.runViewImageVersions(self.__image)

    def __focusInEventHandler(self, widget, event):
        for x in self.__selectedImageWidgets:
            x.set_state(gtk.STATE_SELECTED)

    def __focusOutEventHandler(self, widget, event):
        for x in self.__selectedImageWidgets:
            x.set_state(gtk.STATE_ACTIVE)
