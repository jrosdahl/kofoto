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
        os.path.join(os.path.dirname(sys.argv[0]), "..", "packages")))
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
        assert s.getAlbumByTag(u"foo")
        s.commit()
        s = Shelf(db, codeset)
        s.begin()
        assert s.getAlbumByTag(u"foo")
        s.rollback()

    def test_rollback(self):
        s = Shelf(db, codeset)
        s.create()
        s.begin()
        s.createAlbum(u"foo")
        s.rollback()
        s.begin()
        try:
            s.getAlbumByTag(u"foo")
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
            image = self.shelf.createImage()
            imageversion = self.shelf.createImageVersion(
                image, loc, ImageVersionType.Original)
            children.append(image)
        del children[-1] # The last image becomes orphaned.
        alpha.setChildren(children)
        beta.setChildren(list(beta.getChildren()) + [children[-1]])
        root.setChildren(list(root.getChildren()) + [alpha, beta])
        self.shelf.createAlbum(u"epsilon", AlbumType.Plain) # Orphaned album.
        zeta = self.shelf.createAlbum(u"zeta", AlbumType.Search)
        zeta.setAttribute(u"query", u"a")
        root.setChildren(list(root.getChildren()) + [zeta])

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
        assert s["nalbums"] == 6
        assert s["nimages"] == 11
        assert s["nimageversions"] == 11

    def test_createdObjects(self):
        root = self.shelf.getRootAlbum()
        children = list(root.getChildren())
        assert len(children) == 4
        orphans, alpha, beta, zeta = children
        assert self.shelf.getAlbum(alpha.getId()) == alpha
        assert self.shelf.getAlbumByTag(u"beta") == beta
        assert len(list(alpha.getChildren())) == 11
        assert len(list(beta.getChildren())) == 1

    def test_createdAttributes(self):
        imageversion = self.shelf.getImageVersionByLocation(
            os.path.join(PICDIR, "Canon_Digital_IXUS.jpg"))
        image = imageversion.getImage()
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
        album = self.shelf.getAlbum(0)
        assert album == self.shelf.getRootAlbum()

    def test_negativeGetAlbum(self):
        try:
            self.shelf.getAlbum(12345678)
        except AlbumDoesNotExistError:
            pass
        else:
            assert False

    def test_getAlbumByTag(self):
        album = self.shelf.getAlbumByTag(u"root")
        assert album == self.shelf.getRootAlbum()

    def test_negativeGetAlbumByTag(self):
        try:
            self.shelf.getAlbum(u"12345678")
        except AlbumDoesNotExistError:
            pass
        else:
            assert False

    def test_getRootAlbum(self):
        root = self.shelf.getRootAlbum()
        assert root.getId() == 0
        assert root == self.shelf.getAlbumByTag(u"root")

    def test_getAllAlbums(self):
        albums = list(self.shelf.getAllAlbums())
        assert len(albums) == 6

    def test_getAllImageVersions(self):
        imageversions = list(self.shelf.getAllImageVersions())
        assert len(imageversions) == 11

    def test_getImageVersionsInDirectory(self):
        self.shelf.flushImageVersionCache()

        imageversions = list(self.shelf.getImageVersionsInDirectory(u"."))
        assert len(imageversions) == 0

        # Image versions not in cache.
        imageversions = list(self.shelf.getImageVersionsInDirectory(PICDIR))
        assert len(imageversions) == 11

        # Image versions in cache.
        imageversions = list(self.shelf.getImageVersionsInDirectory(PICDIR))
        assert len(imageversions) == 11

    def test_deleteAlbum(self):
        album = self.shelf.getAlbumByTag(u"beta")
        self.shelf.deleteAlbum(album.getId())

    def test_negativeRootAlbumDeletion(self):
        root = self.shelf.getRootAlbum()
        try:
            self.shelf.deleteAlbum(root.getId())
        except UndeletableAlbumError:
            pass
        else:
            assert False

    def test_negativeAlbumDeletion(self):
        try:
            self.shelf.deleteAlbum(12345678)
        except AlbumDoesNotExistError:
            pass
        else:
            assert False

    def test_negativeImageCreation(self):
        try:
            image = self.shelf.createImage()
            self.shelf.createImageVersion(
                image,
                os.path.join(PICDIR, "arlaharen.png"),
                ImageVersionType.Original)
        except ImageVersionExistsError:
            pass
        else:
            assert False

    def test_getImage(self):
        imageversion = self.shelf.getImageVersionByLocation(
            os.path.join(PICDIR, "arlaharen.png"))
        image = imageversion.getImage()
        assert self.shelf.getImage(image.getId()) == image

    def test_negativeGetImage(self):
        try:
            self.shelf.getImage(12345678)
        except ImageDoesNotExistError:
            pass
        else:
            assert False

    def test_getImageVersion(self):
        imageversion = self.shelf.getImageVersionByLocation(
            os.path.join(PICDIR, "arlaharen.png"))
        assert self.shelf.getImageVersion(imageversion.getId()) == imageversion

    def test_negativeGetImageVersion(self):
        try:
            self.shelf.getImageVersion(12345678)
        except ImageVersionDoesNotExistError:
            pass
        else:
            assert False

    def test_getImageVersionByHash(self):
        imageversion = self.shelf.getImageVersionByLocation(
            os.path.join(PICDIR, "arlaharen.png"))
        assert self.shelf.getImageVersionByHash(
            imageversion.getHash()) == imageversion

    def test_negativeGetImageVersionByHash(self):
        try:
            self.shelf.getImageVersion(u"badhash")
        except ImageVersionDoesNotExistError:
            pass
        else:
            assert False

    def test_getImageVersionByLocation(self):
        imageversion1 = self.shelf.getImageVersionByLocation(
            os.path.join(PICDIR, u"arlaharen.png"))
        currentDir = os.getcwd()
        try:
            os.chdir(PICDIR)
            imageversion2 = self.shelf.getImageVersionByLocation(
                u"arlaharen.png")
        finally:
            os.chdir(currentDir)
        assert imageversion1 == imageversion2

    def test_negativeGetImageVersionByHash(self):
        try:
            self.shelf.getImageVersionByLocation(u"/bad/location")
        except ImageVersionDoesNotExistError:
            pass
        else:
            assert False

    def test_deleteImage(self):
        imageversion = self.shelf.getImageVersionByLocation(
            os.path.join(PICDIR, "arlaharen.png"))
        imageid = imageversion.getImage().getId()
        self.shelf.deleteImage(imageid)
        try:
            self.shelf.getImageVersionByLocation(
                os.path.join(PICDIR, "arlaharen.png"))
        except ImageVersionDoesNotExistError:
            pass
        else:
            assert False

    def test_negativeImageDeletion(self):
        try:
            self.shelf.deleteImage(12345678)
        except ImageDoesNotExistError:
            pass
        else:
            assert False

    def test_deleteImageVersion(self):
        imageversion = self.shelf.getImageVersionByLocation(
            os.path.join(PICDIR, "arlaharen.png"))
        self.shelf.deleteImageVersion(imageversion.getId())

    def test_negativeImageVersionDeletion(self):
        try:
            self.shelf.deleteImageVersion(12345678)
        except ImageVersionDoesNotExistError:
            pass
        else:
            assert False

    def test_getObject(self):
        rootalbum = self.shelf.getRootAlbum()
        album = self.shelf.getObject(rootalbum.getId())
        assert album == rootalbum

    def test_deleteObject(self):
        albumid = self.shelf.getAlbumByTag(u"beta").getId()
        imageversion = self.shelf.getImageVersionByLocation(
            os.path.join(PICDIR, "arlaharen.png"))
        imageid = imageversion.getImage().getId()
        self.shelf.deleteObject(albumid)
        self.shelf.deleteObject(imageid)
        try:
            self.shelf.getAlbum(albumid)
        except AlbumDoesNotExistError:
            pass
        else:
            assert False
        try:
            self.shelf.getImage(imageid)
        except ImageDoesNotExistError:
            pass
        else:
            assert False

    def test_getAllAttributeNames(self):
        attrnames = list(self.shelf.getAllAttributeNames())
        attrnames.sort()
        assert attrnames == [
            "cameramake", "cameramodel", "captured", "description",
            "digitalzoom", "exposurebias", "exposureprogram", "exposuretime",
            "flash", "fnumber", "focallength", "iso", "orientation", "query",
            "title"
            ], attrnames

    def test_getCategory(self):
        category = self.shelf.getCategory(1)
        assert category.getId() == 1

    def test_getCategoryByTag(self):
        category = self.shelf.getCategoryByTag(u"a")
        assert category.getTag() == u"a"

    def test_negativeCreateCategory(self):
        try:
            self.shelf.createCategory(u"a", u"Foo")
        except CategoryExistsError:
            pass
        else:
            assert False

    def test_deleteCategory(self):
        category = self.shelf.getCategoryByTag(u"a")
        self.shelf.deleteCategory(category.getId())

    def test_negativeDeleteCategory(self):
        try:
            self.shelf.deleteCategory(12345678)
        except CategoryDoesNotExistError:
            pass
        else:
            assert False

    def test_getRootCategories(self):
        categories = list(self.shelf.getRootCategories())
        cat_a = self.shelf.getCategoryByTag(u"a")
        cat_events = self.shelf.getCategoryByTag(u"events")
        cat_locations = self.shelf.getCategoryByTag(u"locations")
        cat_people = self.shelf.getCategoryByTag(u"people")
        categories.sort(lambda x, y: cmp(x.getTag(), y.getTag()))
        assert categories == [cat_a, cat_events, cat_locations, cat_people], \
               categories

class TestCategory(TestShelfFixture):
    def test_categoryMethods(self):
        cat_a = self.shelf.getCategoryByTag(u"a")
        cat_b = self.shelf.getCategoryByTag(u"b")
        cat_c = self.shelf.getCategoryByTag(u"c")
        cat_d = self.shelf.getCategoryByTag(u"d")

        assert self.shelf.getCategory(cat_a.getId()) == cat_a
        cat_a.setTag(u"foo")
        assert self.shelf.getCategoryByTag(u"foo") == cat_a

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
        cat_a = self.shelf.getCategoryByTag(u"a")
        cat_b = self.shelf.getCategoryByTag(u"b")
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
        cat_a = self.shelf.getCategoryByTag(u"a")
        cat_b = self.shelf.getCategoryByTag(u"b")
        cat_a.disconnectChild(cat_b)
        assert not cat_a.isParentOf(cat_b)

    def test_negativeCategoryDisconnectChild(self):
        cat_a = self.shelf.getCategoryByTag(u"a")
        cat_d = self.shelf.getCategoryByTag(u"d")
        cat_a.disconnectChild(cat_d) # No exception.

class TestObject(TestShelfFixture):
    def test_getParents(self):
        root = self.shelf.getRootAlbum()
        alpha = self.shelf.getAlbumByTag(u"alpha")
        beta = self.shelf.getAlbumByTag(u"beta")
        parents = list(beta.getParents())
        parents.sort(lambda x, y: cmp(x.getTag(), y.getTag()))
        assert parents == [alpha, root]

    def test_getAttribute(self):
        orphans = self.shelf.getAlbumByTag(u"orphans")
        assert orphans.getAttribute(u"title")
        assert orphans.getAttribute(u"description")
        orphans.getAttributeMap() # Just populate the cache.
        assert not orphans.getAttribute(u"nonexisting")
        assert u"nonexisting" not in orphans.getAttributeMap()

    def test_getAttributeMap(self):
        orphans = self.shelf.getAlbumByTag(u"orphans")
        map = orphans.getAttributeMap()
        assert "description" in map
        assert "title" in map

    def test_getAttributeNames(self):
        orphans = self.shelf.getAlbumByTag(u"orphans")
        names = list(orphans.getAttributeNames())
        names.sort()
        assert names == ["description", "title"]

    def test_setAttribute(self):
        orphans = self.shelf.getAlbumByTag(u"orphans")
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
        orphans = self.shelf.getAlbumByTag(u"orphans")
        orphans.deleteAttribute(u"nonexisting") # No exception.
        assert orphans.getAttribute(u"title")
        orphans.deleteAttribute(u"title")
        orphans.getAttributeMap() # Just populate the cache.
        assert not orphans.getAttribute(u"title")
        assert u"title" not in orphans.getAttributeMap()

    def test_addCategory(self):
        orphans = self.shelf.getAlbumByTag(u"orphans")
        cat_a = self.shelf.getCategoryByTag(u"a")
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
        orphans = self.shelf.getAlbumByTag(u"orphans")
        assert list(orphans.getCategories()) == []
        cat_a = self.shelf.getCategoryByTag(u"a")
        orphans.addCategory(cat_a)
        assert list(orphans.getCategories()) == [cat_a]
        orphans.removeCategory(cat_a)
        assert list(orphans.getCategories()) == []

    def test_deleteCategoryInvalidatesCategoryCache(self):
        orphans = self.shelf.getAlbumByTag(u"orphans")
        assert list(orphans.getCategories()) == []
        cat_a = self.shelf.getCategoryByTag(u"a")
        orphans.addCategory(cat_a)
        assert list(orphans.getCategories()) == [cat_a]
        self.shelf.deleteCategory(cat_a.getId())
        assert list(orphans.getCategories()) == []

class TestAlbum(TestShelfFixture):
    def test_getType(self):
        alpha = self.shelf.getAlbumByTag(u"alpha")
        assert alpha.getType() == AlbumType.Plain

    def test_isMutable(self):
        alpha = self.shelf.getAlbumByTag(u"alpha")
        assert alpha.isMutable()

    def test_getTag(self):
        alpha = self.shelf.getAlbumByTag(u"alpha")
        assert alpha.getTag() == u"alpha"

    def test_setTag(self):
        alpha = self.shelf.getAlbumByTag(u"alpha")
        alpha.setTag(u"alfa")
        assert alpha.getTag() == u"alfa"

    def test_getAlbumParents(self):
        root = self.shelf.getRootAlbum()
        alpha = self.shelf.getAlbumByTag(u"alpha")
        parents = list(alpha.getAlbumParents())
        parents.sort(lambda x, y: cmp(x.getTag(), y.getTag()))
        assert parents == [root]

    def test_isAlbum(self):
        assert self.shelf.getRootAlbum().isAlbum()

class TestPlainAlbum(TestShelfFixture):
    def test_getType(self):
        alpha = self.shelf.getAlbumByTag(u"alpha")
        assert alpha.getType() == AlbumType.Plain

    def test_isMutable(self):
        alpha = self.shelf.getAlbumByTag(u"alpha")
        assert alpha.isMutable()

    def test_getChildren(self):
        epsilon = self.shelf.getAlbumByTag(u"epsilon")
        alpha = self.shelf.getAlbumByTag(u"alpha")
        beta = self.shelf.getAlbumByTag(u"beta")
        assert list(epsilon.getChildren()) == []
        alphaChildren = list(alpha.getChildren())
        assert list(beta.getChildren()) == [alphaChildren[-1]]

    def test_getAlbumChildren(self):
        alpha = self.shelf.getAlbumByTag(u"alpha")
        beta = self.shelf.getAlbumByTag(u"beta")
        epsilon = self.shelf.getAlbumByTag(u"epsilon")
        alphaAlbumChildren = list(alpha.getAlbumChildren())
        assert alphaAlbumChildren == [beta]
        assert list(epsilon.getAlbumChildren()) == []

    def test_setChildren(self):
        root = self.shelf.getRootAlbum()
        beta = self.shelf.getAlbumByTag(u"beta")
        assert list(beta.getChildren()) != []
        beta.setChildren([beta, root])
        assert list(beta.getChildren()) == [beta, root]
        beta.setChildren([]) # Break the cycle.
        assert list(beta.getChildren()) == []

class TestImage(TestShelfFixture):
    def test_isAlbum(self):
        imageversion = self.shelf.getImageVersionByLocation(
            os.path.join(PICDIR, "arlaharen.png"))
        assert not imageversion.getImage().isAlbum()

    def test_getImageVersions(self):
        imageversion = self.shelf.getImageVersionByLocation(
            os.path.join(PICDIR, "arlaharen.png"))
        image = imageversion.getImage()
        assert list(image.getImageVersions()) == [imageversion]
        imageversion2 = self.shelf.getImageVersionByLocation(
            os.path.join(PICDIR, "Canon_Digital_IXUS.jpg"))
        imageversion2.setImage(image)
        imageversions = list(image.getImageVersions())
        imageversions.sort(lambda x, y: cmp(x.getHash(), y.getHash()))
        assert list(image.getImageVersions()) == [imageversion, imageversion2]
        self.shelf.deleteImageVersion(imageversion.getId())
        self.shelf.deleteImageVersion(imageversion2.getId())
        assert list(image.getImageVersions()) == []

    def test_getPrimaryVersion(self):
        imageversion = self.shelf.getImageVersionByLocation(
            os.path.join(PICDIR, "arlaharen.png"))
        image = imageversion.getImage()
        assert image.getPrimaryVersion() == imageversion
        imageversion2 = self.shelf.getImageVersionByLocation(
            os.path.join(PICDIR, "Canon_Digital_IXUS.jpg"))
        imageversion2.setImage(image)
        assert image.getPrimaryVersion() == imageversion
        imageversion2.makePrimary()
        assert image.getPrimaryVersion() == imageversion2

        newImage = self.shelf.createImage()
        lastImageVersion = list(image.getImageVersions())[-1]
        lastImageVersion.setImage(newImage)
        assert image.getPrimaryVersion() != lastImageVersion
        assert newImage.getPrimaryVersion() == lastImageVersion
        lastImageVersion.setImage(image)

        self.shelf.deleteImageVersion(imageversion2.getId())
        assert image.getPrimaryVersion() == imageversion
        self.shelf.deleteImageVersion(imageversion.getId())
        assert image.getPrimaryVersion() == None

class TestImageVersion(TestShelfFixture):
    def test_getType(self):
        imageversion = self.shelf.getImageVersionByLocation(
            os.path.join(PICDIR, "arlaharen.png"))
        assert imageversion.getType() == ImageVersionType.Original
        imageversion.setType(ImageVersionType.Important)
        assert imageversion.getType() == ImageVersionType.Important
        imageversion.setType(ImageVersionType.Other)
        assert imageversion.getType() == ImageVersionType.Other
        imageversion.setType(ImageVersionType.Original)
        assert imageversion.getType() == ImageVersionType.Original

    # ImageVersion.makePrimary tested in TestImage.test_getPrimaryVersion.
    # ImageVersion.setImage tested in TestImage.test_getPrimaryVersion.
    # ImageVersion.setType tested in TestImageVersion.test_getType.
    # ImageVersion.setComment tested in TestImageVersion.test_getComment.

    def test_getComment(self):
        imageversion = self.shelf.getImageVersionByLocation(
            os.path.join(PICDIR, "arlaharen.png"))
        assert imageversion.getComment() == ""
        imageversion.setComment(u"a comment")
        assert imageversion.getComment() == u"a comment"

    def test_getHash(self):
        imageversion = self.shelf.getImageVersionByLocation(
            os.path.join(PICDIR, "arlaharen.png"))
        assert imageversion.getHash() == "39a1266d2689f53d48b09a5e0ca0af1f"

    def test_getLocation(self):
        location = os.path.join(PICDIR, "arlaharen.png")
        imageversion = self.shelf.getImageVersionByLocation(location)
        assert imageversion.getLocation() == os.path.realpath(location)

    def test_getModificationTime(self):
        imageversion = self.shelf.getImageVersionByLocation(
            os.path.join(PICDIR, "arlaharen.png"))
        t = imageversion.getModificationTime()
        assert isinstance(t, int)
        assert t > 0

    def test_getSize(self):
        imageversion = self.shelf.getImageVersionByLocation(
            os.path.join(PICDIR, "arlaharen.png"))
        assert imageversion.getSize() == (304, 540)

    def test_contentChanged(self):
        path = os.path.join(PICDIR, "arlaharen.png")
        imageversion = self.shelf.getImageVersionByLocation(path)
        self.shelf.deleteImageVersion(imageversion.getId())
        newpath = u"tmp.png"
        try:
            shutil.copy2(path, newpath)
            newimage = self.shelf.createImage()
            newimageversion = self.shelf.createImageVersion(
                newimage, newpath, ImageVersionType.Original)
            oldmtime = imageversion.getModificationTime()
            pilimg = PILImage.open(newpath)
            pilimg.thumbnail((100, 100))
            pilimg.save(newpath, "PNG")
            newimageversion.contentChanged()
            assert newimageversion.getHash() == "d55a9cc74371c09d484b163c71497cab"
            assert newimageversion.getSize() == (56, 100)
            assert newimageversion.getModificationTime() > oldmtime
        finally:
            try:
                os.unlink(newpath)
            except OSError:
                pass

    def test_locationChanged(self):
        location = os.path.join(PICDIR, "arlaharen.png")
        imageversion = self.shelf.getImageVersionByLocation(location)
        imageversion.locationChanged(u"/foo/../bar")
        assert imageversion.getLocation() == "/bar"

    def test_importExifTags(self):
        imageversion = self.shelf.getImageVersionByLocation(
            os.path.join(PICDIR, "arlaharen.png"))
        imageversion.importExifTags(True) # TODO: Test more.
        imageversion.importExifTags(False) # TODO: Test more.

class TestOrphansAlbum(TestShelfFixture):
    def test_getType(self):
        orphans = self.shelf.getAlbumByTag(u"orphans")
        assert orphans.getType() == AlbumType.Orphans

    def test_isMutable(self):
        orphans = self.shelf.getAlbumByTag(u"orphans")
        assert not orphans.isMutable()

    def test_getChildren(self):
        orphans = self.shelf.getAlbumByTag(u"orphans")
        assert len(list(orphans.getChildren())) == 2

    def test_getAlbumChildren(self):
        orphans = self.shelf.getAlbumByTag(u"orphans")
        epsilon = self.shelf.getAlbumByTag(u"epsilon")
        assert list(orphans.getAlbumChildren()) == [epsilon]

    def test_setChildren(self):
        orphans = self.shelf.getAlbumByTag(u"orphans")
        try:
            orphans.setChildren([])
        except UnsettableChildrenError:
            pass
        else:
            assert False

    def test_isAlbum(self):
        assert self.shelf.getAlbumByTag(u"orphans").isAlbum()

class TestSearchAlbum(TestShelfFixture):
    def test_getType(self):
        zeta = self.shelf.getAlbumByTag(u"zeta")
        assert zeta.getType() == AlbumType.Search

    def test_isMutable(self):
        zeta = self.shelf.getAlbumByTag(u"zeta")
        assert not zeta.isMutable()

    def test_getChildren(self):
        alpha = self.shelf.getAlbumByTag(u"alpha")
        image1, image2 = list(alpha.getChildren())[0:2]
        cat_a = self.shelf.getCategoryByTag(u"a")
        cat_b = self.shelf.getCategoryByTag(u"b")
        image1.addCategory(cat_a)
        image2.addCategory(cat_b)
        zeta = self.shelf.getAlbumByTag(u"zeta")
        assert zeta
        zeta.setAttribute(u"query", u"b")
        children = zeta.getChildren()
        assert list(children) == [image2]

    def test_getAlbumChildren(self):
        alpha = self.shelf.getAlbumByTag(u"alpha")
        image1, image2 = list(alpha.getChildren())[0:2]
        cat_a = self.shelf.getCategoryByTag(u"a")
        cat_b = self.shelf.getCategoryByTag(u"b")
        image1.addCategory(cat_a)
        image2.addCategory(cat_b)
        zeta = self.shelf.getAlbumByTag(u"zeta")
        assert zeta
        zeta.setAttribute(u"query", u"b")
        children = zeta.getAlbumChildren()
        l = list(children)
        assert list(children) == []

    def test_setChildren(self):
        zeta = self.shelf.getAlbumByTag(u"zeta")
        try:
            zeta.setChildren([])
        except UnsettableChildrenError:
            pass
        else:
            assert False

    def test_isAlbum(self):
        assert self.shelf.getAlbumByTag(u"zeta").isAlbum()

######################################################################

removeTmpDb()
if __name__ == "__main__":
    unittest.main()
