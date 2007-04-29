"""
This module contains the ImageView class.
"""

__all__ = ["ImageView"]

if __name__ == "__main__":
    import pygtk
    pygtk.require("2.0")
import gc
import gtk
import gobject
import operator
import os
from kofoto.alternative import Alternative
from kofoto.gkofoto.environment import env
from kofoto.rectangle import Rectangle

def _gdk_rectangle_size(gdk_rectangle):
    return Rectangle(gdk_rectangle.width, gdk_rectangle.height)

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

class ImageView(gtk.Table):
    """A quick image view widget supporting zooming."""

    # Possible values of self._zoom_mode.
    ZoomMode = Alternative("BestFit", "ActualSize", "Zoom")

    # Hard-coded for now.
    _MOUSE_WHEEL_ZOOM_FACTOR = 1.2

    def __init__(self):
        self.__gobject_init__() # TODO: Use gtk.Table.__init__ in PyGTK 2.8.

        # Displayed pixbuf; None if not available.
        self._displayed_pixbuf = None

        # Zoom factor to use for one zoom step.
        self._zoom_factor = 1.5

        # Zoom size in pixels (a float, so that self._zoom_size *
        # self._zoom_factor * 1/self._zoom_factor == self._zoom_size).
        self._zoom_size = 0.0

        # Zoom mode.
        self._zoom_mode = ImageView.ZoomMode.BestFit

        # Whether the widget should prescale resized images while
        # waiting for the real thing.
        self._prescale_mode = True

        # Function to call when a new pixbuf size is wanted. None if
        # ImageView.set_image has not yet been called.
        self._request_pixbuf_func = None

        # The size of the original image as a Rectangle instance. None
        # if not yet known.
        self._available_size = None

        # Remember requested pixbuf size (a Rectangle instance or
        # None) to avoid unnecessary reloading.
        self._previously_requested_pixbuf_size = None

        # Whether scrolling by mouse dragging is enabled, i.e.,
        # whether there is at least one visible scroll bar.
        self._mouse_dragging_enabled = False

        # Used to remember reference coordinates for mouse dragging.
        self._last_mouse_drag_reference_x = None
        self._last_mouse_drag_reference_y = None

        # Pixbuf to display on errors.
        self._error_pixbuf = self.render_icon(
            gtk.STOCK_DIALOG_ERROR, gtk.ICON_SIZE_DIALOG, "kofoto")

        # Mouse cursors.
        display = gtk.gdk.display_get_default()
        pixbuf = gtk.gdk.pixbuf_new_from_file(
            os.path.join(env.iconDir, "hand-open.png"))
        self._open_hand_cursor = gtk.gdk.Cursor(display, pixbuf, 13, 13)
        pixbuf = gtk.gdk.pixbuf_new_from_file(
            os.path.join(env.iconDir, "hand-closed.png"))
        self._closed_hand_cursor = gtk.gdk.Cursor(display, pixbuf, 13, 13)

        # Subwidgets.
        self.resize(2, 2)
        self._eventbox_widget = gtk.EventBox()
        self._image_widget = gtk.DrawingArea()
        ew = self._eventbox_widget
        iw = self._image_widget
        options = gtk.FILL | gtk.EXPAND | gtk.SHRINK
        self.attach(ew, 0, 1, 0, 1, options, options)
        ew.add(iw)
        iw.connect_after("realize", self._image_realize_cb)
        iw.connect_after("unrealize", self._image_unrealize_cb)
        self.connect_after("size-allocate", self._after_size_allocate_cb)
        iw.connect("expose-event", self._image_expose_event_cb)
        ew.connect("button-press-event", self._image_button_press_event_cb)
        ew.connect("button-release-event", self._image_button_release_event_cb)
        ew.connect("motion-notify-event", self._image_motion_notify_event_cb)
        ew.connect("scroll-event", self._image_scroll_event_cb)

        self._width_adjustment = gtk.Adjustment()
        wadj = self._width_adjustment
        self._width_scrollbar = gtk.HScrollbar(wadj)
        wscrollbar = self._width_scrollbar
        self.attach(wscrollbar, 0, 1, 1, 2, gtk.FILL, gtk.FILL)

        self._height_adjustment = gtk.Adjustment()
        hadj = self._height_adjustment
        self._height_scrollbar = gtk.VScrollbar(hadj)
        hscrollbar = self._height_scrollbar
        self.attach(hscrollbar, 1, 2, 0, 1, gtk.FILL, gtk.FILL)

        # Listen for adjustment changes so that we can make
        # adjustments behave nicely when zooming and resizing.
        wadj.connect("value-changed", self._width_adjustment_value_changed)
        hadj.connect("value-changed", self._height_adjustment_value_changed)

        self._image_widget.show()
        self._eventbox_widget.show()

    def clear(self):
        """Make the widget display nothing."""

        assert self._is_realized()
        self._available_size = None
        self._request_pixbuf_func = None
        self._displayed_pixbuf = None
        self._update_scroll_bars()
        self._image_widget.queue_draw()
        gc.collect() # Help GTK to get rid of the old pixbuf.

    def get_image_widget(self):
        """Get the wrapped image widget.

        Returns the wrapped image widget. This widget is the widget to
        which mouse event handlers should be connected. (The return
        value is actually an eventbox in which the image widget is
        wrapped.)
        """
        return self._eventbox_widget

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

        if self._zoom_mode == ImageView.ZoomMode.ActualSize:
            return None
        else:
            return tuple(self._calculate_wanted_image_size())

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

        gtk.Table.modify_bg(self, state, color)
        self._image_widget.modify_bg(state, color)

    def set_error(self):
        """Indicate that loading of the image failed.

        This method should be called by the pixbuf request function
        passed to ImageView.set_image if there was an error loading
        the pixbuf.
        """

        assert self._is_realized() and self._image_is_set()
        self._available_size = _pixbuf_size(self._error_pixbuf)
        self._displayed_pixbuf = self._error_pixbuf
        self._update_scroll_bars()
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

        if not (self._is_realized() and self._image_is_set()):
            return
        if self._displayed_pixbuf_is_current():
            if not Rectangle(*available_size).fits_within(
                    self._available_size):
                # The original has grown on disk, so we might want a
                # larger pixbuf if available.
                self._request_pixbuf_and_prescale()
                return
        self._available_size = Rectangle(*available_size)
        self._create_displayed_pixbuf(pixbuf)
        self._update_scroll_bars()
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
            self._request_pixbuf_and_prescale()

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
        self._zoom_mode = ImageView.ZoomMode.Zoom
        level = min(level, 1.0)
        max_avail = max(
            self._available_size.width, self._available_size.height)
        self._zoom_size = level * max_avail
        self._zoom_changed()

    def zoom_to_actual(self):
        """Zoom to actual (pixel-wise) image size."""

        assert self._is_realized() and self._image_is_set()
        self._zoom_mode = ImageView.ZoomMode.ActualSize
        self._zoom_changed()

    def zoom_to_fit(self):
        """Zoom image to fit the current widget size."""

        assert self._is_realized() and self._image_is_set()
        self._zoom_mode = ImageView.ZoomMode.BestFit
        self._zoom_changed()

    def _after_size_allocate_cb(self, widget, rect):
        if not (self._is_realized() and self._image_is_set()):
            return
        self._maybe_request_new_pixbuf_and_prescale()
        self._update_scroll_bars()
        self._image_widget.queue_draw()

    def _calculate_best_fit_image_size(self):
        allocation = self._image_widget.allocation
        return Rectangle(allocation.width, allocation.height)

    def _calculate_wanted_image_size(self):
        if self._zoom_mode == ImageView.ZoomMode.ActualSize:
            return self._available_size
        else:
            if self._zoom_mode == ImageView.ZoomMode.BestFit:
                return self._calculate_best_fit_image_size()
            else:
                return self._calculate_zoomed_image_boundary()

    def _calculate_zoomed_image_boundary(self):
        zsize = int(round(self._zoom_size))
        return Rectangle(zsize, zsize)

    def _create_displayed_pixbuf(self, pixbuf):
        size = self._calculate_wanted_image_size()
        if self._zoom_mode == ImageView.ZoomMode.ActualSize:
            self._displayed_pixbuf = pixbuf
        elif size == _pixbuf_size(pixbuf):
            self._displayed_pixbuf = pixbuf
        else:
            self._displayed_pixbuf = _safely_downscale_pixbuf(pixbuf, size)

    def _disable_mouse_dragging(self):
        self._mouse_dragging_enabled = False
        self._image_widget.window.set_cursor(None)

    def _displayed_pixbuf_is_current(self):
        return self._available_size is not None

    def _draw_pixbuf(self):
        if not self._displayed_pixbuf:
            return

        # The rectangle <source_x, source_y> to <source_x + width,
        # source_y + height> defines which part of the pixbuf to draw
        # and the rectangle <target_x, target_y> to <target_x + width,
        # target_y + height> defines where to draw it on the image
        # widget.
        source_x = int(round(self._width_adjustment.value))
        width = int(round(self._width_adjustment.page_size))
        source_y = int(round(self._height_adjustment.value))
        height = int(round(self._height_adjustment.page_size))

        # Draw the pixbuf in the center if it is smaller than the
        # image widget.
        allocation = self._image_widget.allocation
        target_x = max(allocation.width - width, 0) / 2
        target_y = max(allocation.height - height, 0) / 2

        dp = self._displayed_pixbuf
        gcontext = self._image_widget.style.fg_gc[gtk.STATE_NORMAL]
        self._image_widget.window.draw_pixbuf(
            gcontext, dp,
            source_x, source_y,
            target_x, target_y,
            width, height)

    def _enable_mouse_dragging(self):
        self._mouse_dragging_enabled = True
        self._image_widget.window.set_cursor(self._open_hand_cursor)

    def _height_adjustment_value_changed(self, adj):
        self._image_widget.queue_draw()

    def _image_button_press_event_cb(self, widget, event):
        if self._mouse_dragging_enabled and event.button == 1:
            self._image_widget.window.set_cursor(self._closed_hand_cursor)
            self._last_mouse_drag_reference_x = event.x
            self._last_mouse_drag_reference_y = event.y

    def _image_button_release_event_cb(self, widget, event):
        if self._mouse_dragging_enabled and event.button == 1:
            self._image_widget.window.set_cursor(self._open_hand_cursor)

    def _image_expose_event_cb(self, widget, event):
        self._draw_pixbuf()

    def _image_is_set(self):
        return self._request_pixbuf_func is not None

    def _image_motion_notify_event_cb(self, widget, event):
        if self._mouse_dragging_enabled:
            wa = self._width_adjustment
            ha = self._height_adjustment

            dx = event.x - self._last_mouse_drag_reference_x
            dy = event.y - self._last_mouse_drag_reference_y
            new_w_value = max(0, min(wa.upper - wa.page_size, wa.value - dx))
            new_h_value = max(0, min(ha.upper - ha.page_size, ha.value - dy))
            self._last_mouse_drag_reference_x -= new_w_value - wa.value
            self._last_mouse_drag_reference_y -= new_h_value - ha.value
            wa.value = new_w_value
            ha.value = new_h_value

    def _image_realize_cb(self, widget):
        if self._image_is_set():
            self._request_pixbuf_and_prescale()

    def _image_scroll_event_cb(self, widget, event):
        allocation = self._image_widget.allocation
        center_x = float(event.x) / allocation.width
        center_y = float(event.y) / allocation.height
        if event.direction == gtk.gdk.SCROLL_DOWN:
            self._zoom_inout(
                1 / ImageView._MOUSE_WHEEL_ZOOM_FACTOR, center_x, center_y)
        elif event.direction == gtk.gdk.SCROLL_UP:
            self._zoom_inout(
                ImageView._MOUSE_WHEEL_ZOOM_FACTOR, center_x, center_y)

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

    def _maybe_request_new_pixbuf_and_prescale(self):
        if self._zoom_mode != ImageView.ZoomMode.BestFit:
            # We already have (requested) a pixbuf of the correct
            # size.
            return
        wanted_size = self._calculate_best_fit_image_size()
        if self._displayed_pixbuf_is_current():
            # See comment in _request_pixbuf_and_prescale.
            limited_wanted_size = wanted_size.downscaled_to(
                self._available_size)
        else:
            limited_wanted_size = wanted_size
        psize = self._previously_requested_pixbuf_size
        if psize is not None and limited_wanted_size != psize:
            self._request_pixbuf_and_prescale()

    def _request_pixbuf_and_prescale(self, center_x=0.5, center_y=0.5):
        # Remember/guess the actual size of the pixbuf to be
        # loaded by _request_pixbuf_func. This is done to
        # avoid _request_pixbuf_and_prescale being called when
        # we expect that the currently displayed image already
        # is of the correct (full) size.
        size = self._calculate_wanted_image_size()
        self._previously_requested_pixbuf_size = size

        if self._prescale_mode and self._displayed_pixbuf_is_current():
            self._displayed_pixbuf = _safely_rescale_pixbuf(
                self._displayed_pixbuf, size)
            if self._zoom_mode == ImageView.ZoomMode.Zoom:
                self._update_scroll_bars(center_x, center_y)
                self._draw_pixbuf()
        self._request_pixbuf_func(size)

    def _update_scroll_bars(self, center_w=0.5, center_h=0.5):
        if self._displayed_pixbuf is None:
            self._width_scrollbar.hide()
            self._height_scrollbar.hide()
            self._disable_mouse_dragging()
            return

        old_pb_width = self._width_adjustment.upper
        old_pb_height = self._height_adjustment.upper
        new_pb_width = self._displayed_pixbuf.get_width()
        new_pb_height = self._displayed_pixbuf.get_height()

        if self._zoom_mode == ImageView.ZoomMode.BestFit:
            self._width_scrollbar.hide()
            self._height_scrollbar.hide()
            self._width_adjustment.set_all(
                value=0, page_size=new_pb_width, upper=new_pb_width)
            self._height_adjustment.set_all(
                value=0, page_size=new_pb_height, upper=new_pb_height)
            self._disable_mouse_dragging()
            return

        allocated_table_size = _gdk_rectangle_size(self.get_allocation())

        # The size to allocate to the image widget. Start out with an
        # image size equal to the whole table, i.e., no scroll bars.
        size = Rectangle(*allocated_table_size)

        h_sb_height = self._width_scrollbar.size_request()[1]
        v_sb_width = self._height_scrollbar.size_request()[0]
        show_w_scroll_bar = False
        show_h_scroll_bar = False
        for i in range(2): # Two loops are enough to stabilize the result.
            if not show_w_scroll_bar and \
                    new_pb_width > size.width:
                show_w_scroll_bar = True
                size.height -= h_sb_height
            if not show_h_scroll_bar and \
                    new_pb_height > size.height:
                show_h_scroll_bar = True
                size.width -= v_sb_width

        # If the image widget allocation is larger than the displayed
        # pixbuf, make it not larger than the pixbuf.
        size.width = min(size.width, new_pb_width)
        size.height = min(size.height, new_pb_height)

        old_w_page_size = self._width_adjustment.page_size
        old_h_page_size = self._height_adjustment.page_size

        self._width_adjustment.set_all(
            upper=new_pb_width,
            page_size=size.width,
            page_increment=size.width,
            step_increment=size.width / 10.0)
        self._height_adjustment.set_all(
            upper=new_pb_height,
            page_size=size.height,
            page_increment=size.height,
            step_increment=size.height / 10.0)

        w_value = self._width_adjustment.value
        h_value = self._height_adjustment.value

        # Adjust adjustment values so that we zoom relative to the
        # chosen center point.
        w_value = \
            (new_pb_width / old_pb_width) \
            * (w_value + center_w * old_w_page_size) \
            - center_w * size.width
        h_value = \
            (new_pb_height / old_pb_height) \
            * (h_value + center_h * old_h_page_size) \
            - center_h * size.height

        # Adjust adjustment values so that they aren't smaller or
        # larger than allowed (which they may be after a zoom).
        w_value = min(
            max(w_value, 0),
            self._width_adjustment.upper - self._width_adjustment.page_size)
        h_value = min(
            max(h_value, 0),
            self._height_adjustment.upper - self._height_adjustment.page_size)

        self._width_adjustment.value = w_value
        self._height_adjustment.value = h_value

        if show_w_scroll_bar:
            self._width_scrollbar.show()
        else:
            self._width_scrollbar.hide()
        if show_h_scroll_bar:
            self._height_scrollbar.show()
        else:
            self._height_scrollbar.hide()

        if show_w_scroll_bar or show_h_scroll_bar:
            self._enable_mouse_dragging()
        else:
            self._disable_mouse_dragging()

    def _update_zoom_size_to_current(self):
        if self._zoom_mode == ImageView.ZoomMode.BestFit:
            allocation = self._image_widget.allocation
            self._zoom_size = float(max(allocation.width, allocation.height))
        elif self._zoom_mode == ImageView.ZoomMode.ActualSize:
            self._zoom_size = max(
                self._available_size.width, self._available_size.height)

    def _width_adjustment_value_changed(self, adj):
        self._image_widget.queue_draw()

    def _zoom_changed(self, center_x=0.5, center_y=0.5):
        self._request_pixbuf_and_prescale(center_x, center_y)
        self._update_scroll_bars(center_x, center_y)
        self._image_widget.queue_draw()

    def _zoom_inout(self, factor, center_x=0.5, center_y=0.5):
        self._update_zoom_size_to_current()
        self._zoom_mode = ImageView.ZoomMode.Zoom
        # The two calls to _limit_zoom_size_to_available_size below
        # make the zooming feel right in the following two cases (A
        # and B):
        #
        # 1. Both A & B: Enter zoom mode on a large image with a
        #    sufficiently large zoom size.
        # 2. Both A & B: Change to an image that is smaller than the
        #    current zoom size.
        # 3. Case A: Zoom in and then zoom out. Case B: Zoom out.
        self._limit_zoom_size_to_available_size()
        self._zoom_size *= factor
        self._limit_zoom_size_to_available_size()
        self._zoom_changed(center_x, center_y)

gobject.type_register(ImageView) # TODO: Not needed in PyGTK 2.8.

######################################################################

if __name__ == "__main__":
    from kofoto.gkofoto.cachingpixbufloader import CachingPixbufLoader
    import sys

    env.iconDir = "%s/../../../gkofoto/icons" % os.path.dirname(sys.argv[0])

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
