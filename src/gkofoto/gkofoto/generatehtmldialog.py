import gtk
import os
import re
from sets import Set
from environment import env
import kofoto.generate

class GenerateHTMLDialog:
    def __init__(self, album):
        self.album = album
        self.widgets = gtk.glade.XML(
            env.gladeFile, "generateHtmlDialog")
        self.dialog = self.widgets.get_widget("generateHtmlDialog")
        self.browseButton = self.widgets.get_widget("browseButton")
        self.cancelButton = self.widgets.get_widget("cancelButton")
        self.directoryTextEntry = self.widgets.get_widget("directoryTextEntry")
        self.generateButton = self.widgets.get_widget("generateButton")

        self.browseButton.connect("clicked", self._onBrowse)
        self.cancelButton.connect("clicked", self._onCancel)
        self.generateButton.connect("clicked", self._onGenerate)

        self.directoryTextEntry.connect(
            "changed", self._onDirectoryTextEntryModified)

        self.generateButton.set_sensitive(False)

    def run(self):
        self.dialog.show()

    def _onDirectoryTextEntryModified(self, *unused):
        self.generateButton.set_sensitive(
            os.path.isdir(self.directoryTextEntry.get_text()))

    def _onBrowse(self, *unused):
        directorySelectedInDirList = False
        dirDialog = gtk.FileSelection(title="Choose directory")
        dirDialog.file_list.set_sensitive(False)
        dirDialog.fileop_del_file.set_sensitive(False)
        dirDialog.fileop_ren_file.set_sensitive(False)
        if dirDialog.run() == gtk.RESPONSE_OK:
            model, iterator = dirDialog.dir_list.get_selection().get_selected()
            directory = dirDialog.get_filename()
            if iterator:
                directory = os.path.join(
                    directory, model.get_value(iterator, 0))
            self.directoryTextEntry.set_text(directory)
        dirDialog.destroy()

    def _onCancel(self, *unused):
        self.dialog.destroy()

    def _onGenerate(self, *unused):
        for widget in [self.directoryTextEntry, self.browseButton,
                       self.cancelButton, self.generateButton]:
            widget.set_sensitive(False)
        self._generate(self.directoryTextEntry.get_text())
        self.dialog.destroy()

    def _generate(self, directoryName):
        # TODO: Rewrite this gross hack.

        def outputParser(string):
            m = re.match(
                r"Creating album (\S+) \((\d+) of (\d+)\)",
                string,
                re.UNICODE)
            if m:
                progressBar.set_text(m.group(1).decode("latin1"))
                progressBar.set_fraction(
                    (int(m.group(2)) - 1) / float(m.group(3)))
                while gtk.events_pending():
                    gtk.main_iteration()

        progressBar = self.widgets.get_widget("progressBar")

        env.out = outputParser
        env.verbose = True
        env.thumbnailsizelimit = env.config.getcoordlist(
            "album generation", "thumbnail_size_limit")[0]
        env.defaultsizelimit = env.config.getcoordlist(
            "album generation", "default_image_size_limit")[0]

        imgsizesval = env.config.getcoordlist(
            "album generation", "other_image_size_limits")
        imgsizesset = Set(imgsizesval) # Get rid of duplicates.
        defaultlimit = env.config.getcoordlist(
            "album generation", "default_image_size_limit")[0]
        imgsizesset.add(defaultlimit)
        imgsizes = list(imgsizesset)
        imgsizes.sort(lambda x, y: cmp(x[0] * x[1], y[0] * y[1]))
        env.imagesizelimits = imgsizes

        generator = kofoto.generate.Generator(u"woolly", env)
        generator.generate(self.album, None, directoryName, "latin1")
        progressBar.set_fraction(1)
        while gtk.events_pending():
            gtk.main_iteration()