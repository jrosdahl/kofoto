import gtk
import gtk.gdk
import math
import gobject
import gc
from gtk import TRUE, FALSE

class ImageView(gtk.ScrolledWindow):
    # TODO: Read from configuration file?
    _INTERPOLATION_TYPE = gtk.gdk.INTERP_BILINEAR
    # gtk.gdk.INTERP_HYPER is slower but gives better quality.
    _MAX_IMAGE_SIZE = 2000
    _MIN_IMAGE_SIZE = 1
    _MIN_ZOOM = -100
    _MAX_ZOOM = 1
    _ZOOMFACTOR = 1.2
    
    _pixBuf = None
    _currentZoom = None
    _wantedZoom = None
    _image = gtk.Image()            
    _fitToWindowMode = TRUE
    _previousWidgetWidth = 0
    _previousWidgetHeight = 0
    
    def __init__(self):
        gtk.ScrolledWindow.__init__(self)
        eventBox = gtk.EventBox()
        eventBox.add(self._image)
        self.add_with_viewport(eventBox)
        self.add_events(gtk.gdk.ALL_EVENTS_MASK)
        self.connect_after("size_allocate", self.resizeEventHandler)
        self.connect("scroll_event", self.scrollEventHandler)

    def loadFile(self, filename):
        # TODO: Loading file should be asyncronous to avoid freezing the gtk-main loop
        try:
            gc.collect()
            self._pixBuf = gtk.gdk.pixbuf_new_from_file(filename)
            self._image.show()
            self._newImageLoaded = TRUE
            self.fitToWindow()
        except gobject.GError:
            self._pixBuf = None
            self._image.hide()

    def clear(self):
        self._image.hide()
        self._image.set_from_file(None)
        self._pixBuf = None
        gc.collect()
            
    def renderImage(self):
        # TODO: Scaling should be asyncronous to avoid freezing the gtk-main loop
        if self._pixBuf == None:
            # No image loaded
            self._image.hide()
            return
        if self._currentZoom == self._wantedZoom and self._newImageLoaded == FALSE:
            return
        if self._wantedZoom == 0:
            pixBufResized = self._pixBuf
        else:
            zoomMultiplicator = pow(self._ZOOMFACTOR, self._wantedZoom)
            wantedWidth = self._pixBuf.get_width() * zoomMultiplicator 
            wantedHeight = self._pixBuf.get_height() * zoomMultiplicator 
            if min(wantedWidth, wantedHeight) < self._MIN_IMAGE_SIZE:
                # Too small image size
                return
            if max(wantedWidth, wantedHeight) > self._MAX_IMAGE_SIZE:
                # Too large image size
                return
            pixBufResized = self._pixBuf.scale_simple(wantedWidth,
                                                      wantedHeight,
                                                      self._INTERPOLATION_TYPE)
        pixMap, mask = pixBufResized.render_pixmap_and_mask()
        self._image.set_from_pixmap(pixMap, mask)
        self._newImageLoaded = FALSE
        self._currentZoom = self._wantedZoom
        gc.collect()

    def resizeEventHandler(self, widget, gdkEvent):
        if self._fitToWindowMode == TRUE:
            x, y, width, height = self.get_allocation()
            if height != self._previousWidgetHeight or width != self._previousWidgetWidth:
                self.fitToWindow()
        return FALSE
        
    def fitToWindow(self, *foo):
        self._fitToWindowMode = TRUE
        self.set_policy(gtk.POLICY_NEVER, gtk.POLICY_NEVER)
        y, x, widgetWidth, widgetHeight = self.get_allocation()
        if self._pixBuf != None:
            self._previousWidgetWidth = widgetWidth
            self._previousWidgetHeight = widgetHeight
            a = min(float(widgetWidth) / self._pixBuf.get_width(),
                    float(widgetHeight) / self._pixBuf.get_height())
            self._wantedZoom = self._log(self._ZOOMFACTOR, a)
            self._wantedZoom = min(self._wantedZoom, 0)
            self._wantedZoom = max(self._wantedZoom, self._MIN_ZOOM)
            self.renderImage()
        
    def _log(self, base, value):
        return math.log(value) / math.log(base)

    def zoomIn(self, *foo):
        self.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self._fitToWindowMode = FALSE
        if self._wantedZoom <= self._MAX_ZOOM:
            self._wantedZoom = math.floor(self._wantedZoom + 1)
            self.renderImage()
                
    def zoomOut(self, *foo):
        self.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self._fitToWindowMode = FALSE
        if self._wantedZoom >= self._MIN_ZOOM:
            self._wantedZoom = math.ceil(self._wantedZoom - 1)
            self.renderImage()

    def zoom100(self, *foo):
        self.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self._fitToWindowMode = FALSE
        self._wantedZoom = 0
        self.renderImage()
                    
    def scrollEventHandler(self, widget, gdkEvent):
        if gdkEvent.type == gtk.gdk.SCROLL:
            if gdkEvent.direction == gtk.gdk.SCROLL_UP:
                self.zoomOut()
            elif gdkEvent.direction == gtk.gdk.SCROLL_DOWN:
                self.zoomIn()
            return TRUE
        else:
            return FALSE

