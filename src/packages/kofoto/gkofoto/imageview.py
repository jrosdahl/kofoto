# pylint: disable-msg=F0203, E0201

"""
This module contains the ImageView class.
"""

# TODO:
#
# * Let the picture stay centered when zooming in/out. (This seems to
#   be harder than it, eh, seems; the signalling between
#   ScrolledWindow and the adjustments is kind of puzzling. Probably
#   need to get rid of ScrolledWindow and make something out of a
#   table, two scrollbars and two adjustments or so.)
# * Drag to scroll if the image is larger than displayed.
# * Only draw visible image parts on expose-event.
# * Bind mouse wheel to zoom in/out.
# * Bind arrow keys.

__all__ = ["ImageView"]

if __name__ == "__main__":
    import pygtk
    pygtk.require("2.0")
import gtk
import gobject
import gc
import operator
from kofoto.rectangle import Rectangle

def _pixbuf_size(pixbuf):
    return Rectangle(pixbuf.get_width(), pixbuf.get_height())

def _safely_downscale_pixbuf(pixbuf, limit):
    size = _pixbuf_size(pixbuf)
    return _safely_scale_pixbuf(pixbuf, size.downscaled_to(limit))

def _safely_rescale_pixbuf(pixbuf, limit):
    size = _pixbuf_size(pixbuf)
    return _safely_scale_pixbuf(pixbuf, size.rescaled_to(limit))

def _safely_scale_pixbuf(pixbuf, size):
    # The scaling with a factor not more than 30 is a work-around for
    # a scaling bug in GTK+.

    def scale_pixbuf(pixbuf, size):
        if not Rectangle(1, 1).fits_within(size):
            size = Rectangle(1, 1)
        return pixbuf.scale_simple(
            int(size.width), int(size.height), gtk.gdk.INTERP_BILINEAR)

    psize = _pixbuf_size(pixbuf)
    if psize.fits_within(size):
        # Scale up.
        factor = 1/30.0 # Somewhat arbitrary.
        cmpfn = operator.lt
    else:
        # Scale down.
        factor = 30 # Somewhat arbitrary.
        cmpfn = operator.gt
    while cmpfn(float(psize.max()) / size.max(), factor):
        psize /= factor
        pixbuf = scale_pixbuf(pixbuf, psize)
    return scale_pixbuf(pixbuf, size)

class ImageView(gtk.ScrolledWindow):
    """A reasonably quick image view widget supporting zooming."""

    # Possible values of self._zoom_mode
    _ZOOM_MODE_BEST_FIT = object()
    _ZOOM_MODE_ACTUAL_SIZE = object()
    _ZOOM_MODE_ZOOM = object()

    def __init__(self):
        self.__gobject_init__() # TODO: Use gtk.ScrolledWindow.__init__ in PyGTK 2.8.

        # Displayed pixbuf; None if not available.
        self._displayed_pixbuf = None

        # Zoom factor to use for one zoom step.
        self._zoom_factor = 1.5

        # Zoom size in pixels (a float, so that self._zoom_size *
        # self._zoom_factor * 1/self._zoom_factor == self._zoom_size).
        self._zoom_size = 0.0

        # Zoom mode.
        self._zoom_mode = ImageView._ZOOM_MODE_BEST_FIT

        # Whether the widget should prescale resized images while
        # waiting for the real thing.
        self._prescale_mode = True

        # Function to call when a new pixbuf size is wanted. None if
        # ImageView.set_image has not yet been called.
        self._request_pixbuf_func = None

        # The original image as a Rectangle instance. None if not yet
        # known.
        self._available_size = None

        # Remember requested image size (a Rectangle instance or None)
        # to avoid unnecessary reloading.
        self._previously_requested_image_size = None

        # Pixbuf to display on errors.
        self._error_pixbuf = self.render_icon(
            gtk.STOCK_DIALOG_ERROR, gtk.ICON_SIZE_DIALOG, "kofoto")

        # Subwidgets.
        self._eventbox_widget = gtk.EventBox()
        self._image_widget = gtk.DrawingArea()
        ew = self._eventbox_widget
        iw = self._image_widget
        self.add_with_viewport(ew)
        ew.add(iw)
        iw.connect_after("realize", self._image_realize_cb)
        iw.connect_after("unrealize", self._image_unrealize_cb)
        iw.connect_after("size-allocate", self._image_after_size_allocate_cb)
        iw.connect("expose-event", self._image_expose_event_cb)
        self.set_policy(gtk.POLICY_NEVER, gtk.POLICY_NEVER)

    def clear(self):
        """Make the widget display nothing."""

        assert self._is_realized()
        self._available_size = None
        self._displayed_pixbuf = None
        self._image_widget.queue_draw()
        gc.collect() # Help GTK to get rid of the old pixbuf.

    def get_prescale_mode(self):
        """Whether the widget should prescale a resized image."""

        return self._prescale_mode

    def get_wanted_image_size(self):
        """Get the currently wanted image size.

        Returns a tuple (width_limit, height_limit) or None. None
        indicates that the full-size image is wanted. The size is the
        same that will be passed to the load_pixbuf_func passed to
        set_image.
        """

        size = self._calculate_wanted_image_size()
        if size is None:
            return None
        else:
            return tuple(size)

    def get_zoom_level(self):
        """Get current zoom level."""

        if self._displayed_pixbuf is None:
            # Just return something.
            return 1.0
        else:
            # We know that the proportions of self._displayed_pixbuf
            # and the full-size image are the same since they are both
            # set in set_from_pixbuf/set_error.
            return (
                float(self._displayed_pixbuf.get_width()) /
                self._available_size.width)

    def modify_bg(self, state, color):
        """Set the background color.

        See gtk.Widget.modify_bg.
        """

        gtk.ScrolledWindow.modify_bg(self, state, color)
        self._image_widget.modify_bg(state, color)
        self.get_child().modify_bg(state, color)

    def set_error(self):
        """Indicate that loading of the image failed.

        This method should be called by the pixbuf request function
        passed to ImageView.set_image if there was an error loading
        the pixbuf.
        """

        assert self._is_realized() and self._image_is_set()
        self._available_size = _pixbuf_size(self._error_pixbuf)
        self._displayed_pixbuf = self._error_pixbuf
        self._image_widget.queue_draw()
        gc.collect() # Help GTK to get rid of the old pixbuf.

    def set_error_pixbuf(self, pixbuf):
        """Set the pixbuf displayed on errors."""

        self._error_pixbuf = pixbuf

    def set_from_pixbuf(self, pixbuf, available_size):
        """Set displayed pixbuf.

        This method should be called by the pixbuf request function
        passed to ImageView.set_image if the load was successful.

        Arguments:

        pixbuf           -- The pixbuf.
        available_size   -- Tuple (width, height) of the full-size image.
        """

        assert self._is_realized() and self._image_is_set()
        if self._available_size is not None:
            if not Rectangle(*available_size).fits_within(self._available_size):
                # The original has grown on disk, so we might want a
                # larger pixbuf if available.
                self._load_pixbuf()
                return
        self._available_size = Rectangle(*available_size)
        self._create_displayed_pixbuf(pixbuf)
        self._image_widget.queue_draw()
        gc.collect() # Help GTK to get rid of the old pixbuf.

    def set_image(self, load_pixbuf_func):
        """Set image to display in the view.

        This method indirectly sets the image to be displayed in the
        widget. The argument function will be called (possibly
        multiple times) to request a new pixbuf. Here are the
        requirements on the function:

        1. The function must accept one parameter: a tuple of width
           limit and height limit in pixels, or None.
        2. If the limit parameter is None, a full-size pixbuf should
           be loaded.
        3. The function must
           a) call set_from_pixbuf with a the largest possible pixbuf
              that fits within the limit; or
           b) call set_error on failure.
        4. The image proportions must be retained when scaling down
           the image down to fit the limit.
        5. The loaded pixbuf must not be larger than the original
           image.

        Arguments:

        load_pixbuf_func -- The function.
        """

        self._request_pixbuf_func = load_pixbuf_func
        self._available_size = None
        if self._is_realized():
            self._load_pixbuf()

    def set_prescale_mode(self, mode):
        """Set whether the widget should prescale a resized image."""

        self._prescale_mode = mode

    def set_zoom_factor(self, factor):
        """Set the zoom factor."""

        self._zoom_factor = factor

    def zoom_in(self):
        """Zoom in one step."""

        assert self._is_realized() and self._image_is_set()
        self._zoom_inout(self._zoom_factor)

    def zoom_out(self):
        """Zoom out one step."""

        assert self._is_realized() and self._image_is_set()
        self._zoom_inout(1 / self._zoom_factor)

    def zoom_to(self, level):
        """Zoom to a given zoom level.

        Arguments:

        level -- The zoom level (a number). 1.0 means the full-size
                 image, 0.5 means a half-size image and so on.
        """

        assert self._is_realized() and self._image_is_set()
        self._zoom_mode = ImageView._ZOOM_MODE_ZOOM
        level = min(level, 1.0)
        max_avail = max(
            self._available_size.width, self._available_size.height)
        self._zoom_size = level * max_avail
        self._zoom_changed()

    def zoom_to_actual(self):
        """Zoom to actual (pixel-wise) image size."""

        assert self._is_realized() and self._image_is_set()
        self._zoom_mode = ImageView._ZOOM_MODE_ACTUAL_SIZE
        self._zoom_changed()

    def zoom_to_fit(self):
        """Zoom image to fit the current widget size."""

        assert self._is_realized() and self._image_is_set()
        self._zoom_mode = ImageView._ZOOM_MODE_BEST_FIT
        self.set_policy(gtk.POLICY_NEVER, gtk.POLICY_NEVER)
        self._resize_image_widget()

    def _calculate_best_fit_image_size(self):
        allocation = self._image_widget.allocation
        return Rectangle(allocation.width, allocation.height)

    def _calculate_wanted_image_size(self):
        if self._zoom_mode == ImageView._ZOOM_MODE_ACTUAL_SIZE:
            return None
        else:
            if self._zoom_mode == ImageView._ZOOM_MODE_BEST_FIT:
                size = self._calculate_best_fit_image_size()
            else:
                size = self._calculate_zoomed_image_size()
            return size

    def _calculate_zoomed_image_size(self):
        zsize = int(round(self._zoom_size))
        return Rectangle(zsize, zsize)

    def _create_displayed_pixbuf(self, pixbuf):
        size = self._calculate_wanted_image_size()
        if self._zoom_mode == ImageView._ZOOM_MODE_ACTUAL_SIZE:
            self._displayed_pixbuf = pixbuf
        elif size == _pixbuf_size(pixbuf):
            self._displayed_pixbuf = pixbuf
        else:
            self._displayed_pixbuf = _safely_downscale_pixbuf(pixbuf, size)
        self._resize_image_widget()

    def _displayed_pixbuf_is_current(self):
        return self._available_size is not None

    def _image_after_size_allocate_cb(self, widget, rect):
        if not (self._is_realized() and self._image_is_set()):
            return
        if self._zoom_mode != ImageView._ZOOM_MODE_BEST_FIT:
            return
        wanted_size = self._calculate_best_fit_image_size()
        if self._displayed_pixbuf_is_current():
            # We now know that self._available_size is available. 
            # Also see comment in _load_pixbuf.
            limited_wanted_size = wanted_size.downscaled_to(
                self._available_size)
        else:
            limited_wanted_size = wanted_size
        psize = self._previously_requested_image_size
        if psize is not None and limited_wanted_size != psize:
            self._load_pixbuf()

    def _image_expose_event_cb(self, widget, event):
        if not self._displayed_pixbuf:
            return
        allocation = self._image_widget.allocation
        pb = self._displayed_pixbuf
        x = max(allocation.width - pb.get_width(), 0) / 2
        y = max(allocation.height - pb.get_height(), 0) / 2
        gcontext = self._image_widget.style.fg_gc[gtk.STATE_NORMAL]
        dp = self._displayed_pixbuf
        self._image_widget.window.draw_pixbuf(gcontext, dp, 0, 0, x, y, -1, -1)

    def _image_realize_cb(self, widget):
        if self._image_is_set():
            self._load_pixbuf()

    def _image_is_set(self):
        return self._request_pixbuf_func is not None

    def _image_unrealize_cb(self, widget):
        self._displayed_pixbuf = None
        gc.collect() # Help GTK to get rid of the old pixbuf.

    def _is_realized(self):
        return self.flags() & gtk.REALIZED

    def _limit_zoom_size_to_available_size(self):
        if self._displayed_pixbuf_is_current():
            self._zoom_size = float(min(
                self._zoom_size,
                max(self._available_size.width, self._available_size.height)))

    def _load_pixbuf(self):
        size = self._calculate_wanted_image_size()
        if self._zoom_mode != ImageView._ZOOM_MODE_ACTUAL_SIZE:
            dp = self._displayed_pixbuf
            if (self._prescale_mode and
                self._displayed_pixbuf_is_current() and
                size.fits_within(self._available_size)):
                # Don't prescale to a pixbuf larger than the full-size
                # image.
                self._displayed_pixbuf = _safely_rescale_pixbuf(dp, size)
                self._resize_image_widget()
            if self._displayed_pixbuf_is_current():
                # Remember/guess the actual size of the pixbuf to be
                # loaded by _request_pixbuf_func. This is done to
                # avoid _load_pixbuf being called when we expect that
                # the currently displayed already is of the correct
                # (full) size.
                self._previously_requested_image_size = size.downscaled_to(
                    self._available_size)
            else:
                self._previously_requested_image_size = size
        self._request_pixbuf_func(size)

    def _resize_image_widget(self):
        # The signal size-allocate is emitted when set_size_request is
        # called.
        if self._zoom_mode == ImageView._ZOOM_MODE_BEST_FIT:
            self._image_widget.set_size_request(-1, -1)
        else:
            size = _pixbuf_size(self._displayed_pixbuf)
            self._image_widget.set_size_request(size.width, size.height)

    def _set_zoom_size_from_widget_allocation(self):
        allocation = self._image_widget.allocation
        self._zoom_size = float(max(allocation.width, allocation.height))

    def _zoom_changed(self):
        self.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self._load_pixbuf()

    def _zoom_inout(self, factor):
        if self._zoom_mode != ImageView._ZOOM_MODE_ZOOM:
            self._zoom_mode = ImageView._ZOOM_MODE_ZOOM
            self._set_zoom_size_from_widget_allocation()
        # The two calls to _limit_zoom_size_to_available_size below
        # make the zooming feel right in the following two cases:
        #
        # 1. Both cases: Enter zoom mode on a large image with a
        #    sufficiently large zoom size.
        # 2. Both cases: Change to an image that is smaller than the
        #    current zoom size.
        # 3. Case 1: Zoom in and then zoom out. Case 2: Zoom out.
        self._limit_zoom_size_to_available_size()
        self._zoom_size *= factor
        self._limit_zoom_size_to_available_size()
        self._zoom_changed()

gobject.type_register(ImageView) # TODO: Not needed in PyGTK 2.8.

######################################################################

if __name__ == "__main__":
    from kofoto.gkofoto.cachingpixbufloader import CachingPixbufLoader
    import sys

    caching_pixbuf_loader = CachingPixbufLoader()

    class State:
        def __init__(self):
            self._latest_handle = None
            self._latest_key = None
            self._current_pic_index = -1
            self._image_paths = sys.argv[1:]

        def get_image_async_cb(self, size):
            path = self._image_paths[self._current_pic_index]
            if self._latest_handle is not None:
                caching_pixbuf_loader.cancel_load(self._latest_handle)
                if path == self._latest_key[0]:
                    caching_pixbuf_loader.unload(*self._latest_key)
            self._latest_handle = caching_pixbuf_loader.load(
                path,
                size,
                imageview.set_from_pixbuf,
                imageview.set_error)
            self._latest_key = (path, size)

        def next_image(self, *unused):
            self._current_pic_index = \
                (self._current_pic_index + 1) % len(self._image_paths)
            imageview.set_image(self.get_image_async_cb)

    def callback_wrapper(fn):
        def _f(*unused):
            fn()
        return _f

    def toggle_prescale_mode(widget):
        imageview.set_prescale_mode(widget.get_active())

    appstate = State()

    window = gtk.Window()
    window.set_default_size(300, 200)

    imageview = ImageView()
    window.add(imageview)

    control_window = gtk.Window()
    control_window.set_transient_for(window)

    control_box = gtk.VBox()
    control_window.add(control_box)

    clear_button = gtk.Button(stock=gtk.STOCK_CLEAR)
    control_box.add(clear_button)
    clear_button.connect("clicked", callback_wrapper(imageview.clear))

    ztf_button = gtk.Button(stock=gtk.STOCK_ZOOM_FIT)
    control_box.add(ztf_button)
    ztf_button.connect("clicked", callback_wrapper(imageview.zoom_to_fit))

    za_button = gtk.Button(stock=gtk.STOCK_ZOOM_100)
    control_box.add(za_button)
    za_button.connect("clicked", callback_wrapper(imageview.zoom_to_actual))

    zi_button = gtk.Button(stock=gtk.STOCK_ZOOM_IN)
    control_box.add(zi_button)
    zi_button.connect("clicked", callback_wrapper(imageview.zoom_in))

    zo_button = gtk.Button(stock=gtk.STOCK_ZOOM_OUT)
    control_box.add(zo_button)
    zo_button.connect("clicked", callback_wrapper(imageview.zoom_out))

    next_button = gtk.Button(stock=gtk.STOCK_GO_FORWARD)
    control_box.add(next_button)
    next_button.connect("clicked", appstate.next_image)

    prescale_checkbutton = gtk.CheckButton("Prescale mode")
    prescale_checkbutton.set_active(True)
    control_box.add(prescale_checkbutton)
    prescale_checkbutton.connect("toggled", toggle_prescale_mode)

    window.show_all()
    window.connect("destroy", gtk.main_quit)

    control_window.show_all()

    appstate.next_image()
    gtk.main()
