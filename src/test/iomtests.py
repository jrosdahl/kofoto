#! /usr/bin/env python

import os
import sys
import unittest

if __name__ == "__main__":
    cwd = os.getcwd()
    libdir = unicode(os.path.realpath(
        os.path.join(os.path.dirname(sys.argv[0]), "..", "packages")))
    os.chdir(libdir)
    sys.path.insert(0, libdir)
from kofoto.insertionorderedmapping import *

class TestInsertionOrderedMapping(unittest.TestCase):
    def setUp(self):
        self.iom = InsertionOrderedMapping([
            (1, "a"),
            (3, "c"),
            (2, "b"),
            ])

    def tearDown(self):
        del self.iom

    def test___cmp__(self):
        assert(cmp(self.iom, self.iom) == 0)
        iom2 = self.iom.copy()
        assert(cmp(self.iom, iom2) == 0)
        del iom2[3]
        assert(cmp(self.iom, iom2) == 1)
        del self.iom[2]
        del self.iom[3]
        assert(cmp(self.iom, iom2) == -1)

    def test___contains__(self):
        assert(0 not in self.iom)
        assert("a" not in self.iom)
        assert(1 in self.iom)
        assert(2 in self.iom)
        assert(3 in self.iom)

    def test___delitem__(self):
        try:
            del self.iom[0]
        except KeyError:
            pass
        else:
            assert False
        assert 0 not in self.iom
        assert len(self.iom) == 3
        del self.iom[1]
        assert 1 not in self.iom
        assert len(self.iom) == 2
        del self.iom[2]
        del self.iom[3]
        assert self.iom._keylist_head.next is self.iom._keylist_tail
        assert self.iom._keylist_tail.prev is self.iom._keylist_head
        assert len(self.iom) == 0

    def test___getitem__(self):
        try:
            self.iom[0]
        except KeyError:
            pass
        else:
            assert False
        assert self.iom[1] == "a"
        assert self.iom[2] == "b"
        assert self.iom[3] == "c"

    def test___iter__(self):
        assert list(self.iom) == [2, 3, 1]

    def test___repr__(self):
        assert \
            repr(self.iom) == \
            "InsertionOrderedMapping([(2, 'b'), (3, 'c'), (1, 'a')])"

    def test___setitem__(self):
        self.iom[0] = "-"
        assert self.iom.items() == [
            (0, "-"), (2, "b"), (3, "c"), (1, "a")]
        self.iom[4] = "d"
        assert self.iom.items() == [
            (4, "d"), (0, "-"), (2, "b"), (3, "c"), (1, "a")]

    def test_clear(self):
        self.iom.clear()
        assert 1 not in self.iom
        assert 2 not in self.iom
        assert 3 not in self.iom
        assert self.iom._keylist_head.next is self.iom._keylist_tail
        assert self.iom._keylist_tail.prev is self.iom._keylist_head
        assert len(self.iom) == 0

    def test_copy(self):
        assert self.iom.copy() == self.iom

    def test_get(self):
        assert self.iom.get(0) is None
        assert self.iom.get(0, "x") is "x"
        assert self.iom.get(1) == "a"

    def test_has_key(self):
        assert not self.iom.has_key(0)
        assert self.iom.has_key(1)
        assert self.iom.has_key(2)
        assert self.iom.has_key(3)

    def test_insert_after(self):
        self.iom.insert_after(1, 1, "z")
        assert self.iom.items() == [(2, "b"), (3, "c"), (1, "z")]
        assert len(self.iom) == 3
        self.iom.insert_after(2, 0, "x")
        assert self.iom.items() == [(2, "b"), (0, "x"), (3, "c"), (1, "z")]
        assert len(self.iom) == 4
        self.iom.insert_after(1, 0, "y")
        assert self.iom.items() == [(2, "b"), (3, "c"), (1, "z"), (0, "y")]
        assert len(self.iom) == 4
        try:
            self.iom.insert_after(5, 1, "a")
        except KeyError:
            pass
        else:
            assert False
        assert self.iom.items() == [(2, "b"), (3, "c"), (1, "z"), (0, "y")]
        assert len(self.iom) == 4

    def test_insert_before(self):
        self.iom.insert_before(1, 1, "z")
        assert self.iom.items() == [(2, "b"), (3, "c"), (1, "z")]
        assert len(self.iom) == 3
        self.iom.insert_before(2, 0, "x")
        assert self.iom.items() == [(0, "x"), (2, "b"), (3, "c"), (1, "z")]
        assert len(self.iom) == 4
        self.iom.insert_before(1, 0, "y")
        assert self.iom.items() == [(2, "b"), (3, "c"), (0, "y"), (1, "z")]
        assert len(self.iom) == 4
        try:
            self.iom.insert_before(5, 1, "a")
        except KeyError:
            pass
        else:
            assert False
        assert self.iom.items() == [(2, "b"), (3, "c"), (0, "y"), (1, "z")]
        assert len(self.iom) == 4

    def test_insert_first(self):
        self.iom.insert_first(0, "-")
        assert self.iom.items() == [
            (0, "-"), (2, "b"), (3, "c"), (1, "a")]
        self.iom.insert_first(4, "d")
        assert self.iom.items() == [
            (4, "d"), (0, "-"), (2, "b"), (3, "c"), (1, "a")]

    def test_insert_last(self):
        self.iom.insert_last(0, "-")
        assert self.iom.items() == [
            (2, "b"), (3, "c"), (1, "a"), (0, "-")]
        self.iom.insert_last(4, "d")
        assert self.iom.items() == [
            (2, "b"), (3, "c"), (1, "a"), (0, "-"), (4, "d")]

    def test_items(self):
        assert self.iom.items() == [(2, "b"), (3, "c"), (1, "a")]

    def test_iteritems(self):
        assert list(self.iom.iteritems()) == [(2, "b"), (3, "c"), (1, "a")]

    def test_iterkeys(self):
        assert list(self.iom.iterkeys()) == [2, 3, 1]

    def test_itervalues(self):
        assert list(self.iom.itervalues()) == ["b", "c", "a"]

    def test_keys(self):
        assert self.iom.keys() == [2, 3, 1]

    def test_pop(self):
        try:
            self.iom.pop(0)
        except KeyError:
            pass
        else:
            assert False
        assert self.iom.pop(0, "x") == "x"
        assert self.iom.pop(1) == "a"
        assert 1 not in self.iom
        assert len(self.iom) == 2

    def test_popitem(self):
        assert self.iom.popitem() == (2, "b")
        assert self.iom.popitem() == (3, "c")
        assert self.iom.popitem() == (1, "a")
        try:
            self.iom.popitem()
        except KeyError:
            pass
        else:
            assert False

    def test_reviteritems(self):
        assert list(self.iom.reviteritems()) == [(1, "a"), (3, "c"), (2, "b")]

    def test_reviterkeys(self):
        assert list(self.iom.reviterkeys()) == [1, 3, 2]

    def test_revitervalues(self):
        assert list(self.iom.revitervalues()) == ["a", "c", "b"]

    def test_setdefault(self):
        assert self.iom.setdefault(0, "x") == "x"
        assert self.iom.setdefault(1, "x") == "a"
        assert self.iom.setdefault(4) is None

    def test_update(self):
        self.iom.update([(0, "x"), (4, "d")])
        assert self.iom.items() == [
            (4, "d"), (0, "x"), (2, "b"), (3, "c"), (1, "a")]

    def test_values(self):
        assert self.iom.values() == ["b", "c", "a"]

######################################################################

if __name__ == "__main__":
    unittest.main()
