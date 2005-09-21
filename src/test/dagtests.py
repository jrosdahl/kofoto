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
from kofoto.dag import *

PICDIR = unicode(os.path.realpath(
    os.path.join("..", "reference_pictures", "working")))

def sorted(x):
    y = x[:]
    y.sort()
    return y

class TestDAG(unittest.TestCase):
    def setUp(self):
        self.dag = DAG()
        for x in [1, 2, 3, 4, 5, 6]:
            self.dag.add(x)
        for x, y in [(1, 3), (1, 4), (2, 3), (3, 5), (4, 5), (5, 6)]:
            self.dag.connect(x, y)

    def tearDown(self):
        del self.dag

    def test_iter(self):
        assert sorted(list(self.dag)) == [1, 2, 3, 4, 5, 6]

    def test_contains(self):
        assert 3 in self.dag

    def test_negative_contains(self):
        assert not 4711 in self.dag

    def test_redundant_add(self):
        self.dag.add(1)
        assert sorted(list(self.dag)) == [1, 2, 3, 4, 5, 6]

    def test_redundant_connect(self):
        assert self.dag.reachable(1, 3)
        self.dag.connect(1, 3)
        assert self.dag.reachable(1, 3)

    def test_connect_loop(self):
        try:
            self.dag.connect(6, 1)
        except LoopError:
            pass
        else:
            assert False

    def test_connected(self):
        assert self.dag.connected(1, 3)
        assert self.dag.connected(1, 4)
        assert not self.dag.connected(1, 2)
        assert not self.dag.connected(1, 5)

    def test_disconnect(self):
        assert self.dag.reachable(1, 3)
        self.dag.disconnect(1, 3)
        assert not self.dag.reachable(1, 3)

    def test_idempotent_disconnect(self):
        self.dag.disconnect(3, 1)
        assert self.dag.reachable(1, 3)
        assert not self.dag.reachable(3, 1)

    def test_getAncestors(self):
        for x, y in [(1, [1]),
                     (2, [2]),
                     (3, [1, 2, 3]),
                     (4, [1, 4]),
                     (5, [1, 2, 3, 4, 5]),
                     (6, [1, 2, 3, 4, 5, 6])]:
            assert sorted(list(self.dag.getAncestors(x))) == sorted(y)

    def test_getChildren(self):
        for x, y in [(1, [3, 4]),
                     (2, [3]),
                     (3, [5]),
                     (4, [5]),
                     (5, [6]),
                     (6, [])]:
            assert sorted(list(self.dag.getChildren(x))) == sorted(y)

    def test_getDescendants(self):
        for x, y in [(1, [1, 3, 4, 5, 6]),
                     (2, [2, 3, 5, 6]),
                     (3, [3, 5, 6]),
                     (4, [4, 5, 6]),
                     (5, [5, 6]),
                     (6, [6])]:
            assert sorted(list(self.dag.getDescendants(x))) == sorted(y)

    def test_getParents(self):
        for x, y in [(1, []),
                     (2, []),
                     (3, [1, 2]),
                     (4, [1]),
                     (5, [3, 4]),
                     (6, [5])]:
            assert sorted(list(self.dag.getParents(x))) == sorted(y)

    def test_getRoots(self):
        assert sorted(list(self.dag.getRoots())) == [1, 2]

    def test_reachable(self):
        assert self.dag.reachable(1, 3)
        assert self.dag.reachable(1, 6)
        assert not self.dag.reachable(1, 2)
        assert not self.dag.reachable(1, 4711)

    def test_remove(self):
        assert self.dag.reachable(1, 6)
        self.dag.remove(5)
        assert not self.dag.reachable(1, 6)

    def test_negative_remove(self):
        try:
            self.dag.remove(4711)
        except:
            pass
        else:
            assert False

######################################################################

if __name__ == "__main__":
    unittest.main()
