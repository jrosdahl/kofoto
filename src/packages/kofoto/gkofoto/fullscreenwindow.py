"""This module contains the FullScreenWindow class."""

__all__ = ["FullScreenWindow"]

import gtk
import gobject
import re
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
        self._selected_category = None

        bg_color = gtk.gdk.color_parse("#000000")
        fg_color = gtk.gdk.color_parse("#999999")

        eventbox = gtk.EventBox()
        vbox = gtk.VBox()
        eventbox.add(vbox)

        # Add the image widget.
        self._image_view = ImageView()
        self._image_view.set_error_pixbuf(
            gtk.gdk.pixbuf_new_from_file(env.unknownImageIconFileName))
        self._image_view.modify_bg(gtk.STATE_NORMAL, bg_color)
        vbox.pack_start(self._image_view)

        # Add informative label.
        self._info_label = gtk.Label()
        self._info_label.set_text(
            "No more images.\nPress escape to get back to GKofoto.")
        self._info_label.set_justify(gtk.JUSTIFY_CENTER)
        self._info_label.modify_fg(gtk.STATE_NORMAL, fg_color)
        vbox.pack_start(self._info_label)

        # Add category entry.
        self._category_hbox = gtk.HBox()
        self._category_hbox.set_spacing(5)
        vbox.pack_start(self._category_hbox, False)
        label = gtk.Label("Category:")
        label.modify_fg(gtk.STATE_NORMAL, fg_color)
        self._category_hbox.pack_start(label, False)
        self._category_entry = gtk.Entry()
        self._category_entry.connect(
            "activate", self._category_entry_activate_cb)
        self._category_entry.connect(
            "changed", self._category_entry_changed_cb)
        self._category_hbox.pack_start(self._category_entry, False)
        self._category_indicator_image = gtk.Image()
        self._category_indicator_image.set_from_stock(
            gtk.STOCK_CANCEL, gtk.ICON_SIZE_MENU)
        self._category_hbox.pack_start(self._category_indicator_image, False)
        self._category_info_label = gtk.Label()
        self._category_info_label.set_line_wrap(True)
        self._category_info_label.modify_fg(gtk.STATE_NORMAL, fg_color)
        self._category_hbox.pack_start(self._category_info_label, True, True)

        self.modify_bg(gtk.STATE_NORMAL, bg_color)
        eventbox.modify_bg(gtk.STATE_NORMAL, bg_color)
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

    def _category_entry_activate_cb(self, widget):
        if self._selected_category is not None:
            image = self._image_versions[self._current_index].getImage()
            if self._selected_category in image.getCategories():
                image.removeCategory(self._selected_category)
            else:
                image.addCategory(self._selected_category)
            self._category_hbox.hide_all()
            self._category_entry.set_text("")
            # self._selected_category is set to None implicitly by set_text.

    def _category_entry_changed_cb(self, widget):
        text = self._category_entry.get_text().decode("utf-8")
        regexp = re.compile(".*%s.*" % re.escape(text.lower()))
        if text != "":
            categories = list(env.shelf.getMatchingCategories(regexp))
        else:
            categories = []
        exact_match = None
        for category in categories:
            if category.getTag().lower() == text.lower() \
                   or category.getDescription().lower() == text.lower():
                exact_match = category
                break
        if len(categories) == 1 or exact_match is not None:
            image_stock_id = gtk.STOCK_OK
            if len(categories) == 1:
                self._selected_category = categories[0]
            else:
                self._selected_category = exact_match
            current_image = \
                self._image_versions[self._current_index].getImage()
            image_categories = current_image.getCategories()
            category_set = self._selected_category in image_categories
            self._category_info_label.set_markup(
                u"Press enter to <b>%s</b> category <b>%s</b> [<b>%s</b>]" % (
                    ["set", "unset"][category_set],
                    self._selected_category.getDescription(),
                    self._selected_category.getTag()))
        else:
            image_stock_id = gtk.STOCK_CANCEL
            self._selected_category = None
            self._category_info_label.set_text("No matching category")
        self._category_indicator_image.set_from_stock(
            image_stock_id, gtk.ICON_SIZE_MENU)

    def _display_end_screen(self):
        self._maybe_cancel_load()
        self._image_view.hide()
        self._info_label.show()
        self._category_hbox.hide_all()

    def _display_image(self):
        self._image_view.set_image(self._get_image_async_cb)
        self._image_view.show()
        self._info_label.hide()
        self._category_hbox.hide_all()

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
            self._display_image()

    def _hide_cursor(self):
        pixmap = gtk.gdk.Pixmap(None, 1, 1, 1)
        color = gtk.gdk.Color()
        invisible_cursor = gtk.gdk.Cursor(pixmap, pixmap, color, color, 0, 0)
        self.window.set_cursor(invisible_cursor)

    def _is_valid_index(self, index):
        return 0 <= index < len(self._image_versions)

    def _key_press_event_cb(self, unused, event):
        # GIMP: 1 --> 100%, C-S-e --> fit
        # EOG: [1,C-0,C-1] --> 100%
        # f-spot: [0,1,C-0,C-1] --> fit

        k = gtk.keysyms
        CTRL = gtk.gdk.CONTROL_MASK
        e = (event.keyval, event.state & CTRL)
        if self._category_hbox.props.visible:
            # Showing category entry -- disable bindings except escape.
            if e in [(k.Escape, 0), (k.t, CTRL)]:
                self._toggle_category_field()
                return True
            else:
                return False
        if e in [(k.space, 0), (k.Right, 0), (k.Down, 0), (k.Page_Down, 0)]:
            self._goto(self._current_index + 1)
            return True
        if e in [(k.BackSpace, 0), (k.Left, 0), (k.Up, 0), (k.Page_Up, 0)]:
            self._goto(self._current_index - 1)
            return True
        if e == (k.Home, 0):
            self._goto(0)
            return True
        if e == (k.End, 0):
            self._goto(len(self._image_versions) - 1)
            return True
        if e == (k.Escape, 0):
            self.destroy()
            return True
        if e == (k.plus, 0):
            self._image_view.zoom_in()
            return True
        if e == (k.minus, 0):
            self._image_view.zoom_out()
            return True
        if e == (k._1, 0):
            self._image_view.zoom_to_actual()
            return True
        if e in [(k.equal, 0), (k._0, 0)]:
            self._image_view.zoom_to_fit()
            return True
        if e == (k.t, CTRL):
            self._toggle_category_field()
            return True
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

    def _toggle_category_field(self):
        if not self._image_view.props.visible:
            # Display end screen.
            return
        if self._category_hbox.props.visible:
            self._category_hbox.hide_all()
        else:
            self._category_hbox.show_all()
            self._category_entry.grab_focus()

    def _unload(self, size):
        self._preload_or_unload(size, False)

gobject.type_register(FullScreenWindow) # TODO: Not needed in PyGTK 2.8.
