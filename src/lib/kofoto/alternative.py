"""A simple variant record-like class."""

__all__ = ["Alternative"]

from sets import Set

class Alternative:
    """A simple variant record (AKA discriminated union) class
    representing a set of unique identifers. It's sort of like an
    enum, except there's no enumeration, i.e. no integers are
    associated with the identifiers.

    Example usage:

    >>> a = Alternative("Foo", "Bar", "Gazonk")
    >>> print a
    Alternative('Bar', 'Gazonk', 'Foo')
    >>> x = a.Foo
    >>> print x
    Foo
    >>> x in a
    True
    >>> "Foo" in a
    False
    """

    def __init__(self, *identifiers):
        self.__identifiers = Set()
        for x in identifiers:
            ei = _EnumInstance(x)
            setattr(self, x, ei)
            self.__identifiers.add(ei)

    def __repr__(self):
        return "Alternative(%s)" % ", ".join(
            ["'" + str(x) + "'" for x in self.__identifiers])

    def __contains__(self, x):
        return x in self.__identifiers

class _EnumInstance:
    def __init__(self, identifier):
        self.__name = identifier

    def __str__(self):
        return self.__name
