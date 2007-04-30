"""This module contains the FullScreenWindow class."""

__all__ = ["FullScreenWindow"]

import gtk
import gobject
from kofoto.gkofoto.imageview import ImageView
from kofoto.gkofoto.environment import env

class FullScreenWindow(gtk.Window):
    """A fullscreen window widget."""

    def __init__(self, image_versions, current_index=0):
        """Constructor.

        Arguments:

        image_versions -- A list of ImageVersion instance to display.
        current_index  -- Where to start in image_versions.
        """

        self.__gobject_init__() # TODO: Use gtk.Window.__init__ in PyGTK 2.8.

        self._last_allocated_size = None
        self._image_versions = image_versions
        self._current_index = current_index
        self._latest_handle = None
        self._latest_size = (0, 0)

        bg_color = gtk.gdk.color_parse("#000000")
        fg_color = gtk.gdk.color_parse("#999999")

        eventbox = gtk.EventBox()
        vbox = gtk.VBox()
        eventbox.add(vbox)
        self._image_view = ImageView()
        self._image_view.set_error_pixbuf(
            gtk.gdk.pixbuf_new_from_file(env.unknownImageIconFileName))
        vbox.pack_start(self._image_view)
        self._info_label = gtk.Label()
        self._info_label.set_text(
            "No more images.\nPress escape to get back to GKofoto.")
        self._info_label.set_justify(gtk.JUSTIFY_CENTER)
        self._info_label.hide()
        vbox.pack_start(self._info_label)

        self.modify_bg(gtk.STATE_NORMAL, bg_color)
        eventbox.modify_bg(gtk.STATE_NORMAL, bg_color)
        self._image_view.modify_bg(gtk.STATE_NORMAL, bg_color)
        self._info_label.modify_fg(gtk.STATE_NORMAL, fg_color)
        self.add(eventbox)
        self.set_modal(True)
        self.set_default_size(400, 400)
        self.fullscreen()
        self.connect_after("map-event", self._after_map_event_cb)
        self.connect_after("size-allocate", self._after_size_allocate_cb)
        eventbox.connect("button-press-event", self._button_press_event_cb)
        self.connect("key-press-event", self._key_press_event_cb)

    def destroy(self):
        """Destroy the widget."""

        self._maybe_cancel_load()
        gtk.Window.destroy(self)

    # ----------------------------------------

    def _after_map_event_cb(self, *unused):
        self._hide_cursor()

    def _after_size_allocate_cb(self, widget, rect):
        allocated_size = (rect.width, rect.height)
        if allocated_size == self._last_allocated_size:
            return
        self._last_allocated_size = allocated_size
        self._goto(self._current_index)

    def _button_press_event_cb(self, widget, event):
        iv = self._image_view
        if event.button == 1 and iv.get_zoom_mode() == iv.ZoomMode.BestFit:
            self._goto(self._current_index + 1)

    def _display_end_screen(self):
        self._maybe_cancel_load()
        self._image_view.hide()
        self._info_label.show()

    def _get_image_async_cb(self, size):
        path = self._image_versions[self._current_index].getLocation()
        self._maybe_cancel_load()
        self._latest_handle = env.pixbufLoader.load(
            path,
            size,
            self._image_view.set_from_pixbuf,
            self._image_view.set_error)
        if size != self._latest_size:
            self._unload(self._latest_size)
        self._preload(size)
        self._latest_size = size

    def _goto(self, new_index):
        if new_index < 0:
            self._current_index = -1
            self._display_end_screen()
        elif new_index >= len(self._image_versions):
            self._current_index = len(self._image_versions)
            self._display_end_screen()
        else:
            self._current_index = new_index
            self._image_view.show()
            self._info_label.hide()
            self._image_view.set_image(self._get_image_async_cb)

    def _hide_cursor(self):
        pixmap = gtk.gdk.Pixmap(None, 1, 1, 1)
        color = gtk.gdk.Color()
        invisible_cursor = gtk.gdk.Cursor(pixmap, pixmap, color, color, 0, 0)
        self.window.set_cursor(invisible_cursor)

    def _is_valid_index(self, index):
        return 0 <= index < len(self._image_versions)

    def _key_press_event_cb(self, unused, event):
        k = gtk.keysyms
        if event.state == 0:
            if event.keyval in [k.space, k.Right, k.Down, k.Page_Down]:
                self._goto(self._current_index + 1)
                return True
            if event.keyval in [k.BackSpace, k.Left, k.Up, k.Page_Up]:
                self._goto(self._current_index - 1)
                return True
            if event.keyval == k.Home:
                self._goto(0)
                return True
            if event.keyval == k.End:
                self._goto(len(self._image_versions) - 1)
                return True
            if event.keyval == k.Escape:
                self.destroy()
                return True
            if event.keyval == k.plus:
                self._image_view.zoom_in()
                return
            if event.keyval == k.minus:
                self._image_view.zoom_out()
                return
            if event.keyval == k._0:
                self._image_view.zoom_to_actual()
                return
            if event.keyval == k.equal:
                self._image_view.zoom_to_fit()
                return
        return False

    def _maybe_cancel_load(self):
        if self._latest_handle is None:
            # Nothing to cancel.
            return
        env.pixbufLoader.cancel_load(self._latest_handle)
        self._latest_handle = None

    def _preload(self, size):
        self._preload_or_unload(size, True)

    def _preload_or_unload(self, size, preload):
        index = self._current_index
        for x in [index + 2, index - 1, index + 1]:
            if self._is_valid_index(x):
                location = self._image_versions[x].getLocation()
                if preload:
                    env.pixbufLoader.preload(location, size)
                else:
                    env.pixbufLoader.unload(location, size)

    def _unload(self, size):
        self._preload_or_unload(size, False)

gobject.type_register(FullScreenWindow) # TODO: Not needed in PyGTK 2.8.
