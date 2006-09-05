"""This module contains the CachingPixbufLoader class."""

__all__ = ["CachingPixbufLoader"]

import gc
import os
import time
from sets import Set as set
if __name__ == "__main__":
    import pygtk
    pygtk.require("2.0")
import gobject
from kofoto.common import UnimplementedError
from kofoto.gkofoto.pixbufloader import PixbufLoader, get_pixbuf_size
from kofoto.gkofoto.pseudothread import PseudoThread
from kofoto.iodict import InsertionOrderedDict
from kofoto.rectangle import Rectangle

class _RequestStateBase(object):
    def __init__(self, request):
        self._request = request

    def add_callback(self, load_callback, error_callback):
        self._request._callbacks.append((load_callback, error_callback))

    def get_number_of_loaded_pixels(self):
        if self._request._loaded_bytes == 0:
            return 0
        else:
            return (
                float(self._request._size_to_load[0]) *
                self._request._size_to_load[1] *
                self._request._loaded_bytes /
                self._request._available_bytes)

    def is_finished(self):
        raise UnimplementedError

    def load_some_more(self):
        return 0

class _RequestStateInitial(_RequestStateBase):
    def get_number_of_loaded_pixels(self):
        return 0

    def is_finished(self):
        return False

    def load_some_more(self):
        req = self._request
        try:
            stat = os.stat(req._path)
            # TODO: Look for image in diskcache here and load the
            # cached image instead (if cached image mtime <= original
            # image mtime?).
        except OSError:
            req._state = _RequestStateError(req)
        else:
            req._mtime = stat.st_mtime
            req._available_bytes = stat.st_size
            req._state = _RequestStateWaitingForSize(req)
            req._pb_loader.prepare(req._path, req._size_limit)
        return 0

class _RequestStateWaitingForSize(_RequestStateBase):
    def get_number_of_loaded_pixels(self):
        return 0

    def is_finished(self):
        return False

    def load_some_more(self):
        req = self._request
        req._unreported_bytes += req._pb_loader.load_some_more()
        original_size = req._pb_loader.get_original_size()
        if original_size is not None:
            req._state = _RequestStateLoading(req)
            req._original_size = original_size
            if req._size_limit is None:
                req._size_to_load = original_size
            else:
                req._size_to_load = Rectangle(*original_size).downscaled_to(
                    req._size_limit)
        return 0

class _RequestStateLoading(_RequestStateBase):
    def is_finished(self):
        return False

    def load_some_more(self):
        req = self._request
        loaded_bytes = req._pb_loader.load_some_more()
        if req._unreported_bytes > 0:
            loaded_bytes += req._unreported_bytes
            req._unreported_bytes = 0
        req._loaded_bytes += loaded_bytes
        if loaded_bytes == 0:
            # Here it would be possible to check mtime again and
            # reload the image if mtime has changed. We decided to
            # ignore this right now because of implementation
            # difficulties (for example, a negative number of pixels
            # (watch out so it isn't 0!) must be reported back to
            # req._cpb_loader in some way).

            req._pixbuf = req._pb_loader.get_pixbuf()
            if req._pixbuf is None:
                req._state = _RequestStateError(req)
            else:
                req._state = _RequestStateFinished(req)
        return (
            (float(loaded_bytes) / req._available_bytes) *
            req._size_to_load[0] * req._size_to_load[1])

class _RequestStateFinished(_RequestStateBase):
    def __init__(self, request):
        _RequestStateBase.__init__(self, request)
        for (load_cb, _) in request._callbacks:
            if request._cpb_loader._debug_level > 0:
                print "%.3f callback(%s, %s)" % (
                    time.time(), request._path, request._size_limit)
            load_cb(request._pixbuf, request._original_size)
        request._callbacks = []
        # TODO: Store in disk cache here if
        # self._request._persistence_size_limit isn't None and we
        # didn't load the image from the cache.

    def add_callback(self, load_callback, _):
        req = self._request
        if req._cpb_loader._debug_level > 0:
            print "%.3f callback(%s, %s)" % (
                time.time(), req._path, req._size_limit)
        load_callback(req._pixbuf, req._original_size)

    def is_finished(self):
        return True

class _RequestStateError(_RequestStateBase):
    def __init__(self, request):
        _RequestStateBase.__init__(self, request)
        request._pb_loader.cancel()
        request._pixbuf = None
        for (_, error_cb) in request._callbacks:
            if error_cb is not None:
                error_cb()
        request._callbacks = []

        # Don't cache negative requests since we can't be sure that it
        # will fail in the future. The image may for example be partly
        # written now but fully written soon.
        key = (request._path, request._size_limit)
        request._cpb_loader._remove_erroneous_request(key)

    def add_callback(self, _, error_callback):
        error_callback()

    def is_finished(self):
        return True

class _Request(object):
    def __init__(self, cpb_loader, path, size_limit, persistence_size_limit):
        self._cpb_loader = cpb_loader
        self._path = path
        self._size_limit = size_limit
        self._persistence_size_limit = persistence_size_limit
        self._callbacks = [] # List of (load_callback, error_callback).
        self._pixbuf = None
        self._unreported_bytes = 0
        self._loaded_bytes = 0
        self._available_bytes = None
        self._original_size = None
        self._size_to_load = None
        self._mtime = None
        self._pb_loader = PixbufLoader()
        self._state = _RequestStateInitial(self)

    # ----------------------------------

    def get_key(self):
        return (self._path, self._size_limit)
    key = property(get_key)

    # ----------------------------------

    def add_callback(self, load_callback, error_callback):
        return self._state.add_callback(load_callback, error_callback)

    def cancel(self):
        self._pb_loader.cancel()
        del self._state # Break cycle.

    def get_number_of_loaded_pixels(self):
        return self._state.get_number_of_loaded_pixels()

    def has_changed_on_disk(self):
        if self._mtime is None:
            # We don't know yet.
            return False
        else:
            try:
                return os.path.getmtime(self._path) != self._mtime
            except OSError:
                return True

    def is_finished(self):
        return self._state.is_finished()

    def load_some_more(self):
        return self._state.load_some_more()

    def remove_callback(self, load_callback, error_callback):
        try:
            self._callbacks.remove((load_callback, error_callback))
        except ValueError:
            pass

    def _print_state(self, verbose):
        print "        state:                 ", self._state.__class__.__name__
        print "        path:                  ", self._path
        print "        size limit:            ", self._size_limit
        print "        persistence size limit:", self._persistence_size_limit
        if verbose:
            print "        callbacks:             ", self._callbacks
            print "        pixbuf:                ", self._pixbuf
            print "        unreported bytes:      ", self._unreported_bytes
            print "        loaded bytes:          ", self._loaded_bytes
            print "        available bytes:       ", self._available_bytes
            print "        original size:         ", self._original_size
            print "        size to load:          ", self._size_to_load
            print "        mtime:                 ", self._mtime
            print "        pb loader:             ", self._pb_loader

class CachingPixbufLoader(object):
    """A pixbuf loader with preload and cache functionality.

    This class is a pixbuf loader that keeps loaded pixbufs in an LRU
    memory cache. It handles several outstanding pixbuf load requests
    and also handles preload requests. It can optionally store pixbufs
    in a disk-based cache. Currently, all pixbufs are stored as JPEGs.

    Load requests are asynchronous; the request is done by supplying
    the path to the image, a wanted pixbuf size and a callback
    function to the load() method. The callback function is called
    when the load has finished (or immediately, if the pixbuf already
    exists in the cache). Old load requests have higher priority than
    new. Load requests have higher priority than preload requests. 
    Load requests are never forgotten.

    Preload requests are also asynchronous. A preload request is used
    to hint the loader to load a pixbuf into the cache. New preload
    requests have higher priority than old. Load requests have higher
    priority than preload requests. Old preload requests may be
    ignored (and the cached pixbuf thrown away) if the cache limits
    are exceeded.
    """

    def __init__(self, pixel_limit=10**7, cache_directory=None):
        """Constructor.

        Arguments:

        pixel_limit  -- The number of pixels to keep in the memory
                        cache.
        cache_directory
                     -- Path to the disk cache directory. If None, no
                        images will be cached on disk.
        """

        self._pixel_limit = pixel_limit
        self._cache_directory = cache_directory
        self._load_thread = PseudoThread(self._load_loop())
        self._debug_level = 0

        # Cached value of the sum of loaded pixels of all requests in
        # the queue.
        self._pixels_in_cache = 0.0

        # Whether the load loop should reevaluate which request to
        # work on.
        self._load_loop_reeval = False

        # Maps path to Rectangle(full_width, full_height).
        self._available_size = {}

        # Maps (path, (width_limit, height_limit)) to _Request
        # instances. Newest requests are first and oldest are last.
        self._request_queue = InsertionOrderedDict()

        # List of _Request instances. Always a subset of
        # self._request_queue.values() (except order). Newest requests
        # are last and oldest are first.
        self._load_queue = []

        # Maps path to set(_Request)
        self._path_to_requests = {}

    def cancel_load(self, handle):
        """Cancel a load.

        This method does not remove the cached pixbuf from the cache,
        it just makes sure that the callback passed to load doesn't
        get called. In other words, cancel_load converts a load to a
        preload.

        If the handle represents a load that already has finished,
        nothing will happen and no exception will be raised.
        """
        if self._debug_level > 0:
            print "%.3f cancel_load(%r)" % (time.time(), handle)

        (path, size_limit, load_callback, error_callback) = handle
        key = (path, size_limit)
        if key in self._request_queue:
            request = self._request_queue[key]
            try:
                self._load_queue.remove(request)
            except ValueError:
                # Nothing to do.
                return
            request.remove_callback(load_callback, error_callback)
            self._load_loop_reeval = True

    def get_pixel_limit(self):
        """Get cache size limit."""

        return self._pixel_limit

    def load(self, path, size_limit, load_callback,
             error_callback=None, persistence_size_limit=None):
        """Load a pixbuf as quick as possible.

        The pixbuf is taken from the cache if possible.

        Old load requests have higher priority than new. Load requests
        have higher priority than preload requests.

        Arguments:

        path         -- Path to the image file to load.
        size_limit   -- A tuple (width, height) with the size limit of
                        the resulting pixbuf, or None. If None, a
                        full-size pixbuf will be loaded.
        load_callback
                     -- Function to call when loading has finished.
                        The function will be passed two arguments: the
                        resulting pixbuf and a tuple (width, height)
                        with the full size of the image file on disk.
        error_callback
                     -- Function to call when loading has failed. If
                        None, no call will be made and the error will
                        be ignored. The function will be given no
                        arguments.
        persistence_size_limit
                     -- Limit (an integer) of the image stored in the
                        disk cache (if disk caching is enabled). Must
                        be None if size_limit is None. Must be equal
                        to or greater than max(size_limit[0],
                        size_limit[1]). If None, the disk cache will
                        not be used.

        The method returns a handle that can be passed to cancel_load.
        """
        if self._debug_level > 0:
            print "%.3f load(%s, %s)" % (time.time(), path, size_limit)

        if size_limit is not None:
            size_limit = tuple(size_limit)
            if persistence_size_limit is not None:
                assert persistence_size_limit >= size_limit[0]
                assert persistence_size_limit >= size_limit[1]
            size_limit = self._calculate_size_limit(path, size_limit)
        key = (path, size_limit)
        request = self._request_queue.get(key)
        if request and request.has_changed_on_disk():
            self._remove_request(key)
        if key in self._request_queue:
            # Just move it to the front.
            request = self._request_queue[key]
            self._request_queue.insert_first(key, request)
        else:
            # Let preload create the request.
            self.preload(path, size_limit, persistence_size_limit)
            request = self._request_queue[key]
        if request not in self._load_queue:
            self._load_queue.append(request)
            self._load_loop_reeval = True

        # It's okay to wait until now to add the callback, since any
        # errors that will trigger error_callback will arise later (at
        # the first load_some_more in the load loop).
        request.add_callback(load_callback, error_callback)

        self._load_thread.start()
        handle = (
            path, size_limit, load_callback, error_callback)
        return handle

    def preload(self, path, size_limit, persistence_size_limit=None):
        """Request that a pixbuf should be loaded into the cache.

        The pixbuf can be retrieved by a call to load().

        New preload requests have higher priority than old. Load
        requests have higher priority than preload requests.

        Arguments:

        path         -- Path to the image file to load.
        size_limit   -- A tuple (width, height) with the size limit of the
                        resulting pixbuf, or None. If None, a
                        full-size pixbuf will be loaded.
        persistence_size_limit
                     -- Limit (an integer) of the image stored in the
                        disk cache (if disk caching is enabled). Must
                        be None if size_limit is None. Must be equal
                        to or greater than max(size_limit[0],
                        size_limit[1]). If None, the disk cache will
                        not be used.
        """

        if self._debug_level > 0:
            print "%.3f preload(%s, %s)" % (time.time(), path, size_limit)

        if size_limit is not None:
            size_limit = tuple(size_limit)
            if persistence_size_limit is not None:
                assert persistence_size_limit >= size_limit[0]
                assert persistence_size_limit >= size_limit[1]
            size_limit = self._calculate_size_limit(path, size_limit)
        key = (path, size_limit)
        if key in self._request_queue:
            request = self._request_queue[key]
        else:
            request = _Request(self, path, size_limit, persistence_size_limit)
            request_set = self._path_to_requests.setdefault(path, set())
            request_set.add(request)
        self._request_queue.insert_first(key, request)
        self._load_loop_reeval = True
        self._load_thread.start()

    def set_pixel_limit(self, pixel_limit):
        """Set cache size limit.

        Arguments:

        pixel_limit -- The number of pixels to keep in the cache.
        """

        self._pixel_limit = pixel_limit
        self._prune_queue()

    def unload(self, path, size_limit):
        """Remove a cached pixbuf from the cache.

        This method is a hint to the cache that it's not interesting
        to keep a cached pixbuf anymore. If no pixbuf for the given
        path and size limit exists, nothing will happen.

        Arguments:

        path         -- Path given to load/preload.
        size_limit   -- Size limit given to load/preload.
        """

        if self._debug_level > 0:
            print "%.3f unload(%s, %s)" % (time.time(), path, size_limit)

        key = (path, size_limit)
        if key in self._request_queue:
            request = self._request_queue[key]
            if request not in self._load_queue:
                self._remove_request(key)

    def unload_all(self, path):
        """Remove all cached sizes of a pixbuf from the cache.

        This method is a hint to the cache that it's not interesting
        to keep a cached pixbuf anymore. If no pixbufs for the given
        path exist, nothing will happen.

        Arguments:

        path         -- Path given to load/preload.
        """

        if self._debug_level > 0:
            print "%.3f unload_all(%s)" % (time.time(), path)

        if path not in self._path_to_requests:
            return
        for request in self._path_to_requests[path].copy():
            if request not in self._load_queue:
                self._remove_request(request.key)

    def _calculate_size_limit(self, path, size_limit):
        if size_limit is None:
            return None
        else:
            available_size = self._available_size.get(path)
            if available_size is None:
                size = get_pixbuf_size(path)
                if size is None:
                    # Error reading image size.
                    return None
                available_size = Rectangle(*size)
                self._available_size[path] = available_size
            if available_size.fits_within(size_limit):
                return None
            else:
                return size_limit

    def _load_loop(self):
        while True:
            request = None
            self._load_loop_reeval = False
            found_a_load = False
            while len(self._load_queue) > 0:
                if self._load_queue[0].is_finished():
                    # The load request has finished, so remove it.
                    del self._load_queue[0]
                else:
                    request = self._load_queue[0]
                    found_a_load = True
                    break
            if request is None:
                # No loads. Find a preload, if any.
                for req in self._request_queue.itervalues():
                    if not req.is_finished():
                        request = req
                        break
            if request is None:
                # The request queue needs to be pruned now since there
                # may be old load requests that now are finished but
                # could not be removed before.
                self._prune_queue()

                # No loads or preloads left. Pause until
                # self._load_thread.start() is called.
                if self._debug_level > 1:
                    print
                    print "LOAD LOOP FINISHED:"
                    self._print_state(False)
                self._load_thread.stop()
                yield True
            else:
                if self._debug_level > 1:
                    print "LOAD LOOP SELECTED TO LOAD", request._path
                if found_a_load:
                    priority = gobject.PRIORITY_HIGH_IDLE
                else:
                    priority = gobject.PRIORITY_DEFAULT_IDLE
                self._load_thread.set_priority(priority)
                while not (self._load_loop_reeval or request.is_finished()):
                    loaded_pixels = request.load_some_more()
                    self._pixels_in_cache += loaded_pixels
                    self._prune_queue()
                    yield True
            # Now it's time to reevaluate which request to work on.

    def _print_state(self, verbose=False):
        print "------------------------------------------------------------------"
        print "Pixel limit:", self._pixel_limit
        print "Cache directory:", self._cache_directory
        print "Pixels in cache:", self._pixels_in_cache
        print "Request queue:"
        for (key, request) in self._request_queue.iteritems():
            print "    Key:", key
            print "    Request:"
            request._print_state(verbose)
        print "Load queue:"
        for request in self._load_queue:
            print "    Request:"
            request._print_state(verbose)
        print "Path to requests:"
        for (path, requests) in self._path_to_requests.iteritems():
            print "    Path:", path
            print "    Requests:", requests

    def _prune_queue(self):
        if self._pixels_in_cache <= self._pixel_limit:
            return
        requests_to_prune = []
        load_requests = set(self._load_queue)
        pixels_after_pruning = self._pixels_in_cache
        for (key, request) in self._request_queue.reviteritems():
            if pixels_after_pruning <= self._pixel_limit:
                # Enough pruning.
                break
            if request not in load_requests:
                requests_to_prune.append((key, request))
                pixels_after_pruning -= request.get_number_of_loaded_pixels()
        if len(requests_to_prune) > 0:
            self._load_loop_reeval = True
            for (key, request) in requests_to_prune:
                if self._debug_level > 1:
                    print "PRUNING", key
                self._remove_request(key)
            gc.collect()

    def _remove_erroneous_request(self, key):
        self._remove_request(key)

    def _remove_request(self, key):
        assert key in self._request_queue
        request = self._request_queue[key]
        self._pixels_in_cache -= request.get_number_of_loaded_pixels()
        request.cancel()
        try:
            self._load_queue.remove(request)
        except ValueError:
            # OK, it wasn't a load.
            pass
        del self._request_queue[key]
        path = key[0]
        request_set = self._path_to_requests[path]
        request_set.remove(request)
        if len(request_set) == 0:
            del self._path_to_requests[path]

######################################################################

def main(argv):
    import gtk

    def pixbuf_loaded_cb(pixbuf, full_size):
        print "Received pixbuf of %dx%d pixels (full size: %dx%d)." % (
            pixbuf.get_width(), pixbuf.get_height(), full_size[0], full_size[1])
    def pixbuf_error_cb():
        print "Error while loading pixbuf."

    loader = CachingPixbufLoader()
    loader._debug_level = 2
    loader.set_pixel_limit(10000000000)
    print "INITIAL:"
    loader._print_state(False)

    for path in argv[1:]:
        loader.load(path, (300, 200), pixbuf_loaded_cb, pixbuf_error_cb)

    print
    print "BEFORE LOAD LOOP START:"
    loader._print_state(False)

    gtk.main()

if __name__ == "__main__":
    import sys
    main(sys.argv)
