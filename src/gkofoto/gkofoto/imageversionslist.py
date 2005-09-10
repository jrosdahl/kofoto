import os
import gtk

from environment import env
from kofoto.shelf import ImageVersionType
from gkofoto.menuhandler import MenuGroup
from imageversionsdialog import ImageVersionsDialog
from sets import Set as set
from kofoto.alternative import Alternative
from duplicateandopenimagedialog import DuplicateAndOpenImageDialog

_imageVersionTypeToStringMap = {
    ImageVersionType.Important: "Important",
    ImageVersionType.Original: "Original",
    ImageVersionType.Other: "Other",
}

_rotationDirection = Alternative("Left", "Right")

class ImageVersionsList(gtk.ScrolledWindow):
    def __init__(self, singleObjectView, imageView):
        gtk.ScrolledWindow.__init__(self)
        self.__singleObjectView = singleObjectView
        self.__imageView = imageView
        self.__vbox = gtk.VBox()
        self.__vbox.set_border_width(5)
        self.__vbox.set_spacing(10)
        self.__vbox.show()
        self.add_with_viewport(self.__vbox)
        self.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.__image = None
        self.__tooltips = gtk.Tooltips()
        self.__recentlySelectedImageWidget = None
        self.connect("focus-in-event", self.__focusInEventHandler)
        self.connect("focus-out-event", self.__focusOutEventHandler)
        self.__contextMenu = self.__createContextMenu()
        self.clear()

        callbacks = [
            ("menubarViewImageVersion", self.__view),
            ("menubarCopyImageVersionLocations", self.__copyImageLocation),
            ("menubarOpenImageVersions", self.__open),
            ("menubarDuplicateAndOpenImageVersion", self.__duplicateAndOpen),
            ("menubarRotateImageVersionLeft", self.__rotateLeft),
            ("menubarRotateImageVersionRight", self.__rotateRight),
            ("menubarSplitToIndependentImages", self.__split),
            ("menubarDestroyImageVersion", self.__destroy),
            ("menubarEditImageVersionProperties", self.__editProperties),
            ]
        for widgetName, callback in callbacks:
            env.widgets[widgetName].connect("activate", callback)

    def clear(self):
        for widget in self.__vbox.get_children():
            self.__vbox.remove(widget)
        self.__imageWidgetList = []
        self.__imageWidgetToImageVersion = {}
        self.__selectedImageWidgets = set()
        self.__updateMenus()

    def loadImage(self, image):
        self.clear()
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

    def reload(self):
        self.loadImage(self.__image)

    def __createContextMenu(self):
        menu = gtk.Menu()
        menugroup = MenuGroup()
        menugroup.addMenuItem(
            "View",
            self.__view)
        menugroup.addMenuItem(
            "Copy image version location(s)",
            self.__copyImageLocation)
        menugroup.addStockImageMenuItem(
            "Open image version(s) in external program...",
            gtk.STOCK_OPEN,
            self.__open)
        menugroup.addStockImageMenuItem(
            "Duplicate and open image version(s) in external program...",
            gtk.STOCK_OPEN,
            self.__duplicateAndOpen)
        menugroup.addImageMenuItem(
            "Rotate left",
            os.path.join(env.iconDir, "rotateleft.png"),
            self.__rotateLeft)
        menugroup.addImageMenuItem(
            "Rotate right",
            os.path.join(env.iconDir, "rotateright.png"),
            self.__rotateRight)
        menugroup.addSeparator()
        menugroup.addMenuItem(
            "Split to independent image(s)",
            self.__split)
        menugroup.addSeparator()
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
        self.__menuGroup = menugroup
        return menu

    def __updateMenus(self):
        zeroSelected = len(self.__selectedImageWidgets) == 0
        oneSelected = len(self.__selectedImageWidgets) == 1
        allSelected = (
            len(self.__selectedImageWidgets) == len(self.__imageWidgetList))

        env.widgets["menubarViewImageVersion"].set_sensitive(
            oneSelected)
        env.widgets["menubarCopyImageVersionLocations"].set_sensitive(
            not zeroSelected)
        env.widgets["menubarOpenImageVersions"].set_sensitive(
            not zeroSelected)
        env.widgets["menubarDuplicateAndOpenImageVersion"].set_sensitive(
            oneSelected)
        env.widgets["menubarRotateImageVersionLeft"].set_sensitive(
            not zeroSelected)
        env.widgets["menubarRotateImageVersionRight"].set_sensitive(
            not zeroSelected)
        env.widgets["menubarSplitToIndependentImages"].set_sensitive(
            not zeroSelected and not allSelected)
        env.widgets["menubarDestroyImageVersion"].set_sensitive(
            not zeroSelected)
        env.widgets["menubarEditImageVersionProperties"].set_sensitive(
            not zeroSelected)

        if zeroSelected:
            self.__menuGroup.disable()
        else:
            self.__menuGroup.enable()
            if not oneSelected:
                self.__menuGroup["View"].set_sensitive(False)
                self.__menuGroup[
                    ("Duplicate and open image version(s) in external"
                     " program...")
                    ].set_sensitive(False)
            if allSelected:
                self.__menuGroup["Split to independent image(s)"].set_sensitive(False)

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
            if event.type == gtk.gdk.BUTTON_PRESS:
                if event.state & gtk.gdk.CONTROL_MASK:
                    flipThis()
                elif event.state & gtk.gdk.SHIFT_MASK:
                    extendSelection()
                else:
                    selectOnlyThis()
            elif event.type == gtk.gdk._2BUTTON_PRESS:
                if (event.state & (
                        gtk.gdk.CONTROL_MASK | gtk.gdk.SHIFT_MASK) == 0):
                    self.__view()
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
        self.__updateMenus()

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
        assert len(self.__selectedImageWidgets) == 1
        widget = list(self.__selectedImageWidgets)[0]
        imageVersion = self.__imageWidgetToImageVersion[widget]
        self.__imageView.loadFile(imageVersion.getLocation())

    def __copyImageLocation(self, widget, param):
        assert len(self.__selectedImageWidgets) > 0
        clipboard = gtk.clipboard_get(gtk.gdk.SELECTION_CLIPBOARD)
        primary = gtk.clipboard_get(gtk.gdk.SELECTION_PRIMARY)
        location = "\n".join(
            [self.__imageWidgetToImageVersion[x].getLocation()
             for x in self.__selectedImageWidgets])
        clipboard.set_text(location)
        primary.set_text(location)

    def __open(self, *args):
        assert len(self.__selectedImageWidgets) > 0
        locations = [
            self.__imageWidgetToImageVersion[x].getLocation()
            for x in self.__selectedImageWidgets]
        command = env.openCommand % {"locations": " ".join(locations)}
        result = os.system(command.encode(env.codeset) + " &")
        if result != 0:
            dialog = gtk.MessageDialog(
                type=gtk.MESSAGE_ERROR,
                buttons=gtk.BUTTONS_OK,
                message_format="Failed to execute command: \"%s\"" % command)
            dialog.run()
            dialog.destroy()

    def __duplicateAndOpen(self, *args):
        assert len(self.__selectedImageWidgets) == 1
        imageWidget = list(self.__selectedImageWidgets)[0]
        imageVersion = self.__imageWidgetToImageVersion[imageWidget]
        dialog = DuplicateAndOpenImageDialog()
        dialog.run(imageVersion)

    def __split(self, *args):
        assert len(self.__selectedImageWidgets) > 0
        assert len(self.__selectedImageWidgets) < len(self.__imageWidgetList)
        for widget in self.__selectedImageWidgets:
            imageVersion = self.__imageWidgetToImageVersion[widget]
            image = env.shelf.createImage()
            imageVersion.setImage(image)
            for key, value in self.__image.getAttributeMap().items():
                image.setAttribute(key, value)
            for category in  self.__image.getCategories():
                image.addCategory(category)
        self.__singleObjectView.reload()

    def __rotateLeft(self, *args):
        assert len(self.__selectedImageWidgets) > 0
        self.__rotate(_rotationDirection.Left)

    def __rotateRight(self, *args):
        assert len(self.__selectedImageWidgets) > 0
        self.__rotate(_rotationDirection.Right)

    def __destroy(self, *args):
        assert len(self.__selectedImageWidgets) > 0
        widgets = gtk.glade.XML(env.gladeFile, "destroyImageVersionsDialog")
        dialog = widgets.get_widget("destroyImageVersionsDialog")
        result = dialog.run()
        if result == gtk.RESPONSE_OK:
            checkbutton = widgets.get_widget("deleteImageFilesCheckbutton")
            deleteFiles = checkbutton.get_active()
            for widget in self.__selectedImageWidgets:
                imageVersion = self.__imageWidgetToImageVersion[widget]
                if deleteFiles:
                    try:
                        os.remove(
                            imageVersion.getLocation().encode(env.codset))
                        # TODO: Delete from image cache too?
                    except OSError:
                        pass
                env.shelf.deleteImageVersion(imageVersion.getId())
            self.__singleObjectView.reload()
        dialog.destroy()

    def __editProperties(self, *args):
        assert len(self.__selectedImageWidgets) > 0
        dialog = ImageVersionsDialog(self.__singleObjectView._objectCollection)
        dialog.runViewImageVersions(self.__image)
        self.__singleObjectView.reload()

    def __focusInEventHandler(self, widget, event):
        for x in self.__selectedImageWidgets:
            x.set_state(gtk.STATE_SELECTED)

    def __focusOutEventHandler(self, widget, event):
        for x in self.__selectedImageWidgets:
            x.set_state(gtk.STATE_ACTIVE)

    def __rotate(self, rotationDirection):
        for widget in self.__selectedImageWidgets:
            imageVersion = self.__imageWidgetToImageVersion[widget]
            if rotationDirection == _rotationDirection.Left:
                rotateCommand = env.rotateLeftCommand
            elif rotationDirection == _rotationDirection.Right:
                rotateCommand = env.rotateRightCommand
            else:
                # Can't happen.
                assert True
            command = rotateCommand % {"location": imageVersion.getLocation()}
            result = os.system(command.encode(env.codeset))
            if result == 0:
                imageVersion.contentChanged()
            else:
                dialog = gtk.MessageDialog(
                    type=gtk.MESSAGE_ERROR,
                    buttons=gtk.BUTTONS_OK,
                    message_format="Failed to execute command: \"%s\"" % command)
                dialog.run()
                dialog.destroy()
        env.mainwindow.getImagePreloader().clearCache()
        self.__singleObjectView.reload()
