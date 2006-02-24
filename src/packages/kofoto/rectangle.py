"""
This module contains the Rectangle class.
"""

class Rectangle:
    """A class representing a rectangle with width and height.

    The width and height are available as instance properties r.width
    and r.height for an instance r, and also as r[0] and r[1]. The
    rectangle can thus be cast to a (width, height) tuple with
    tuple(r).

    Other operations that are available are:

    r1 == r2
    r1 != r2
    r1 * n   (where n is an integer)
    n * r1   (where n is an integer)
    r1 / n   (where n is an integer)
    r1 // n  (where n is an integer)
    hash(r1)
    r.copy()
    r1.downscaled_to(r2)
    r1.fits_within(r2)
    r.max()
    r.min()
    r1.rescaled_to(r2)
    """

    def __init__(self, width, height):
        """Constructor.

        Arguments:

        width        -- The width.
        height       -- The height.
        """

        self._width = width
        self._height = height

    # ----------------------------------

    def __div__(self, factor):
        return self.__class__(self._width / factor, self._height / factor)

    def __eq__(self, other):
        try:
            return self._width == other[0] and self._height == other[1]
        except (TypeError, IndexError):
            return False

    def __ne__(self, other):
        return not (self == other)

    def __floordiv__(self, factor):
        return self.__class__(self._width // factor, self._height // factor)

    def __getitem__(self, item):
        if item == 0:
            return self._width
        elif item == 1:
            return self._height
        else:
            raise IndexError

    def __hash__(self):
        return hash((self._width, self._height))

    def __len__(self):
        return 2

    def __mul__(self, factor):
        return self.__class__(self._width * factor, self._height * factor)

    def __repr__(self):
        return "Rectangle(%r, %r)" % (self._width, self._height)

    def __rmul__(self, factor):
        return self * factor

    # ----------------------------------

    def get_width(self):
        return self._width
    width = property(get_width)

    def get_height(self):
        return self._height
    height = property(get_height)

    # ----------------------------------

    def copy(self):
        """Get a copy of the rectangle."""

        return self.__class__(self._width, self._height)

    def downscaled_to(self, limit):
        """Scale the rectangle down to fit within a given limit.

        Returns the downscaled rectangle.
        """

        w = self._width
        h = self._height
        if w > limit[0]:
            h = limit[0] * h // w
            w = limit[0]
        if h > limit[1]:
            w = limit[1] * w // h
            h = limit[1]
        w = max(1, w)
        h = max(1, h)
        return self.__class__(w, h)

    def fits_within(self, limit):
        """Check whether the rectangle fits within a limit.

        Arguments:

        limit        -- A tuple (width, height) or a Rectangle instance.
        """

        return self._width <= limit[0] and self._height <= limit[1]

    def max(self):
        """Get the maximum of the rectangle's width and height."""

        return max(self._width, self._height)

    def min(self):
        """Get the minimum of the rectangle's width and height."""

        return min(self._width, self._height)

    def rescaled_to(self, limit):
        """Scale the rectangle up or down to fit within a given limit.

        Returns the rescaled rectangle.
        """

        w = limit[0]
        h = limit[0] * self._height // self._width
        if h > limit[1]:
            w = limit[1] * w // h
            h = limit[1]
        w = max(1, w)
        h = max(1, h)
        return self.__class__(w, h)
