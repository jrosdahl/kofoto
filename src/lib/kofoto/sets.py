"""A non-generator version of a subset of sets.py in Python 2.3."""

__all__ = ["Set"]

class Set:
    def __init__(self, initlist=None):
        self._elements = {}
        if initlist:
            self.update(initlist)

    def __and__(self, other):
        return self.intersection(other)

    def __contains__(self, element):
        return element in self._elements

    def __eq__(self, other):
        if isinstance(other, Set):
            return self._elements == other._elements
        else:
            return False

    def __le__(self, other):
        return self.issubset(other)

    def __lt__(self, other):
        return len(self) < len(other) and self.issubset(other)

    def __ge__(self, other):
        return self.issuperset(other)

    def __gt__(self, other):
        return len(self) > len(other) and self.issuperset(other)

    def __iand__(self, other):
        self.intersection_update(other)
        return self

    def __ior__(self, other):
        self.union_update(other)
        return self

    def __isub__(self, other):
        self.difference_update(other)
        return self

    def __iter__(self):
        return self._elements.iterkeys()

    def __ixor__(self, other):
        self.symmetric_difference_update(other)
        return self

    def __len__(self):
        return len(self._elements)

    def __ne__(self, other):
        if isinstance(other, Set):
            return self._elements != other._elements
        else:
            return False

    def __or__(self, other):
        return self.union(other)

    def __repr__(self):
        return "Set(%s)" % repr(self._elements.keys())

    def __sub__(self, other):
        return self.difference(other)

    def __xor__(self, other):
        return self.symmetric_difference(other)

    def add(self, element):
        self._elements[element] = True

    def clear(self):
        self._elements = {}
        
    def copy(self):
        new = Set()
        new._elements = self._elements.copy()
        return new

    def difference(self, other):
        new = Set()
        new._elements.update(self._elements)
        otherelements = other._elements
        newelements = new._elements
        for x in otherelements:
            try:
                del newelements[x]
            except KeyError:
                pass
        return new

    def difference_update(self, other):
        selfelements = self._elements
        otherelements = other._elements
        for x in otherelements:
            try:
                del selfelements[x]
            except KeyError:
                pass

    def discard(self, element):
        try:
            del self._elements[element]
        except KeyError:
            pass

    def intersection(self, other):
        new = Set()
        selfelements = self._elements
        otherelements = other._elements
        newelements = new._elements
        for x in selfelements:
            if x in otherelements:
                newelements[x] = True
        return new

    def intersection_update(self, other):
        self._elements = (self.intersection(other))._elements

    def issubset(self, other):
        selfelements = self._elements
        otherelements = other._elements
        for x in selfelements:
            if not x in otherelements:
                return False
        return True

    def issuperset(self, other):
        selfelements = self._elements
        otherelements = other._elements
        for x in otherelements:
            if not x in selfelements:
                return False
        return True

    def pop(self):
        return self._elements.popitem()[0]

    def remove(self, element):
        del self._elements[element]

    def symmetric_difference(self, other):
        new = Set()
        new._elements.update(self._elements)
        otherelements = other._elements
        newelements = new._elements
        for x in otherelements:
            try:
                del newelements[x]
            except KeyError:
                newelements[x] = True
        return new

    def symmetric_difference_update(self, other):
        selfelements = self._elements
        otherelements = other._elements
        for x in otherelements:
            try:
                del selfelements[x]
            except KeyError:
                selfelements[x] = True

    def union(self, other):
        new = Set()
        new._elements.update(self._elements)
        new._elements.update(other._elements)
        return new

    def union_update(self, other):
        self._elements.update(other._elements)
        return self

    def update(self, iterable):
        selfelements = self._elements
        if isinstance(iterable, Set):
            selfelements.update(iterable._data)
        else:
            for x in iterable:
                selfelements[x] = True
