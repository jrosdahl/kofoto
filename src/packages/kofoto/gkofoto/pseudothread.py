"""This module contains the PseudoThread class."""

__all__ = ["PseudoThread"]

import sys
import gobject

class PseudoThread:
    """A pseudo thread using a GTK idle handler.

    This class provides a simple but powerful emulation of an activity
    that is run in a separate thread of control. That is, no actual
    thread is spawned. Instead, the thread-like behaviour is created
    by letting the GTK main loop call a function when idle. By letting
    the function be a generator object that yields quite often, the
    activity can easily remember its state between calls so that
    long-lived loops can be written without complex state machines.

    There are two ways to specify the activity: by passing a generator
    object ("the target") to the constructor, or by overriding the
    _run() method (which must be a generator) in a subclass.

    Once a PseudoThread instance has been created, its activity must
    be started by calling the start() method. After that, the target's
    next() method will be called repeatedly as long it returns a true
    value. If it returns a false value (or throws an exception), the
    activity is stopped.

    To get a thread-like behaviour, the activity should not do
    anything that takes a long time before returning. If the activity
    needs to sleep, the sleep() method can be called, though.

    Usage examples:

    >>> import pygtk
    >>> pygtk.require("2.0")
    >>> import gtk
    >>> from kofoto.gkofoto.pseudothread import PseudoThread
    >>> def f(x):
    ...     for i in range(5):
    ...         print x, i
    ...         yield True
    >>> pt = PseudoThread(f("a"))
    >>> pt.start()
    >>> pt2 = PseudoThread(f("b"))
    >>> pt2.start()
    >>> gtk.main()
    a 0
    b 0
    a 1
    b 1
    a 2
    b 2
    a 3
    b 3
    a 4
    b 4

    >>> import pygtk
    >>> pygtk.require("2.0")
    >>> import gtk
    >>> from kofoto.gkofoto.pseudothread import PseudoThread
    >>> class C(PseudoThread):
    ...     def _run(self):
    ...         print "sleeping..."
    ...         self.sleep(1000)
    ...         yield True
    ...         print "done."
    >>> pt = C()
    >>> pt.start()
    >>> gtk.main()
    sleeping...
    done.
    """

    def __init__(self, target=None, error_fp=sys.stderr):
        """Constructor.

        Arguments:

        target   -- The generator object to be run. If None, the
                    generator object returned by the _run() method is
                    run instead.
        error_fp -- File object to write tracebacks to.
        """

        self.__idle_tag = None
        self.__timeout_tag = None
        if target is None:
            target = self._run()
        self.__target = target
        self.__error_fp = error_fp

    def sleep(self, ms):
        """Delay execution of the next iteration of the pseudo thread.

        Arguments:

        ms -- Number of milliseconds to sleep.
        """

        if self.__timeout_tag is not None:
            return
        self.stop()
        self.__timeout_tag = gobject.timeout_add(ms, self.__timeout_cb)

    def start(self):
        """Start the pseudo thread."""

        if self.__idle_tag is not None:
            return
        self.__idle_tag = gobject.idle_add(self.__idle_cb)

    def stop(self):
        """Stop the pseudo thread."""

        if self.__idle_tag is None:
            return
        gobject.source_remove(self.__idle_tag)
        self.__idle_tag = None

    def is_running(self):
        """Check whether the pseudo thread is running."""
        return (
            (self.__idle_tag is not None) or
            (self.__timeout_tag is not None))

    def __idle_cb(self):
        try:
            x = self.__target.next()
        except StopIteration:
            x = False
        except:
            import traceback
            traceback.print_exc(file=self.__error_fp)
            x = False
        if x:
            return True
        else:
            self._idle_tag = None
            return False

    def __timeout_cb(self):
        self.__timeout_tag = None
        self.start()

    def _run(self):
        raise Exception("not overridden")
