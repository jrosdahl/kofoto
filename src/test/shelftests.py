#! /usr/bin/env python

import gc
import os
import shutil
import sys
import threading
import unittest
import Image as PILImage

if __name__ == "__main__":
    cwd = os.getcwd()
    libdir = unicode(os.path.realpath(
        os.path.join(os.path.dirname(sys.argv[0]), "..", "lib")))
    os.chdir(libdir)
    sys.path.insert(0, libdir)
from kofoto.shelf import *

PICDIR = unicode(os.path.realpath(
    os.path.join("..", "reference_pictures", "working")))

######################################################################

db = "shelf.tmp"
codeset = "latin1"

def removeTmpDb():
    for x in [db, db + "-journal"]:
        if os.path.exists(x):
            os.unlink(x)

class LockerThread(threading.Thread):
    def __init__(self, mContinue, ltContinue):
        threading.Thread.__init__(self)
        self.mContinue = mContinue
        self.ltContinue = ltContinue

    def run(self):
        s = Shelf(db, codeset)
        s.create()
        s.begin()
        self.mContinue.set()
        self.ltContinue.wait()
        s.rollback()

######################################################################

class TestPublicShelfFunctions(unittest.TestCase):
    def test_computeImageHash(self):
        s = computeImageHash(os.path.join(PICDIR, "arlaharen.png"))
        assert s == "39a1266d2689f53d48b09a5e0ca0af1f"
        try:
            computeImageHash("nonexisting")
        except IOError:
            pass
        else:
            assert False, s

    def test_verifyValidAlbumTag(self):
        # Valid tags.
        for x in ("foo", "1foo", "and", "exactly", "not", "or"):
            try:
                verifyValidAlbumTag(x)
            except:
                assert False, x
        # Invalid tags.
        for x in (None, 1, 1L, "1" "foo " "@foo"):
            try:
                verifyValidAlbumTag(x)
            except BadAlbumTagError:
                pass
            else:
                assert False, x

    def test_verifyValidCategoryTag(self):
        # Valid tags.
        for x in ("foo", "1foo"):
            try:
                verifyValidCategoryTag(x)
            except:
                assert False, x
        # Invalid tags.
        for x in (None, 1, 1L, "1" "foo " "@foo",
                  "and", "exactly", "not", "or"):
            try:
                verifyValidCategoryTag(x)
            except BadCategoryTagError:
                pass
            else:
                assert False, x

    def test_makeValidTag(self):
        for tag, validTag in [("", "_"),
                              ("@", "_"),
                              (" ", "_"),
                              ("1", "1_"),
                              ("@foo_", "foo_"),
                              ("fo@o __", "fo@o__")]:
            assert makeValidTag(tag) == validTag, (tag, validTag)

class TestNegativeShelfOpens(unittest.TestCase):
    def tearDown(self):
        removeTmpDb()

    def test_NonexistingShelf(self):
        try:
            s = Shelf(db, codeset)
            s.begin()
        except ShelfNotFoundError:
            pass
        else:
            assert False
        assert not os.path.exists(db)

    def test_BadShelf(self):
        file(db, "w") # Create empty file.
        try:
            s = Shelf(db, codeset)
            s.begin()
        except UnsupportedShelfError:
            pass
        else:
            assert False

    def test_LockedShelf(self):
        mContinue = threading.Event()
        ltContinue = threading.Event()
        lt = LockerThread(mContinue, ltContinue)
        lt.start()
        mContinue.wait()
        try:
            try:
                s = Shelf(db, codeset)
                s.begin()
            except ShelfLockedError:
                pass
            else:
                assert False
        finally:
            ltContinue.set()
            lt.join()

class TestShelfCreation(unittest.TestCase):
    def tearDown(self):
        removeTmpDb()

    def test_CreateShelf1(self):
        s = Shelf(db, codeset)
        s.create()
        assert os.path.exists(db)

    def test_CreateShelf2(self):
        file(db, "w") # Create empty file.
        s = Shelf(db, codeset)
        try:
            s.create()
        except FailedWritingError:
            pass
        else:
            assert False

class TestShelfMemoryLeakage(unittest.TestCase):
    def tearDown(self):
        removeTmpDb()

    def test_MemoryLeak1(self):
        s = Shelf(db, codeset)
        s.create()
        assert gc.collect() == 0

    def test_MemoryLeak2(self):
        s = Shelf(db, codeset)
        s.create()
        s.begin()
        s.getObject(0)
        s.rollback()
        assert gc.collect() == 0

    def test_MemoryLeak3(self):
        s = Shelf(db, codeset)
        s.create()
        s.begin()
        s.getObject(0)
        s.commit()
        assert gc.collect() == 0

class TestShelfTransactions(unittest.TestCase):
    def tearDown(self):
        removeTmpDb()

    def test_commit(self):
        s = Shelf(db, codeset)
        s.create()
        s.begin()
        s.createAlbum(u"foo")
        assert s.getAlbum(u"foo")
        s.commit()
        s = Shelf(db, codeset)
        s.begin()
        assert s.getAlbum(u"foo")
        s.rollback()

    def test_rollback(self):
        s = Shelf(db, codeset)
        s.create()
        s.begin()
        s.createAlbum(u"foo")
        s.rollback()
        s.begin()
        try:
            s.getAlbum(u"foo")
        except AlbumDoesNotExistError:
            pass
        else:
            assert False

    def test_isModified(self):
        s = Shelf(db, codeset)
        s.create()
        s.begin()
        assert not s.isModified()
        s.createAlbum(u"foo")
        assert s.isModified()
        s.rollback()
        s.begin()
        assert not s.isModified()
        s.rollback()

    def test_registerModificationCallback(self):
        res = [False]
        def f(x):
            res[0] = True
        s = Shelf(db, codeset)
        s.create()
        s.begin()
        s.registerModificationCallback(f)
        assert not res[0]
        s.createAlbum(u"foo")
        assert res[0]
        s.rollback()
        res[0] = False
        s.begin()
        assert not res[0]
        s.unregisterModificationCallback(f)
        s.createAlbum(u"foo")
        assert not res[0]
        s.rollback()

class TestShelfFixture(unittest.TestCase):
    def setUp(self):
        self.shelf = Shelf(db, codeset)
        self.shelf.create()
        self.shelf.begin()
        root = self.shelf.getRootAlbum()
        alpha = self.shelf.createAlbum(u"alpha")
        beta = self.shelf.createAlbum(u"beta")
        children = [beta]
        for x in os.listdir(PICDIR):
            loc = os.path.join(PICDIR, x)
            if not os.path.isfile(loc):
                continue
            children.append(self.shelf.createImage(loc))
        del children[-1] # The last image becomes orphaned.
        alpha.setChildren(children)
        beta.setChildren(list(beta.getChildren()) + [children[-1]])
        root.setChildren(list(root.getChildren()) + [
            alpha,
            beta,
            self.shelf.createAlbum(u"gamma", u"allalbums"),
            self.shelf.createAlbum(u"delta", u"allimages")])
        self.shelf.createAlbum(u"epsilon", u"plain") # Orphan album.

        cat_a = self.shelf.createCategory(u"a", u"A")
        cat_b = self.shelf.createCategory(u"b", u"B")
        cat_c = self.shelf.createCategory(u"c", u"C")
        cat_d = self.shelf.createCategory(u"d", u"D")
        cat_a.connectChild(cat_b)
        cat_a.connectChild(cat_c)
        cat_b.connectChild(cat_d)
        cat_c.connectChild(cat_d)

        self.shelf.flushObjectCache()
        self.shelf.flushCategoryCache()

    def tearDown(self):
        self.shelf.rollback()
        removeTmpDb()

class TestShelfMethods(TestShelfFixture):
    def test_flushCaches(self):
        self.shelf.flushCategoryCache()
        self.shelf.flushObjectCache()

    def test_getStatistics(self):
        s = self.shelf.getStatistics()
        assert s["nalbums"] == 7
        assert s["nimages"] == 11

    def test_createdObjects(self):
        root = self.shelf.getRootAlbum()
        children = list(root.getChildren())
        assert len(children) == 5
        orphans, alpha, beta, gamma, delta = children
        assert self.shelf.getObject(u"alpha") == alpha
        assert self.shelf.getAlbum(u"beta") == beta
        assert len(list(alpha.getChildren())) == 11
        assert len(list(beta.getChildren())) == 1
        assert len(list(gamma.getChildren())) == 7
        assert len(list(delta.getChildren())) == 11

    def test_createdAttributes(self):
        for image in self.shelf.getAllImages():
            assert image.getAttribute(u"registered")
        image = self.shelf.getImage(
            os.path.join(PICDIR, "Canon_Digital_IXUS.jpg"))
        assert image.getAttribute(u"captured") == "2002-02-02 22:20:51"
        assert image.getAttribute(u"cameramake") == "Canon"
        assert image.getAttribute(u"cameramodel") == "Canon DIGITAL IXUS"

    def test_negativeAlbumCreation(self):
        try:
            self.shelf.createAlbum(u"beta")
        except AlbumExistsError:
            pass
        else:
            assert False

    def test_getAlbum(self):
        album = self.shelf.getAlbum(u"alpha")
        album = self.shelf.getAlbum(album.getTag())
        album = self.shelf.getAlbum(album.getId())

    def test_negativeGetAlbum(self):
        try:
            self.shelf.getAlbum(u"nonexisting")
        except AlbumDoesNotExistError:
            pass
        else:
            assert False

    def test_getRootAlbum(self):
        root = self.shelf.getRootAlbum()
        assert root == self.shelf.getAlbum(u"root")

    def test_getAllAlbums(self):
        albums = list(self.shelf.getAllAlbums())
        assert len(albums) == 7

    def test_getAllImages(self):
        images = list(self.shelf.getAllImages())
        assert len(images) == 11

    def test_getImagesInDirectory(self):
        images = list(self.shelf.getImagesInDirectory(u"."))
        assert len(images) == 0
        images = list(self.shelf.getImagesInDirectory(PICDIR))
        assert len(images) == 11

    def test_deleteAlbum(self):
        self.shelf.deleteAlbum(u"beta")

    def test_negativeRootAlbumDeletion(self):
        try:
            self.shelf.deleteAlbum(u"root")
        except UndeletableAlbumError:
            pass
        else:
            assert False

    def test_negativeAlbumDeletion(self):
        try:
            self.shelf.deleteAlbum(u"nonexisting")
        except AlbumDoesNotExistError:
            pass
        else:
            assert False

    def test_negativeImageCreation(self):
        try:
            self.shelf.createImage(os.path.join(PICDIR, "arlaharen.png"))
        except ImageExistsError:
            pass
        else:
            assert False

    def test_getImage(self):
        image = self.shelf.getImage(os.path.join(PICDIR, "arlaharen.png"))
        image = self.shelf.getImage(image.getHash())
        image = self.shelf.getImage(image.getId())

    def test_negativeGetImage(self):
        try:
            self.shelf.getImage(u"nonexisting")
        except ImageDoesNotExistError:
            pass
        else:
            assert False

    def test_deleteImage(self):
        self.shelf.deleteImage(os.path.join(PICDIR, "arlaharen.png"))

    def test_negativeImageDeletion(self):
        try:
            self.shelf.deleteImage(u"nonexisting")
        except ImageDoesNotExistError:
            pass
        else:
            assert False

    def test_getObject(self):
        album = self.shelf.getObject(u"alpha")
        album = self.shelf.getObject(album.getTag())
        album = self.shelf.getObject(album.getId())
        image = self.shelf.getObject(os.path.join(PICDIR, "arlaharen.png"))
        image = self.shelf.getObject(image.getHash())
        image = self.shelf.getObject(image.getId())

    def test_deleteObject(self):
        self.shelf.deleteObject(u"beta")
        self.shelf.deleteObject(os.path.join(PICDIR, "arlaharen.png"))

    def test_getAllAttributeNames(self):
        attrnames = list(self.shelf.getAllAttributeNames())
        attrnames.sort()
        assert attrnames == [
            "cameramake", "cameramodel", "captured", "description",
            "orientation", "registered", "title"
            ]

    def test_negativeCreateCategory(self):
        try:
            self.shelf.createCategory(u"a", u"Foo")
        except CategoryExistsError:
            pass
        else:
            assert False

    def test_deleteCategory(self):
        self.shelf.deleteCategory(u"a")

    def test_negativeDeleteCategory(self):
        try:
            self.shelf.deleteCategory(u"nonexisting")
        except CategoryDoesNotExistError:
            pass
        else:
            assert False

    def test_getRootCategories(self):
        categories = list(self.shelf.getRootCategories())
        cat_a = self.shelf.getCategory(u"a")
        assert categories == [cat_a]

class TestCategory(TestShelfFixture):
    def test_categoryMethods(self):
        cat_a = self.shelf.getCategory(u"a")
        cat_b = self.shelf.getCategory(u"b")
        cat_c = self.shelf.getCategory(u"c")
        cat_d = self.shelf.getCategory(u"d")

        assert self.shelf.getCategory(cat_a.getTag()) == cat_a
        assert self.shelf.getCategory(cat_a.getId()) == cat_a
        cat_a.setTag(u"foo")
        assert self.shelf.getCategory(u"foo") == cat_a

        assert cat_a.getDescription() == "A"
        cat_a.setDescription(u"foo")
        assert cat_a.getDescription() == "foo"

        a_children = list(cat_a.getChildren())
        a_children.sort(lambda x, y: cmp(x.getId(), y.getId()))
        assert a_children == [cat_b, cat_c]
        b_children = list(cat_b.getChildren())
        assert b_children == [cat_d]
        d_children = list(cat_d.getChildren())
        assert d_children == []

        a_parents = list(cat_a.getParents())
        assert a_parents == []
        b_parents = list(cat_b.getParents())
        assert b_parents == [cat_a]
        d_parents = list(cat_d.getParents())
        d_parents.sort(lambda x, y: cmp(x.getTag(), y.getTag()))
        assert d_parents == [cat_b, cat_c]

        assert not cat_a.isChildOf(cat_a)
        assert cat_b.isChildOf(cat_a)
        assert cat_c.isChildOf(cat_a)
        assert not cat_d.isChildOf(cat_a)
        assert cat_a.isChildOf(cat_a, recursive=True)
        assert cat_b.isChildOf(cat_a, recursive=True)
        assert cat_c.isChildOf(cat_a, recursive=True)
        assert cat_d.isChildOf(cat_a, recursive=True)

        assert not cat_d.isParentOf(cat_d)
        assert cat_b.isParentOf(cat_d)
        assert cat_c.isParentOf(cat_d)
        assert not cat_a.isParentOf(cat_d)
        assert cat_d.isParentOf(cat_d, recursive=True)
        assert cat_b.isParentOf(cat_d, recursive=True)
        assert cat_c.isParentOf(cat_d, recursive=True)
        assert cat_a.isParentOf(cat_d, recursive=True)

    def test_negativeCategoryConnectChild(self):
        cat_a = self.shelf.getCategory(u"a")
        cat_b = self.shelf.getCategory(u"b")
        try:
            cat_a.connectChild(cat_b)
        except CategoriesAlreadyConnectedError:
            pass
        else:
            assert False
        try:
            cat_b.connectChild(cat_a)
        except CategoryLoopError:
            pass
        else:
            assert False

    def test_categoryDisconnectChild(self):
        cat_a = self.shelf.getCategory(u"a")
        cat_b = self.shelf.getCategory(u"b")
        cat_a.disconnectChild(cat_b)
        assert not cat_a.isParentOf(cat_b)

    def test_negativeCategoryDisconnectChild(self):
        cat_a = self.shelf.getCategory(u"a")
        cat_d = self.shelf.getCategory(u"d")
        cat_a.disconnectChild(cat_d) # No exception.

class TestObject(TestShelfFixture):
    def test_getParents(self):
        root = self.shelf.getRootAlbum()
        alpha = self.shelf.getAlbum(u"alpha")
        beta = self.shelf.getAlbum(u"beta")
        parents = list(beta.getParents())
        parents.sort(lambda x, y: cmp(x.getTag(), y.getTag()))
        assert parents == [alpha, root]

    def test_getAttribute(self):
        orphans = self.shelf.getAlbum(u"orphans")
        assert orphans.getAttribute(u"title")
        assert orphans.getAttribute(u"description")
        assert not orphans.getAttribute(u"nonexisting")

    def test_getAttributeMap(self):
        orphans = self.shelf.getAlbum(u"orphans")
        map = orphans.getAttributeMap()
        assert "description" in map
        assert "title" in map

    def test_getAttributeNames(self):
        orphans = self.shelf.getAlbum(u"orphans")
        names = list(orphans.getAttributeNames())
        names.sort()
        assert names == ["description", "title"]

    def test_setAttribute(self):
        orphans = self.shelf.getAlbum(u"orphans")
        orphans.setAttribute(u"foo", u"fie") # New.
        assert orphans.getAttribute(u"foo") == u"fie"
        assert u"foo" in orphans.getAttributeMap()
        assert u"foo" in orphans.getAttributeNames()
        assert orphans.getAttribute(u"title")
        orphans.setAttribute(u"title", u"gazonk") # Existing
        assert orphans.getAttribute(u"title") == u"gazonk"
        assert u"foo" in orphans.getAttributeMap()
        assert u"foo" in orphans.getAttributeNames()

    def test_deleteAttribute(self):
        orphans = self.shelf.getAlbum(u"orphans")
        orphans.deleteAttribute(u"nonexisting") # No exception.
        assert orphans.getAttribute(u"title")
        orphans.deleteAttribute(u"title")
        assert not orphans.getAttribute(u"title")

    def test_addCategory(self):
        orphans = self.shelf.getAlbum(u"orphans")
        cat_a = self.shelf.getCategory(u"a")
        assert list(orphans.getCategories()) == []
        orphans.addCategory(cat_a)
        assert list(orphans.getCategories()) == [cat_a]
        try:
            orphans.addCategory(cat_a)
        except CategoryPresentError:
            pass
        else:
            assert False
        assert list(orphans.getCategories()) == [cat_a]

    def test_removeCategory(self):
        orphans = self.shelf.getAlbum(u"orphans")
        assert list(orphans.getCategories()) == []
        cat_a = self.shelf.getCategory(u"a")
        orphans.addCategory(cat_a)
        assert list(orphans.getCategories()) == [cat_a]
        orphans.removeCategory(cat_a)
        assert list(orphans.getCategories()) == []

    def test_deleteCategoryInvalidatesCategoryCache(self):
        orphans = self.shelf.getAlbum(u"orphans")
        assert list(orphans.getCategories()) == []
        cat_a = self.shelf.getCategory(u"a")
        orphans.addCategory(cat_a)
        assert list(orphans.getCategories()) == [cat_a]
        self.shelf.deleteCategory(cat_a.getId())
        assert list(orphans.getCategories()) == []

class TestAlbum(TestShelfFixture):
    def test_getType(self):
        alpha = self.shelf.getAlbum(u"alpha")
        assert alpha.getType()

    def test_getTag(self):
        alpha = self.shelf.getAlbum(u"alpha")
        assert alpha.getTag() == u"alpha"

    def test_setTag(self):
        alpha = self.shelf.getAlbum(u"alpha")
        alpha.setTag(u"alfa")
        assert alpha.getTag() == u"alfa"

    def test_getAlbumParents(self):
        root = self.shelf.getRootAlbum()
        alpha = self.shelf.getAlbum(u"alpha")
        parents = list(alpha.getAlbumParents())
        parents.sort(lambda x, y: cmp(x.getTag(), y.getTag()))
        assert parents == [root]

    def test_isAlbum(self):
        assert self.shelf.getRootAlbum().isAlbum()

class TestPlainAlbum(TestShelfFixture):
    def test_getChildren(self):
        epsilon = self.shelf.getAlbum(u"epsilon")
        alpha = self.shelf.getAlbum(u"alpha")
        beta = self.shelf.getAlbum(u"beta")
        assert list(epsilon.getChildren()) == []
        alphaChildren = list(alpha.getChildren())
        assert list(beta.getChildren()) == [alphaChildren[-1]]

    def test_getAlbumChildren(self):
        alpha = self.shelf.getAlbum(u"alpha")
        beta = self.shelf.getAlbum(u"beta")
        epsilon = self.shelf.getAlbum(u"epsilon")
        alphaAlbumChildren = list(alpha.getAlbumChildren())
        assert alphaAlbumChildren == [beta]
        assert list(epsilon.getAlbumChildren()) == []

    def test_setChildren(self):
        root = self.shelf.getRootAlbum()
        beta = self.shelf.getAlbum(u"beta")
        assert list(beta.getChildren()) != []
        beta.setChildren([beta, root])
        assert list(beta.getChildren()) == [beta, root]
        beta.setChildren([]) # Break the cycle.
        assert list(beta.getChildren()) == []

class TestImage(TestShelfFixture):
    def test_getHash(self):
        image = self.shelf.getImage(os.path.join(PICDIR, "arlaharen.png"))
        assert image.getHash() == "39a1266d2689f53d48b09a5e0ca0af1f"

    def test_getLocation(self):
        location = os.path.join(PICDIR, "arlaharen.png")
        image = self.shelf.getImage(location)
        assert image.getLocation() == os.path.realpath(location)

    def test_getModificationTime(self):
        image = self.shelf.getImage(os.path.join(PICDIR, "arlaharen.png"))
        t = image.getModificationTime()
        assert isinstance(t, int)
        assert t > 0

    def test_getSize(self):
        image = self.shelf.getImage(os.path.join(PICDIR, "arlaharen.png"))
        assert image.getSize() == (304, 540)

    def test_contentChanged(self):
        path = os.path.join(PICDIR, "arlaharen.png")
        self.shelf.deleteImage(path)
        newpath = u"tmp.png"
        try:
            shutil.copy2(path, newpath)
            image = self.shelf.createImage(newpath)
            oldmtime = image.getModificationTime()
            pilimg = PILImage.open(newpath)
            pilimg.thumbnail((100, 100))
            pilimg.save(newpath, "PNG")
            image.contentChanged()
            assert image.getHash() == "d55a9cc74371c09d484b163c71497cab"
            assert image.getSize() == (56, 100)
            assert image.getModificationTime() > oldmtime
        finally:
            try:
                os.unlink(newpath)
            except OSError:
                pass

    def test_locationChanged(self):
        location = os.path.join(PICDIR, "arlaharen.png")
        image = self.shelf.getImage(location)
        image.locationChanged(u"/foo/../bar")
        assert image.getLocation() == "/bar"

    def test_isAlbum(self):
        image = self.shelf.getImage(os.path.join(PICDIR, "arlaharen.png"))
        assert not image.isAlbum()

    def test_importExifTags(self):
        image = self.shelf.getImage(os.path.join(PICDIR, "arlaharen.png"))
        image.importExifTags() # TODO: Test more.

class TestAllAlbumsAlbum(TestShelfFixture):
    def test_getChildren(self):
        gamma = self.shelf.getAlbum(u"gamma")
        assert len(list(gamma.getChildren())) == 7

    def test_getAlbumChildren(self):
        gamma = self.shelf.getAlbum(u"gamma")
        assert list(gamma.getAlbumChildren()) == list(gamma.getChildren())

    def test_setChildren(self):
        gamma = self.shelf.getAlbum(u"gamma")
        try:
            gamma.setChildren([])
        except UnsettableChildrenError:
            pass
        else:
            assert False

    def test_isAlbum(self):
        assert self.shelf.getAlbum(u"gamma").isAlbum()

class TestAllImagesAlbum(TestShelfFixture):
    def test_getChildren(self):
        delta = self.shelf.getAlbum(u"delta")
        assert len(list(delta.getChildren())) == 11

    def test_getAlbumChildren(self):
        delta = self.shelf.getAlbum(u"delta")
        assert list(delta.getAlbumChildren()) == []

    def test_setChildren(self):
        delta = self.shelf.getAlbum(u"delta")
        try:
            delta.setChildren([])
        except UnsettableChildrenError:
            pass
        else:
            assert False

    def test_isAlbum(self):
        assert self.shelf.getAlbum(u"delta").isAlbum()

class TestOrphansAlbum(TestShelfFixture):
    def test_getChildren(self):
        orphans = self.shelf.getAlbum(u"orphans")
        assert len(list(orphans.getChildren())) == 2

    def test_getAlbumChildren(self):
        orphans = self.shelf.getAlbum(u"orphans")
        epsilon = self.shelf.getAlbum(u"epsilon")
        assert list(orphans.getAlbumChildren()) == [epsilon]

    def test_setChildren(self):
        orphans = self.shelf.getAlbum(u"orphans")
        try:
            orphans.setChildren([])
        except UnsettableChildrenError:
            pass
        else:
            assert False

    def test_isAlbum(self):
        assert self.shelf.getAlbum(u"orphans").isAlbum()

class TestSearchAlbum(TestShelfFixture):
    def test_getChildren(self):
        alpha = self.shelf.getAlbum(u"alpha")
        image1, image2 = list(alpha.getChildren())[0:2]
        cat_a = self.shelf.getCategory(u"a")
        cat_b = self.shelf.getCategory(u"b")
        image1.addCategory(cat_a)
        image2.addCategory(cat_b)
        searchalbum = self.shelf.createAlbum(u"search", u"search")
        assert searchalbum
        searchalbum.setAttribute(u"query", u"b")
        children = searchalbum.getChildren()
        assert list(children) == [image2]

    def test_getAlbumChildren(self):
        alpha = self.shelf.getAlbum(u"alpha")
        image1, image2 = list(alpha.getChildren())[0:2]
        cat_a = self.shelf.getCategory(u"a")
        cat_b = self.shelf.getCategory(u"b")
        image1.addCategory(cat_a)
        image2.addCategory(cat_b)
        searchalbum = self.shelf.createAlbum(u"search", u"search")
        assert searchalbum
        searchalbum.setAttribute(u"query", u"b")
        children = searchalbum.getAlbumChildren()
        assert list(children) == []

    def test_setChildren(self):
        searchalbum = self.shelf.createAlbum(u"search", u"search")
        try:
            searchalbum.setChildren([])
        except UnsettableChildrenError:
            pass
        else:
            assert False

    def test_isAlbum(self):
        assert self.shelf.getAlbum(u"orphans").isAlbum()

######################################################################

removeTmpDb()
if __name__ == "__main__":
    unittest.main()
