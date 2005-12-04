"""This module contains the InsertionOrderedMapping class."""

__all__ = ["InsertionOrderedMapping"]

class _KeyListNode:
    def __init__(self, key=None):
        self.key = key
        self.prev = None
        self.next = None

    def insert_after(self, node):
        assert self.prev is None
        assert self.next is None
        if node.next:
            node.next.prev = self
            self.next = node.next
        self.prev = node
        node.next = self

    def insert_before(self, node):
        assert self.prev is None
        assert self.next is None
        if node.prev:
            node.prev.next = self
            self.prev = node.prev
        self.next = node
        node.prev = self

    def unlink(self):
        if self.prev:
            self.prev.next = self.next
        if self.next:
            self.next.prev = self.prev
        self.prev = None
        self.next = None

class InsertionOrderedMapping:
    """A mapping datatype with keys sorted in insertion order."""

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
                if sval != oval:
                    return cmp(sval, oval)
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
        return "InsertionOrderedMapping(%r)" % self.items()

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
        return InsertionOrderedMapping(self.reviteritems())

    def get(self, key, default=None):
        if key in self._map:
            return self._map[key][1]
        else:
            return default

    def has_key(self, key):
        return self._map.has_key(key)

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
