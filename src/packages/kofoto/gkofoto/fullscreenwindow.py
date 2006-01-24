# pylint: disable-msg=F0203, E0201

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

        self._image_versions = image_versions
        self._current_index = current_index
        self._latest_handle = None
        self._latest_key = None

        self.connect("key_press_event", self._key_pressed_cb)
        self._image_view = ImageView()
        bg_color = gtk.gdk.color_parse("#000000")
        self._image_view.modify_bg(gtk.STATE_NORMAL, bg_color)
        self.add(self._image_view)
        self.set_modal(True)
        self.set_default_size(400, 400)
        self.fullscreen()
        self.connect_after("map-event", self._hide_cursor)
        self._goto()

    def destroy(self):
        """Destroy the widget."""

        if self._latest_handle is not None:
            env.pixbufLoader.cancel_load(self._latest_handle)
        gtk.Window.destroy(self)

    def next(self, *unused):
        """Show next image."""

        self._goto(1)

    def previous(self, *unused):
        """Show previous image."""

        self._goto(-1)

    # ----------------------------------------

    def _get_image_async_cb(self, size):
        path = self._image_versions[self._current_index].getLocation()
        if self._latest_handle is not None:
            env.pixbufLoader.cancel_load(self._latest_handle)
            if path == self._latest_key[0]:
                env.pixbufLoader.unload(*self._latest_key)
        self._latest_handle = env.pixbufLoader.load(
            path,
            size,
            self._image_view.set_from_pixbuf,
            self._image_view.set_error)
        self._latest_key = (path, size)

    def _goto(self, direction = 0):
        new_index = self._current_index + direction
        if self._is_valid_index(new_index):
            self._current_index = new_index
            self._preload()
            self._image_view.set_image(self._get_image_async_cb)

    def _hide_cursor(self, *unused):
        pix_data = """/* XPM */
            static char * invisible_xpm[] = {
            "1 1 1 1",
            "       c None",
            " "};
            """
        color = gtk.gdk.Color()
        pix = gtk.gdk.pixmap_create_from_data(
            None, pix_data, 1, 1, 1, color, color)
        invisible_cursor = gtk.gdk.Cursor(pix, pix, color, color, 0, 0)
        self.window.set_cursor(invisible_cursor)

    def _is_valid_index(self, index):
        return 0 <= index < len(self._image_versions)

    def _key_pressed_cb(self, unused, event):
        if event.keyval == gtk.gdk.keyval_from_name("space"):
            self.next()
            return True
        if event.keyval == gtk.gdk.keyval_from_name("BackSpace"):
            self.previous()
            return True
        if event.keyval == gtk.gdk.keyval_from_name("Right"):
            self.next()
            return True
        if event.keyval == gtk.gdk.keyval_from_name("Left"):
            self.previous()
            return True
        if event.keyval == 65366: # PageDown
            self.next()
            return True
        if event.keyval == 65365: # PageUp
            self.previous()
            return True
        if event.keyval == gtk.gdk.keyval_from_name("Escape"):
            self.destroy()
            return True
        return False

    def _preload(self):
        index = self._current_index
        size = self._image_view.get_wanted_image_size()
        for x in [index + 2, index - 1, index + 1]:
            if self._is_valid_index(x):
                filename = self._image_versions[x].getLocation()
                env.pixbufLoader.preload(filename, size)

gobject.type_register(FullScreenWindow) # TODO: Not needed in PyGTK 2.8.
