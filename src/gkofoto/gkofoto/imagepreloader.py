import gobject
import gtk
from kofoto.timer import Timer
from kofoto.common import calculateDownscaledDimensions

class _PreloadState:
    def __init__(self, filename, fileSystemCodeset):
        self.fullsizePixbuf = None
        self.pixbufLoader = gtk.gdk.PixbufLoader()
        self.loadFinished = False # Whether loading of fullsizePixbuf is ready.
        self.scaledPixbuf = None
        try:
            self.fp = open(filename.encode(fileSystemCodeset), "rb")
        except OSError:
            self.loadFinished = True

class ImagePreloader(object):
    def __init__(self, fileSystemCodeset, debugPrintFunction=None):
        self._fileSystemCodeset = fileSystemCodeset
        if debugPrintFunction:
            self._debugPrint = debugPrintFunction
        else:
            self._debugPrint = lambda x: None
        self.__delayTimerTag = None
        self.__idleTimerTag = None
        # filename --> _PreloadState
        self.__preloadStates = {}

    def preloadImages(self, filenames, scaledMaxWidth, scaledMaxHeight):
        """Preload images.

        The images are loaded and stored both in a fullsize version
        and a scaled-down version.

        Note that this method discards previously preloaded images,
        except those present in the filenames argument.

        filenames -- Iterable of filenames of images to preload.
        scaledMaxWidth -- Wanted maximum width of the scaled image.
        scaledMaxHeight -- Wanted maximum height of the scaled image.
        """
        if self.__delayTimerTag != None:
            gobject.source_remove(self.__delayTimerTag)
        if self.__idleTimerTag != None:
            gobject.source_remove(self.__idleTimerTag)

        # Delay preloading somewhat to make display of the current
        # image faster. Not sure whether it helps, though...
        self.__delayTimerTag = gobject.timeout_add(
            500,
            self._beginPreloading,
            filenames,
            scaledMaxWidth,
            scaledMaxHeight)

    def clearCache(self):
        for ps in self.__preloadStates.values():
            if ps.pixbufLoader:
                ps.pixbufLoader.close()
        self.__preloadStates = {}

    def getPixbuf(self, filename, maxWidth=None, maxHeight=None):
        """Get a pixbuf.

        If maxWidth and maxHeight are None, the fullsize version is
        returned, otherwise a scaled version no larger than maxWidth
        and maxHeight is returned.

        The pixbuf may be None if the image was unloadable.
        """
        pixbuf = None

        if not self.__preloadStates.has_key(filename):
            self.__preloadStates[filename] = _PreloadState(
                filename, self._fileSystemCodeset)
        ps = self.__preloadStates[filename]
        if not ps.loadFinished:
            try:
                ps.pixbufLoader.write(ps.fp.read())
                ps.pixbufLoader.close()
                ps.fullsizePixbuf = ps.pixbufLoader.get_pixbuf()
            except (gobject.GError, OSError):
                ps.pixbufLoader.close()
                ps.fullsizePixbuf = None
            ps.pixbufLoader = None
            ps.loadFinished = True
        if (ps.fullsizePixbuf == None or
            (maxWidth == None and maxHeight == None) or
            (ps.fullsizePixbuf.get_width() <= maxWidth and
             ps.fullsizePixbuf.get_height() <= maxHeight)):
            # Requested fullsize pixbuf or scaled pixbuf larger than
            # fullsize.
            return ps.fullsizePixbuf
        else:
            # Requested scaled pixbuf.
            ps.scaledPixbuf = self._maybeScalePixbuf(
                ps.fullsizePixbuf,
                ps.scaledPixbuf,
                maxWidth,
                maxHeight,
                filename)
            return ps.scaledPixbuf

    def _beginPreloading(self, filenames, scaledMaxWidth, scaledMaxHeight):
        self.__idleTimerTag = gobject.idle_add(
            self._preloadImagesWorker(
                filenames, scaledMaxWidth, scaledMaxHeight).next)
        return False

    def _preloadImagesWorker(self, filenames, scaledMaxWidth, scaledMaxHeight):
        filenames = list(filenames)
        self._debugPrint("Preloading images %s" % str(filenames))

        # Discard old preloaded images.
        for filename in self.__preloadStates.keys():
            if not filename in filenames:
                pixbufLoader = self.__preloadStates[filename].pixbufLoader
                if pixbufLoader:
                    pixbufLoader.close()
                del self.__preloadStates[filename]

        # Preload the new images.
        for filename in filenames:
            if not self.__preloadStates.has_key(filename):
                self.__preloadStates[filename] = _PreloadState(
                    filename, self._fileSystemCodeset)
            ps = self.__preloadStates[filename]
            try:
                self._debugPrint("Preloading %s" % filename)
                timer = Timer()
                while not ps.loadFinished: # could be set by getPixbuf
                    data = ps.fp.read(32768)
                    if not data:
                        ps.pixbufLoader.close()
                        ps.fullsizePixbuf = ps.pixbufLoader.get_pixbuf()
                        break
                    ps.pixbufLoader.write(data)
                    yield True
                self._debugPrint("Preload of %s took %.2f seconds" % (
                    filename, timer.get()))
            except (gobject.GError, OSError):
                ps.pixbufLoader.close()
            ps.pixbufLoader = None
            ps.loadFinished = True

            ps.scaledPixbuf = self._maybeScalePixbuf(
                ps.fullsizePixbuf,
                ps.scaledPixbuf,
                scaledMaxWidth,
                scaledMaxHeight,
                filename)
            yield True

        # We're finished.
        self.__idleTimerTag = None
        yield False

    def _maybeScalePixbuf(self, fullsizePixbuf, scaledPixbuf,
                          maxWidth, maxHeight, filename):
        if not fullsizePixbuf:
            return None
        elif (fullsizePixbuf.get_width() <= maxWidth and
              fullsizePixbuf.get_height() <= maxHeight):
            return fullsizePixbuf
        elif not (scaledPixbuf and
                  scaledPixbuf.get_width() <= maxWidth and
                  scaledPixbuf.get_height() <= maxHeight and
                  (scaledPixbuf.get_width() == maxWidth or
                   scaledPixbuf.get_height() == maxHeight)):
            scaledWidth, scaledHeight = calculateDownscaledDimensions(
                fullsizePixbuf.get_width(),
                fullsizePixbuf.get_height(),
                maxWidth,
                maxHeight)
            self._debugPrint("Scaling %s to %dx%d" % (
                filename, scaledWidth, scaledHeight))
            if scaledPixbuf:
                self._debugPrint("old size: %dx%d" % (
                    scaledPixbuf.get_width(),
                    scaledPixbuf.get_height()))
                self._debugPrint("new size: %dx%d" % (
                    scaledWidth,
                    scaledHeight))
            timer = Timer()
            scaledPixbuf = fullsizePixbuf.scale_simple(
                scaledWidth,
                scaledHeight,
                gtk.gdk.INTERP_BILINEAR) # TODO: Make configurable.
            self._debugPrint("Scaling of %s to %dx%d took %.2f seconds" % (
                filename, scaledWidth, scaledHeight, timer.get()))
            return scaledPixbuf
        else: # Appropriately sized scaled pixbuf.
            return scaledPixbuf
