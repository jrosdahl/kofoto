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
        images = list(self.shelf.getAllImages())
        self.image1, self.image2, self.image3 = images[0:3]
        cat_a = self.shelf.getCategory(u"a")
        cat_b = self.shelf.getCategory(u"b")
        cat_c = self.shelf.getCategory(u"c")
        cat_d = self.shelf.getCategory(u"d")
        self.image1.addCategory(cat_a)
        self.image1.addCategory(cat_b)
        self.image2.addCategory(cat_c)
        self.image1.setAttribute(u"foo", u"abc")
        self.image1.setAttribute(u"bar", u"17")
        self.image2.setAttribute(u"foo", u"xyz")
        self.image3.setAttribute(u"fie", u"fum")

    def tearDown(self):
        TestShelfFixture.tearDown(self)

    def test_search(self):
        tests = [
            (u"a", [self.image2, self.image1]),
            (u"b", [self.image1]),
            (u"c", [self.image2]),
            (u"d", []),
            (u"(((b)))", [self.image1]),
            (u'@foo >= "b\'ar"', [self.image2]),
            (u"a and b", [self.image1]),
            (u'a and @foo = "abc"', [self.image1]),
            (u'a and @foo = xyz', [self.image2]),
            (u'@foo = "abc" and @bar = 17', [self.image1]),
            (u'a and b and @bar = "17" and @foo = abc', [self.image1]),
            (u"not a and c", []),
            (u"not exactly a and c", [self.image2]),
            (u"not (a and b) and a", [self.image2]),
            (u"not a and not b and @fie=fum", [self.image3]),
            (u"a and b or c", [self.image2, self.image1]),
            (u"b or c and d", [self.image1]),
            (u"a or b or c or d", [self.image2, self.image1]),
            (ur' ((a and not b) or @gazonk != "hej \"ju\"") and c ', [self.image2])]
        parser = Parser(self.shelf)
        for expression, expectedResult in tests:
            parseTree = parser.parse(expression)
            result = list(self.shelf.search(parseTree))
            result.sort(lambda x, y: cmp(x.getLocation(), y.getLocation()))
            assert result == expectedResult, (expression, expectedResult, result)

######################################################################

if __name__ == "__main__":
    removeTmpDb()
    unittest.main()
