import gtk
import gtk.gdk
import math
import gobject
import gc
from environment import env

class ImageView(gtk.ScrolledWindow):
    # TODO: Read from configuration file?
    _INTERPOLATION_TYPE = gtk.gdk.INTERP_BILINEAR
    # gtk.gdk.INTERP_HYPER is slower but gives better quality.
    _MAX_IMAGE_SIZE = 2000
    _MIN_IMAGE_SIZE = 1
    _MIN_ZOOM = -100
    _MAX_ZOOM = 1
    _ZOOMFACTOR = 1.2

    def __init__(self):
        self._image = gtk.Image()
        gtk.ScrolledWindow.__init__(self)
        self.__loadedFileName = None
        self.__pixBuf = None
        self.__currentZoom = None
        self.__wantedZoom = None
        self.__fitToWindowMode = True
        self.__previousWidgetWidth = 0
        self.__previousWidgetHeight = 0
        eventBox = gtk.EventBox()
        eventBox.add(self._image)
        self.add_with_viewport(eventBox)
        self.add_events(gtk.gdk.ALL_EVENTS_MASK)
        self.connect_after("size_allocate", self.resizeEventHandler)
        self.connect("scroll_event", self.scrollEventHandler)

    def loadFile(self, fileName, reload=True):
        fileName = fileName.encode(env.codeset)
        if (not reload) and self.__loadedFileName == fileName:
            return
        # TODO: Loading file should be asyncronous to avoid freezing the gtk-main loop
        try:
            self.clear()
            env.debug("ImageView is loading image from file: " + fileName)
            self.__pixBuf = gtk.gdk.pixbuf_new_from_file(fileName)
            self.__loadedFileName = fileName
        except gobject.GError, e:
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
        self.fitToWindow()

    def clear(self):
        self._image.hide()
        self._image.set_from_file(None)
        self.__pixBuf = None
        self.__loadedFileName = None
        gc.collect()
        env.debug("ImageView is cleared.")

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
            zoomMultiplicator = pow(self._ZOOMFACTOR, self.__wantedZoom)
            wantedWidth = int(self.__pixBuf.get_width() * zoomMultiplicator)
            wantedHeight = int(self.__pixBuf.get_height() * zoomMultiplicator)
            if min(wantedWidth, wantedHeight) < self._MIN_IMAGE_SIZE:
                # Too small image size
                return
            if max(wantedWidth, wantedHeight) > self._MAX_IMAGE_SIZE:
                # Too large image size
                return
            pixBufResized = self.__pixBuf.scale_simple(wantedWidth,
                                                      wantedHeight,
                                                      self._INTERPOLATION_TYPE)
        pixMap, mask = pixBufResized.render_pixmap_and_mask()
        self._image.set_from_pixmap(pixMap, mask)
        self._newImageLoaded = False
        self.__currentZoom = self.__wantedZoom
        gc.collect()

    def resizeEventHandler(self, widget, gdkEvent):
        if self.__fitToWindowMode:
            x, y, width, height = self.get_allocation()
            if height != self.__previousWidgetHeight or width != self.__previousWidgetWidth:
                self.fitToWindow()
        return False

    def fitToWindow(self, *foo):
        self.__fitToWindowMode = True
        self.set_policy(gtk.POLICY_NEVER, gtk.POLICY_NEVER)
        y, x, widgetWidth, widgetHeight = self.get_allocation()
        if self.__pixBuf != None:
            self.__previousWidgetWidth = widgetWidth
            self.__previousWidgetHeight = widgetHeight
            a = min(float(widgetWidth) / self.__pixBuf.get_width(),
                    float(widgetHeight) / self.__pixBuf.get_height())
            self.__wantedZoom = self._log(self._ZOOMFACTOR, a)
            self.__wantedZoom = min(self.__wantedZoom, 0)
            self.__wantedZoom = max(self.__wantedZoom, self._MIN_ZOOM)
            self.renderImage()

    def _log(self, base, value):
        return math.log(value) / math.log(base)

    def zoomIn(self, *foo):
        self.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.__fitToWindowMode = False
        if self.__wantedZoom <= self._MAX_ZOOM:
            self.__wantedZoom = math.floor(self.__wantedZoom + 1)
            self.renderImage()

    def zoomOut(self, *foo):
        self.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.__fitToWindowMode = False
        if self.__wantedZoom >= self._MIN_ZOOM:
            self.__wantedZoom = math.ceil(self.__wantedZoom - 1)
            self.renderImage()

    def zoom100(self, *foo):
        self.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.__fitToWindowMode = False
        self.__wantedZoom = 0
        self.renderImage()

    def scrollEventHandler(self, widget, gdkEvent):
        if gdkEvent.type == gtk.gdk.SCROLL:
            if gdkEvent.direction == gtk.gdk.SCROLL_UP:
                self.zoomOut()
            elif gdkEvent.direction == gtk.gdk.SCROLL_DOWN:
                self.zoomIn()
            return True
        else:
            return False
