"""A simple variant record-like class."""

__all__ = ["Alternative"]

try:
    set
except NameError:
    from sets import Set as set

class Alternative:
    """A simple variant record (AKA discriminated union) class
    representing a set of unique identifers. It's sort of an enum,
    except there's no enumeration, i.e. no integers are associated
    with the identifiers and the identifiers have no specific order.

    Example usage:

    >>> from alternative import Alternative
    >>> options = Alternative("Yes", "Maybe", "No")
    >>> options
    Alternative('Maybe', 'Yes', 'No')
    >>> x = options.Yes
    >>> x
    <alternative.AlternativeInstance instance at 0x4022b50c>
    >>> print x
    Yes
    >>> x in options
    True
    >>> "Yes" in options
    False
    >>> def f(x):
    ...     assert x in options
    ...     if x == options.Yes:
    ...         print "OK!"
    ...     elif x == options.Maybe:
    ...         print "Hmm?"
    ...     elif x == options.No:
    ...         print "Right."
    ...
    >>> f(options.Yes)
    OK!
    >>> options2 = Alternative("Yes")
    >>> f(options2.Yes)
    Traceback (most recent call last):
      File "<stdin>", line 1, in ?
      File "<stdin>", line 2, in f
    AssertionError
    """

    def __init__(self, *identifiers):
        self.__identifiers = set()
        for x in identifiers:
            ai = AlternativeInstance(x)
            setattr(self, x, ai)
            self.__identifiers.add(ai)

    def __repr__(self):
        return "Alternative(%s)" % ", ".join(
            [repr(str(x)) for x in self.__identifiers])

    def __contains__(self, x):
        return x in self.__identifiers

class AlternativeInstance:
    def __init__(self, identifier):
        self.__identifier = identifier

    def __str__(self):
        return self.__identifier
