# Copyright (c) 2006 Joel Rosdahl
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
#       copyright notice, this list of conditions and the following
#       disclaimer in the documentation and/or other materials
#       provided with the distribution.
#     * Neither the name of the copyright holders nor the names of
#       contributors may be used to endorse or promote products
#       derived from this software without specific prior written
#       permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

"""iodict -- An insertion-ordered dictionary.

This module contains a class called InsertionOrderedDict, which
implements a dictionary that keeping the keys in insertion order.
"""


__all__ = ["InsertionOrderedDict"]


class InsertionOrderedDict:
    """A mapping datatype with keys kept in insertion order.

    An ordinary dict insertion operation (d[k] = v) inserts the
    key-value pair first in the dictionary, so the oldest insertion
    appears last in the key list.

    Apart from the standard mapping interface, the class has some
    extra methods:

    insert_after  -- insert a key-value pair after a given existing key
    insert_before -- insert a key-value pair before a given existing key
    insert_first  -- insert a key-value pair first in the dictionary
    insert_last   -- insert a key-value pair last in the dictionary
    reviteritems  -- return a backward iterator over (key, value) pairs
    reviterkeys   -- return a backward iterator over the dictionary's keys
    revitervalues -- return a backward iterator over the dictionary's values

    The class keeps keys in a linked list, which means that insertion
    and deletion are asymptotically efficient; insertion and deletion
    are (amortized) O(1). For small dictionaries, this approach will
    be slower than using an ordinary arrayish Python list, though.
    """

    def __init__(self, items=None):
        self._map = {} # key --> (keylistnode, value)
        self._keylist_head = _KeyListNode()
        self._keylist_tail = _KeyListNode()
        self._keylist_tail.insert_after(self._keylist_head)
        if items is not None:
            self.update(items)

    def __cmp__(self, other):
        snode = self._keylist_head.next
        onode = other._keylist_head.next
        while True:
            if snode is self._keylist_tail:
                if onode is other._keylist_tail:
                    return 0
                else:
                    return -1
            elif onode is other._keylist_tail:
                return 1
            elif snode.key != onode.key:
                return cmp(snode.key, onode.key)
            else:
                sval = self._map[snode.key][1]
                oval = other._map[onode.key][1]
                cmpval = cmp(sval, oval)
                if cmpval != 0:
                    return cmpval
            snode = snode.next
            onode = onode.next

    def __contains__(self, key):
        return key in self._map

    def __delitem__(self, key):
        self._map[key][0].unlink()
        del self._map[key]

    def __getitem__(self, key):
        return self._map[key][1]

    def __iter__(self):
        return self.iterkeys()

    def __len__(self):
        return len(self._map)

    def __repr__(self):
        return "InsertionOrderedDict(%r)" % self.items()

    def __setitem__(self, key, value):
        if key in self._map:
            node = self._map[key][0]
            node.unlink()
        else:
            node = _KeyListNode(key)
        self._map[key] = (node, value)
        node.insert_after(self._keylist_head)

    def clear(self):
        self._map.clear()

        # Break reference cycles:
        node = self._keylist_head
        while node is not None:
            node.prev = None
            node = node.next
        self._keylist_head.unlink()
        self._keylist_tail.unlink()
        self._keylist_tail.insert_after(self._keylist_head)

    def copy(self):
        return InsertionOrderedDict(self.reviteritems())

    def get(self, key, default=None):
        if key in self._map:
            return self._map[key][1]
        else:
            return default

    def has_key(self, key):
        return self._map.has_key(key)

    def insert_after(self, refkey, key, value):
        """Insert a key-value pair after a given existing key.

        Arguments:

        refkey -- Reference key after which to insert the key-value pair.
        key    -- The key to insert.
        value  -- The value to insert.
        """
        self._insert_after_or_before(refkey, key, value, True)

    def insert_before(self, refkey, key, value):
        """Insert a key-value pair before an given existing key.

        Arguments:

        refkey -- Reference key before which to insert the key-value pair.
        key    -- The key to insert.
        value  -- The value to insert.
        """
        self._insert_after_or_before(refkey, key, value, False)

    def insert_first(self, key, value):
        """Insert a key-value pair first in the dictionary.

        Arguments:

        key    -- The key to insert.
        value  -- The value to insert.
        """
        self[key] = value

    def insert_last(self, key, value):
        """Insert a key-value pair last in the dictionary.

        Arguments:

        key    -- The key to insert.
        value  -- The value to insert.
        """
        if key in self._map:
            node = self._map[key][0]
            node.unlink()
        else:
            node = _KeyListNode(key)
        self._map[key] = (node, value)
        node.insert_before(self._keylist_tail)

    def items(self):
        return list(self.iteritems())

    def iteritems(self):
        node = self._keylist_head.next
        while node is not self._keylist_tail:
            yield (node.key, self._map[node.key][1])
            node = node.next

    def iterkeys(self):
        node = self._keylist_head.next
        while node is not self._keylist_tail:
            yield node.key
            node = node.next

    def itervalues(self):
        node = self._keylist_head.next
        while node is not self._keylist_tail:
            yield self._map[node.key][1]
            node = node.next

    def keys(self):
        return list(self.iterkeys())

    def pop(self, key, default=None):
        if key in self._map:
            value = self[key]
            del self[key]
            return value
        else:
            if default is None:
                raise KeyError(key)
            else:
                return default

    def popitem(self):
        if len(self) == 0:
            raise KeyError
        else:
            key = self._keylist_head.next.key
            value = self.pop(key)
            return (key, value)

    def reviteritems(self):
        node = self._keylist_tail.prev
        while node is not self._keylist_head:
            yield (node.key, self._map[node.key][1])
            node = node.prev

    def reviterkeys(self):
        node = self._keylist_tail.prev
        while node is not self._keylist_head:
            yield node.key
            node = node.prev

    def revitervalues(self):
        node = self._keylist_tail.prev
        while node is not self._keylist_head:
            yield self._map[node.key][1]
            node = node.prev

    def setdefault(self, key, value=None):
        if key in self._map:
            return self[key]
        else:
            self[key] = value
            return value

    def update(self, items):
        for key, value in items:
            self[key] = value

    def values(self):
        return list(self.itervalues())

    def _insert_after_or_before(self, refkey, key, value, after):
        refnode = self._map[refkey][0]
        if refkey == key:
            self._map[refkey] = (refnode, value)
        else:
            if key in self._map:
                del self[key]
            node = _KeyListNode(key)
            self._map[key] = (node, value)
            if after:
                node.insert_after(refnode)
            else:
                node.insert_before(refnode)


class _KeyListNode:
    def __init__(self, key=None):
        self.key = key
        self.prev = None
        self.next = None

    def insert_after(self, node):
        if node.next is not None:
            node.next.prev = self
            self.next = node.next
        self.prev = node
        node.next = self

    def insert_before(self, node):
        if node.prev is not None:
            node.prev.next = self
            self.prev = node.prev
        self.next = node
        node.prev = self

    def unlink(self):
        if self.prev is not None:
            self.prev.next = self.next
        if self.next is not None:
            self.next.prev = self.prev
        self.prev = None
        self.next = None


######################################################################


if __name__ == "__main__":
    import unittest

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

    unittest.main()
