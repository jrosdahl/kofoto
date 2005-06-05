import gtk
from environment import env
from kofoto.shelf import ImageVersionType
from gkofoto.menuhandler import MenuGroup
from imageversionsdialog import ImageVersionsDialog

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
            eventbox = gtk.EventBox()
            eventbox.add(thumbnail)
            eventbox.connect(
                "button_press_event", self.__mouseButtonPressed, iv)
            tooltipText = "Location: " + iv.getLocation()
            if iv.getComment():
                tooltipText += "\nComment: " + iv.getComment()
            self.__tooltips.set_tip(eventbox, tooltipText)
            vbox.add(eventbox)
            if iv.isPrimary():
                vbox.add(gtk.Label("Primary"))
            vbox.add(gtk.Label(_imageVersionTypeToStringMap[iv.getType()]))
        self.__vbox.show_all()

    def __createContextMenu(self):
        menu = gtk.Menu()
        menugroup = MenuGroup()
        menugroup.addMenuItem(
            "View",
            self.__view)
        menugroup.addMenuItem(
            "Copy image location",
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

    def __mouseButtonPressed(self, widget, event, param):
        widget.grab_focus()
        if event.button == 3:
            self.__contextMenu.popup(
                None, None, None, event.button, event.time)
            self.__selectedImageVersion = param
            return True
        else:
            return False

    def __view(self, *args):
        print "Not yet implemented."

    def __copyImageLocation(self, widget, param):
        clipboard = gtk.clipboard_get(gtk.gdk.SELECTION_CLIPBOARD)
        primary = gtk.clipboard_get(gtk.gdk.SELECTION_PRIMARY)
        location = self.__selectedImageVersion.getLocation()
        clipboard.set_text(location)
        primary.set_text(location)

    def __open(self, *args):
        print "Not yet implemented."

    def __duplicate(self, *args):
        print "Not yet implemented."

    def __split(self, *args):
        print "Not yet implemented."

    def __destroy(self, *args):
        print "Not yet implemented."

    def __editProperties(self, *args):
        dialog = ImageVersionsDialog()
        dialog.runViewImageVersions(self.__image)
