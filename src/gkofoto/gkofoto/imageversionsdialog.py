import gtk
import os
import re
from environment import env
from kofoto.structclass import makeStructClass
from kofoto.shelf import CategoryPresentError, ImageVersionType
from sets import Set

RowDataStruct = makeStructClass(
    "imageVersion",
    "commentTextBuffer",
    "primaryButton",
    "importantButton",
    "originalButton",
    "otherButton")

class ImageVersionsDialog:
    tableWidth = 3

    def __init__(self):
        self._versionDataList = []
        self._widgets = gtk.glade.XML(
            env.gladeFile, "imageVersionsDialog")
        self._dialog = self._widgets.get_widget("imageVersionsDialog")
        self._cancelButton = self._widgets.get_widget("cancelButton")
        self._okButton = self._widgets.get_widget("okButton")

        self._cancelButton.connect("clicked", self._onCancel)
        self._okButton.connect("clicked", self._onOk)

        scrolledWindow = self._widgets.get_widget("scrolledWindow")
        self._table = gtk.Table(1, ImageVersionsDialog.tableWidth)
        self._table.set_border_width(5)
        self._table.set_row_spacings(5)
        self._table.set_col_spacings(10)
        scrolledWindow.add_with_viewport(self._table)
        self.__primaryRadioButtonGroup = None

    def runViewImageVersions(self, image):
        self._isMerge = False
        self._run([image])

    def runMergeImages(self, images):
        assert len(images) > 1
        self._isMerge = True
        self._mergeImages = images
        self._run(images)

    def _run(self, images):
        for image in images:
            for imageVersion in image.getImageVersions():
                self._addRow(imageVersion)
        self._dialog.show_all()
        x, y = self._dialog.get_position()
        width, height = self._dialog.get_size()
        hackyConstant = 89 # TODO: How to calculate this properly?
        newheight = min(800, self._table.size_request()[1] + hackyConstant)
        self._dialog.move(x, max(0, y - ((newheight - height) / 2)))
        self._dialog.resize(450, newheight)

    def _onCancel(self, *unused):
        self._dialog.destroy()

    def _onOk(self, *unused):
        t = self._table
        for data in self._versionDataList:
            tb = data.commentTextBuffer
            comment = tb.get_text(tb.get_start_iter(), tb.get_end_iter())
            data.imageVersion.setComment(comment.decode("utf-8"))
            if data.primaryButton.get_active():
                data.imageVersion.makePrimary()
            if data.importantButton.get_active():
                data.imageVersion.setType(ImageVersionType.Important)
            elif data.originalButton.get_active():
                data.imageVersion.setType(ImageVersionType.Original)
            elif data.otherButton.get_active():
                data.imageVersion.setType(ImageVersionType.Other)
            else:
                assert False

        proceed = True
        if self._isMerge:
            #
            # The mother image below is the image of the primary
            # version, i.e. the image that will adopt all image
            # versions.
            #

            motherImage = None
            for data in self._versionDataList:
                if data.primaryButton.get_active():
                    motherImage = data.imageVersion.getImage()
                    break
            assert motherImage

            for image in self._mergeImages:
                if image != motherImage:
                    for key, value in image.getAttributeMap().items():
                        motherImage.setAttribute(key, value, overwrite=False)

            for data in self._versionDataList:
                data.imageVersion.setImage(motherImage)

            descriptionTexts = []
            for image in self._mergeImages:
                description = image.getAttribute(u"description")
                if description:
                    descriptionTexts.append(description)
                if image == motherImage:
                    continue
                for category in image.getCategories():
                    try:
                        motherImage.addCategory(category)
                    except CategoryPresentError:
                        pass
                for album in image.getParents():
                    children = list(album.getChildren())
                    if motherImage in children:
                        # Both motherImage and image are present in
                        # children, so just remove image to avoid
                        # duplicates in album.
                        pass
                    else:
                        # Replace image with motherImage.
                        for i, child in enumerate(children):
                            if child == image:
                                children[i] = motherImage
                        album.setChildren(children)
                env.shelf.deleteImage(image.getId())
            description = "\n\n".join(descriptionTexts)
            if len(descriptionTexts) > 1:
                widgets = gtk.glade.XML(
                    env.gladeFile, "editMergedDescriptionDialog")
                dialog = widgets.get_widget("editMergedDescriptionDialog")
                textBuffer = widgets.get_widget("descriptionText").get_buffer()
                textBuffer.set_text(description)
                dialog.run()
                dialog.destroy()
                motherImage.setAttribute(
                    u"description",
                    textBuffer.get_text(
                        textBuffer.get_start_iter(),
                        textBuffer.get_end_iter()).decode("utf-8"))
        env.mainwindow.reloadObjectList()
        self._dialog.destroy()

    def _addRow(self, imageVersion):
        table = self._table
        data = RowDataStruct()
        self._versionDataList.append(data)
        data.imageVersion = imageVersion
        number = len(self._versionDataList) - 1
        table.resize(number + 1, ImageVersionsDialog.tableWidth)

        #
        # Column one.
        #
        image = gtk.Image()
        try:
            thumbnailLocation, w, h = env.imageCache.get(
                imageVersion.getLocation(), 128, 128)
            image.set_from_file(thumbnailLocation)
        except OSError:
            image.set_from_pixbuf(env.unknownImageIconPixbuf)
        table.attach(
            image, 0, 1, number, number + 1, gtk.SHRINK, gtk.SHRINK)

        #
        # Column two.
        #
        buttonBox = gtk.VBox()
        table.attach(
            buttonBox, 1, 2, number, number + 1, gtk.SHRINK, gtk.FILL)
        primaryButton = gtk.RadioButton(self.__primaryRadioButtonGroup, "Primary")
        buttonBox.pack_start(primaryButton, False, False)
        data.primaryButton = primaryButton
        if not self.__primaryRadioButtonGroup:
            self.__primaryRadioButtonGroup = primaryButton
        primaryButton.set_active(imageVersion.isPrimary())

        typeFrame = gtk.Frame("Type")
        buttonBox.pack_start(typeFrame, False, False)

        typeButtonBox = gtk.VBox()
        typeFrame.add(typeButtonBox)

        importantButton = gtk.RadioButton(None, "Important")
        typeButtonBox.add(importantButton)
        data.importantButton = importantButton
        importantButton.set_active(
            imageVersion.getType() == ImageVersionType.Important)

        originalButton = gtk.RadioButton(importantButton, "Original")
        typeButtonBox.add(originalButton)
        data.originalButton = originalButton
        originalButton.set_active(
            imageVersion.getType() == ImageVersionType.Original)

        otherButton = gtk.RadioButton(importantButton, "Other")
        typeButtonBox.add(otherButton)
        data.otherButton = otherButton
        otherButton.set_active(
            imageVersion.getType() == ImageVersionType.Other)

        #
        # Column three.
        #
        scrolledWindow = gtk.ScrolledWindow()
        scrolledWindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        scrolledWindow.set_shadow_type(gtk.SHADOW_IN)
        textView = gtk.TextView()
        scrolledWindow.add(textView)
        data.commentTextBuffer = textView.get_buffer()
        textView.set_wrap_mode(gtk.WRAP_WORD)
        textView.get_buffer().set_text(imageVersion.getComment())
        table.attach(
            scrolledWindow, 2, 3, number, number + 1,
            gtk.FILL|gtk.EXPAND, gtk.FILL)
