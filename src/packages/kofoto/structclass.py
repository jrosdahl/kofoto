# pylint: disable-msg=W0232

"""A simple struct-like class."""

__all__ = ["StructClass"]

def makeStructClass(*attributes):
    """Return a simple struct-like instance.

    Example usage:

    >>> S = makeStructClass("a", "b")
    >>> s = S()
    >>> s.a = 42
    >>> s.c = 1
    Traceback (most recent call last):
      File "<stdin>", line 1, in ?
    AttributeError: 'struct' object has no attribute 'c'
    """

    class Struct(object):
        """A struct."""
        __slots__ = attributes
    return Struct
