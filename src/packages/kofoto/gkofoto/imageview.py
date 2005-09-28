# pylint: disable-msg=F0203, E0201

import gtk
import gtk.gdk
import math
import gc
from kofoto.gkofoto.environment import env
from kofoto.common import calculateDownscaledDimensions

class ImageView(gtk.ScrolledWindow):
    # TODO: Read from configuration file?
    _INTERPOLATION_TYPE = gtk.gdk.INTERP_BILINEAR
    # gtk.gdk.INTERP_HYPER is slower but gives better quality.
    _MAX_IMAGE_SIZE = 2000
    _MIN_IMAGE_SIZE = 10 # Work-around for bug in GTK. (pixbuf.scale_iter(1, 1) crashes.)
    _MIN_ZOOM = -100
    _MAX_ZOOM = 1
    _ZOOMFACTOR = 1.2

    def __init__(self):
        self._image = gtk.Image()
        gtk.ScrolledWindow.__init__(self)
        self._newImageLoaded = False
        self.__loadedFileName = None
        self.__pixBuf = None
        self.__currentZoom = None
        self.__wantedZoom = None
        self.__fitToWindowMode = True
        self.__previousWidgetWidth = 0
        self.__previousWidgetHeight = 0

        # Don't know why the EventBox is needed, but if it is removed,
        # a size_allocate signal will trigger self.resizeEventHandler,
        # which will resize the image, which will trigger
        # size_allocate again, and so on.
        eventBox = gtk.EventBox()
        eventBox.add(self._image)

        self.add_with_viewport(eventBox)
        self.add_events(gtk.gdk.ALL_EVENTS_MASK)
        self.connect_after("size-allocate", self.resizeEventHandler_cb)
        self.connect("scroll-event", self.scrollEventHandler_cb)
        self.connect("focus-in-event", self.focusInEventHandler_cb)
        self.connect("focus-out-event", self.focusOutEventHandler_cb)

    def focusInEventHandler_cb(self, widget, event):
        pass

    def focusOutEventHandler_cb(self, widget, event):
        pass

    def loadFile(self, fileName, reloadFile=True):
        if (not reloadFile) and self.__loadedFileName == fileName:
            return
        self.clear()
        env.debug("ImageView is loading image from file: " + fileName)
        self.__pixBuf = env.mainwindow.getImagePreloader().getPixbuf(fileName)
        if self.__pixBuf:
            self.__loadedFileName = fileName
        else:
            dialog = gtk.MessageDialog(
                type=gtk.MESSAGE_ERROR,
                buttons=gtk.BUTTONS_OK,
                message_format="Could not load image: %s" % fileName)
            dialog.run()
            dialog.destroy()
            self.__pixBuf = env.unknownImageIconPixbuf
            self.__loadedFileName = None
        self._newImageLoaded = True
        self._image.show()
        self.fitToWindow_cb()

    def clear(self):
        self._image.hide()
        self._image.set_from_file(None)
        self.__pixBuf = None
        self.__loadedFileName = None
        gc.collect()
        env.debug("ImageView is cleared.")

    def reload(self):
        self.loadFile(self.__loadedFileName)

    def renderImage(self):
        # TODO: Scaling should be asyncronous to avoid freezing the gtk-main loop
        if self.__pixBuf == None:
            # No image loaded
            self._image.hide()
            return
        if self.__currentZoom == self.__wantedZoom and not self._newImageLoaded:
            return
        if self.__wantedZoom == 0:
            pixBufResized = self.__pixBuf
        else:
            if self.__fitToWindowMode:
                maxWidth, maxHeight = tuple(self.get_allocation())[2:4]
                wantedWidth, wantedHeight = calculateDownscaledDimensions(
                    self.__pixBuf.get_width(),
                    self.__pixBuf.get_height(),
                    maxWidth,
                    maxHeight)
            else:
                zoomMultiplicator = pow(self._ZOOMFACTOR, self.__wantedZoom)
                wantedWidth = int(self.__pixBuf.get_width() * zoomMultiplicator)
                wantedHeight = int(self.__pixBuf.get_height() * zoomMultiplicator)
            if min(wantedWidth, wantedHeight) < self._MIN_IMAGE_SIZE:
                # Too small image size
                return
            if max(wantedWidth, wantedHeight) > self._MAX_IMAGE_SIZE:
                # Too large image size
                return
            pixBufResized = env.mainwindow.getImagePreloader().getPixbuf(
                self.__loadedFileName,
                wantedWidth,
                wantedHeight)
            if not pixBufResized:
                pixBufResized = env.unknownImageIconPixbuf
        pixMap, mask = pixBufResized.render_pixmap_and_mask()
        self._image.set_from_pixmap(pixMap, mask)
        self._newImageLoaded = False
        self.__currentZoom = self.__wantedZoom
        gc.collect()

    def resizeEventHandler_cb(self, widget, gdkEvent):
        if self.__fitToWindowMode:
            _, _, width, height = self.get_allocation()
            if height != self.__previousWidgetHeight or width != self.__previousWidgetWidth:
                self.fitToWindow_cb()
        return False

    def fitToWindow_cb(self, *unused):
        self.__fitToWindowMode = True
        self.set_policy(gtk.POLICY_NEVER, gtk.POLICY_NEVER)
        _, _, widgetWidth, widgetHeight = self.get_allocation()
        if self.__pixBuf != None:
            self.__previousWidgetWidth = widgetWidth
            self.__previousWidgetHeight = widgetHeight
            a = min(float(widgetWidth) / self.__pixBuf.get_width(),
                    float(widgetHeight) / self.__pixBuf.get_height())
            self.__wantedZoom = self._log(self._ZOOMFACTOR, a)
            self.__wantedZoom = min(self.__wantedZoom, 0)
            self.__wantedZoom = max(self.__wantedZoom, self._MIN_ZOOM)
            self.renderImage()

    def getAvailableSpace(self):
        return tuple(self.get_allocation())[2:4]

    def _log(self, base, value):
        return math.log(value) / math.log(base)

    def zoomIn_cb(self, *unused):
        self.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.__fitToWindowMode = False
        if self.__wantedZoom <= self._MAX_ZOOM:
            self.__wantedZoom = math.floor(self.__wantedZoom + 1)
            self.renderImage()

    def zoomOut_cb(self, *unused):
        self.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.__fitToWindowMode = False
        if self.__wantedZoom >= self._MIN_ZOOM:
            self.__wantedZoom = math.ceil(self.__wantedZoom - 1)
            self.renderImage()

    def zoom100_cb(self, *unused):
        self.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.__fitToWindowMode = False
        self.__wantedZoom = 0
        self.renderImage()

    def scrollEventHandler_cb(self, widget, gdkEvent):
        if gdkEvent.type == gtk.gdk.SCROLL:
            if gdkEvent.direction == gtk.gdk.SCROLL_UP:
                self.zoomOut_cb()
            elif gdkEvent.direction == gtk.gdk.SCROLL_DOWN:
                self.zoomIn_cb()
            return True
        else:
            return False
