#! /usr/bin/env python

import os
import sys
import unittest

if __name__ == "__main__":
    cwd = os.getcwd()
    libdir = unicode(os.path.realpath(
        os.path.join(os.path.dirname(sys.argv[0]), "..", "lib")))
    os.chdir(libdir)
    sys.path.insert(0, libdir)
from kofoto.shelf import *
from kofoto.search import *

PICDIR = unicode(os.path.realpath(
    os.path.join("..", "reference_pictures", "working")))

######################################################################

db = "shelf.tmp"
codeset = "latin1"

def removeTmpDb():
    for x in [db, db + "-journal"]:
        if os.path.exists(x):
            os.unlink(x)

from shelftests import TestShelfFixture

class TestSearch(TestShelfFixture):
    def setUp(self):
        TestShelfFixture.setUp(self)
        self.images = list(self.shelf.getAllImageVersions())
        cat_a = self.shelf.getCategoryById(u"a")
        cat_b = self.shelf.getCategoryById(u"b")
        cat_c = self.shelf.getCategoryById(u"c")
        cat_d = self.shelf.getCategoryById(u"d")
        self.images[0].addCategory(cat_a)
        self.images[0].addCategory(cat_b)
        self.images[1].addCategory(cat_c)
        self.images[0].setAttribute(u"foo", u"abc")
        self.images[0].setAttribute(u"bar", u"17")
        self.images[1].setAttribute(u"foo", u"xyz")
        self.images[2].setAttribute(u"fie", u"fum")

    def tearDown(self):
        TestShelfFixture.tearDown(self)

    def test_search(self):
        tests = [
            (u"a", [self.images[0], self.images[1]]),
            (u"b", [self.images[0]]),
            (u"c", [self.images[1]]),
            (u"d", []),
            (u"(((b)))", [self.images[0]]),
            (u'@foo >= "b\'ar"', [self.images[1]]),
            (u"a and b", [self.images[0]]),
            (u'a and @foo = "abc"', [self.images[0]]),
            (u'a and @foo = xyz', [self.images[1]]),
            (u'@foo = "abc" and @bar = 17', [self.images[0]]),
            (u'a and b and @bar = "17" and @foo = abc', [self.images[0]]),
            (u"not a and c", []),
            (u"not exactly a and c", [self.images[1]]),
            (u"not (a and b) and a", [self.images[1]]),
            (u"not a and not b and @fie=fum", [self.images[2]]),
            (u"a and b or c", [self.images[0], self.images[1]]),
            (u"b or c and d", [self.images[0]]),
            (u"a or b or c or d", [self.images[0], self.images[1]]),
            (ur' ((a and not b) or @gazonk != "hej \"ju\"") and c ', [self.images[1]]),
            (u"/alpha and a", [self.images[0], self.images[1]]),
            (u"/gamma", []),
            (u"/delta", self.images),
            (u"/epsilon", []),
            (u"/zeta", [self.images[0], self.images[1]]),
            ]
        parser = Parser(self.shelf)
        for expression, expectedResult in tests:
            parseTree = parser.parse(expression)
            result = list(self.shelf.search(parseTree))
            result.sort(lambda x, y: cmp(x.getId(), y.getId()))
            assert result == expectedResult, (expression, expectedResult, result)

    def test_parseErrors(self):
        tests = [
            (u"+", BadTokenError),
            (u":a and +", BadTokenError),
            (u'"', UnterminatedStringError),
            (ur'"\"\\\"', UnterminatedStringError),
            ]
        parser = Parser(self.shelf)
        for expression, expectedException in tests:
            try:
                parser.parse(expression)
            except expectedException:
                pass
            except Exception, e:
                assert False, (expression, expectedException, e)

######################################################################

if __name__ == "__main__":
    removeTmpDb()
    unittest.main()
