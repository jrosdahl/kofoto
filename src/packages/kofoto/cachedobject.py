"""Implementation of the CachedObject class."""

__all__ = ["CachedObject"]

class CachedObject:
    """A class for keeping track of a cached object.

    This class keeps knowledge about how to create an object. The
    object is created only when needed (when the get method is
    called). The same object is returned for successive calls to get,
    unless the invalidate has been called.
    """

    def __init__(self, constructor, args=()):
        """Constructor.

        Arguments:

        constructor -- Function to call to create the object.
        args        -- Arguments to pass to the constructor function.
        """
        self.__constructor = constructor
        self.__args = args
        self.__object = None
        self.__created = False

    def get(self):
        """Create (if needed) and get the cached object."""

        if not self.__created:
            self.__object = self.__constructor(*self.__args)
        return self.__object

    def invalidate(self):
        """Invalidate the cached object.

        The object will be recreated in the next call to get.
        """

        if self.__created:
            self.__object = None
