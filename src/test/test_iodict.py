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

from kofoto.iodict import InsertionOrderedDict


class TestInsertionOrderedDict(unittest.TestCase):
    def setUp(self):
        self.iod = InsertionOrderedDict([
            (1, "a"),
            (3, "c"),
            (2, "b"),
            ])

    def tearDown(self):
        del self.iod

    def test___cmp__(self):
        self.assertEqual(cmp(self.iod, self.iod), 0)
        iom2 = self.iod.copy()
        self.assertEqual(cmp(self.iod, iom2), 0)
        del iom2[3]
        self.assertEqual(cmp(self.iod, iom2), 1)
        del self.iod[2]
        del self.iod[3]
        self.assertEqual(cmp(self.iod, iom2), -1)

    def test___contains__(self):
        self.assert_(0 not in self.iod)
        self.assert_("a" not in self.iod)
        self.assert_(1 in self.iod)
        self.assert_(2 in self.iod)
        self.assert_(3 in self.iod)

    def test___delitem__(self):
        try:
            del self.iod[0]
        except KeyError:
            pass
        else:
            self.assert_(False)
        self.assert_(0 not in self.iod)
        self.assertEqual(len(self.iod), 3)
        del self.iod[1]
        self.assert_(1 not in self.iod)
        self.assertEqual(len(self.iod), 2)
        del self.iod[2]
        del self.iod[3]
        self.assert_(self.iod._keylist_head.next is self.iod._keylist_tail)
        self.assert_(self.iod._keylist_tail.prev is self.iod._keylist_head)
        self.assertEqual(len(self.iod), 0)

    def test___getitem__(self):
        try:
            self.iod[0]
        except KeyError:
            pass
        else:
            assert False
        assert self.iod[1] == "a"
        assert self.iod[2] == "b"
        assert self.iod[3] == "c"

    def test___iter__(self):
        assert list(self.iod) == [2, 3, 1]

    def test___repr__(self):
        assert \
            repr(self.iod) == \
            "InsertionOrderedDict([(2, 'b'), (3, 'c'), (1, 'a')])"

    def test___setitem__(self):
        self.iod[0] = "-"
        assert self.iod.items() == [
            (0, "-"), (2, "b"), (3, "c"), (1, "a")]
        self.iod[4] = "d"
        assert self.iod.items() == [
            (4, "d"), (0, "-"), (2, "b"), (3, "c"), (1, "a")]

    def test_clear(self):
        self.iod.clear()
        assert 1 not in self.iod
        assert 2 not in self.iod
        assert 3 not in self.iod
        assert self.iod._keylist_head.next is self.iod._keylist_tail
        assert self.iod._keylist_tail.prev is self.iod._keylist_head
        assert len(self.iod) == 0

    def test_copy(self):
        assert self.iod.copy() == self.iod

    def test_get(self):
        assert self.iod.get(0) is None
        assert self.iod.get(0, "x") is "x"
        assert self.iod.get(1) == "a"

    def test_has_key(self):
        assert not self.iod.has_key(0)
        assert self.iod.has_key(1)
        assert self.iod.has_key(2)
        assert self.iod.has_key(3)

    def test_insert_after(self):
        self.iod.insert_after(1, 1, "z")
        assert self.iod.items() == [(2, "b"), (3, "c"), (1, "z")]
        assert len(self.iod) == 3
        self.iod.insert_after(2, 0, "x")
        assert self.iod.items() == [(2, "b"), (0, "x"), (3, "c"), (1, "z")]
        assert len(self.iod) == 4
        self.iod.insert_after(1, 0, "y")
        assert self.iod.items() == [(2, "b"), (3, "c"), (1, "z"), (0, "y")]
        assert len(self.iod) == 4
        try:
            self.iod.insert_after(5, 1, "a")
        except KeyError:
            pass
        else:
            assert False
        assert self.iod.items() == [(2, "b"), (3, "c"), (1, "z"), (0, "y")]
        assert len(self.iod) == 4

    def test_insert_before(self):
        self.iod.insert_before(1, 1, "z")
        assert self.iod.items() == [(2, "b"), (3, "c"), (1, "z")]
        assert len(self.iod) == 3
        self.iod.insert_before(2, 0, "x")
        assert self.iod.items() == [(0, "x"), (2, "b"), (3, "c"), (1, "z")]
        assert len(self.iod) == 4
        self.iod.insert_before(1, 0, "y")
        assert self.iod.items() == [(2, "b"), (3, "c"), (0, "y"), (1, "z")]
        assert len(self.iod) == 4
        try:
            self.iod.insert_before(5, 1, "a")
        except KeyError:
            pass
        else:
            assert False
        assert self.iod.items() == [(2, "b"), (3, "c"), (0, "y"), (1, "z")]
        assert len(self.iod) == 4

    def test_insert_first(self):
        self.iod.insert_first(0, "-")
        assert self.iod.items() == [
            (0, "-"), (2, "b"), (3, "c"), (1, "a")]
        self.iod.insert_first(4, "d")
        assert self.iod.items() == [
            (4, "d"), (0, "-"), (2, "b"), (3, "c"), (1, "a")]

    def test_insert_last(self):
        self.iod.insert_last(0, "-")
        assert self.iod.items() == [
            (2, "b"), (3, "c"), (1, "a"), (0, "-")]
        self.iod.insert_last(4, "d")
        assert self.iod.items() == [
            (2, "b"), (3, "c"), (1, "a"), (0, "-"), (4, "d")]

    def test_items(self):
        assert self.iod.items() == [(2, "b"), (3, "c"), (1, "a")]

    def test_iteritems(self):
        assert list(self.iod.iteritems()) == [(2, "b"), (3, "c"), (1, "a")]

    def test_iterkeys(self):
        assert list(self.iod.iterkeys()) == [2, 3, 1]

    def test_itervalues(self):
        assert list(self.iod.itervalues()) == ["b", "c", "a"]

    def test_keys(self):
        assert self.iod.keys() == [2, 3, 1]

    def test_pop(self):
        try:
            self.iod.pop(0)
        except KeyError:
            pass
        else:
            assert False
        assert self.iod.pop(0, "x") == "x"
        assert self.iod.pop(1) == "a"
        assert 1 not in self.iod
        assert len(self.iod) == 2

    def test_popitem(self):
        assert self.iod.popitem() == (2, "b")
        assert self.iod.popitem() == (3, "c")
        assert self.iod.popitem() == (1, "a")
        try:
            self.iod.popitem()
        except KeyError:
            pass
        else:
            assert False

    def test_reviteritems(self):
        assert list(self.iod.reviteritems()) == [(1, "a"), (3, "c"), (2, "b")]

    def test_reviterkeys(self):
        assert list(self.iod.reviterkeys()) == [1, 3, 2]

    def test_revitervalues(self):
        assert list(self.iod.revitervalues()) == ["a", "c", "b"]

    def test_setdefault(self):
        assert self.iod.setdefault(0, "x") == "x"
        assert self.iod.setdefault(1, "x") == "a"
        assert self.iod.setdefault(4) is None

    def test_update(self):
        self.iod.update([(0, "x"), (4, "d")])
        assert self.iod.items() == [
            (4, "d"), (0, "x"), (2, "b"), (3, "c"), (1, "a")]

    def test_values(self):
        assert self.iod.values() == ["b", "c", "a"]


if __name__ == "__main__":
    unittest.main()
