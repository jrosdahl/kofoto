"""This module contains the PixbufLoader class."""

__all__ = ["PixbufLoader"]

if __name__ == "__main__":
    import pygtk
    pygtk.require("2.0")
import gtk
import gobject
from kofoto.rectangle import Rectangle

def get_pixbuf_size(path):
    """Get size of image at a given path.

    Returns (width, height) or None on error.
    """

    pbl = PixbufLoader()
    pbl.prepare(path, None)
    while True:
        loaded_bytes = pbl.load_some_more()
        size = pbl.get_original_size()
        if size is not None or loaded_bytes == 0:
            break
    pbl.cancel()
    return size

class PixbufLoader:
    """A pixbuf loader.

    This class is a simple convenience wrapper around
    gtk.gdk.PixbufLoader.
    """

    def __init__(self):
        """Constructor."""

        self._pixbuf_loader = None
        self._pixbuf = None
        self._original_size = None
        self._size_limit = None
        self._fp = None
        self._loading_finished = False

    def cancel(self):
        """Cancel loading."""

        self._clean_up()

    def get_original_size(self):
        """Get the on-disk size.

        Returns a tuple (width, height) if known, otherwise None.
        """

        return self._original_size

    def get_pixbuf(self):
        """Get the pixbuf.

        Returns the pixbuf if loading has finished successfully,
        otherwise None.
        """

        return self._pixbuf

    def load_some_more(self):
        """Load some more of the pixbuf.

        Call this function until it returns 0.

        Returns the number of loaded bytes.
        """

        if self._loading_finished:
            return 0
        try:
            data = self._fp.read(32768)
            if data:
                self._pixbuf_loader.write(data)
                return len(data)
            else:
                try:
                    self._pixbuf_loader.close()
                    self._pixbuf = self._pixbuf_loader.get_pixbuf()
                finally:
                    # The loader has already been closed, so make sure
                    # that it isn't closed again in _clean_up().
                    self._pixbuf_loader = None
        except (IOError, gobject.GError):
            self._pixbuf = None
            self._original_size = None
        self._clean_up()
        self._loading_finished = True
        return 0

    def prepare(self, path, limit):
        """Prepare loading of an image into a pixbuf.

        Call the load_some_more() method until it returns 0 to load
        the pixbuf.

        Arguments:

        path         -- A path to the image.
        limit        -- A tuple (width, height) with the size limit of
                        the resulting pixbuf, or None. If None, a
                        full-size pixbuf will be loaded.
        """

        if limit is not None:
            # Avoid GTK bug triggered in self._pixbuf_loader.close() when
            # using small image sizes:
            limit = (max(limit[0], 30), max(limit[1], 30))
        self._clean_up()
        self._pixbuf = None
        self._original_size = None
        try:
            self._fp = open(path, "rb")
        except IOError:
            self._loading_finished = True
            return
        self._loading_finished = False
        self._size_limit = limit
        self._pixbuf_loader = gtk.gdk.PixbufLoader()
        self._pixbuf_loader.connect("size-prepared", self._size_prepared_cb)

    def _clean_up(self):
        if self._pixbuf_loader:
            try:
                self._pixbuf_loader.close()
            except gobject.GError:
                pass
        self._pixbuf_loader = None
        if self._fp:
            self._fp.close()
            self._fp = None

    def _size_prepared_cb(self, pbloader, full_width, full_height):
        self._original_size = (full_width, full_height)
        if self._size_limit is None:
            # Load full-sized image.
            return
        size = Rectangle(full_width, full_height).downscaled_to(
            Rectangle(*self._size_limit))
        self._pixbuf_loader.set_size(size.width, size.height)

######################################################################

if __name__ == "__main__":
    import sys

    loader = PixbufLoader()
    loader.prepare(sys.argv[1], (300, 200))
    while loader.load_some_more() > 0:
        pass
    pixbuf = loader.get_pixbuf()
    if pixbuf:
        (owidth, oheight) = loader.get_original_size()
        print "Loaded %dx%d pixbuf (original size: %dx%d)" % (
            pixbuf.get_width(), pixbuf.get_height(), owidth, oheight)
    else:
        print "Error while loading pixbuf."
    gtk.main()
