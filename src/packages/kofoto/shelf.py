"""Interface to a Kofoto shelf."""

######################################################################
### Public names.

__all__ = [
    "Shelf",
    "computeImageHash",
    "makeValidTag",
    "verifyValidAlbumTag",
    "verifyValidCategoryTag",
]

######################################################################
### Libraries.

import os
import re
import threading
import sqlite as sql
from kofoto.common import UnimplementedError
from kofoto.dag import DAG, LoopError
from kofoto.cachedobject import CachedObject
from kofoto.albumtype import AlbumType
from kofoto.imageversiontype import ImageVersionType
import kofoto.shelfupgrade
import kofoto.shelfschema
from kofoto.shelfexceptions import \
    AlbumDoesNotExistError, \
    AlbumExistsError, \
    BadAlbumTagError, \
    BadCategoryTagError, \
    CategoriesAlreadyConnectedError, \
    CategoryDoesNotExistError, \
    CategoryExistsError, \
    CategoryLoopError, \
    CategoryPresentError, \
    ExifImportError, \
    FailedWritingError, \
    ImageDoesNotExistError, \
    ImageVersionDoesNotExistError, \
    ImageVersionExistsError, \
    MultipleImageVersionsAtOneLocationError, \
    NotAnImageFileError, \
    ObjectDoesNotExistError, \
    ShelfLockedError, \
    ShelfNotFoundError, \
    UndeletableAlbumError, \
    UnknownAlbumTypeError, \
    UnknownImageVersionTypeError, \
    UnsettableChildrenError, \
    UnsupportedShelfError

import warnings
warnings.filterwarnings("ignore", "DB-API extension")
warnings.filterwarnings(
    "ignore",
    ".*losing bits or changing sign will return a long.*",
    FutureWarning)


######################################################################
### Constants.

_ROOT_ALBUM_ID = 0
_SHELF_FORMAT_VERSION = 3


######################################################################
### Public functions.

def computeImageHash(filename):
    """Compute the canonical image ID for an image file."""
    import md5
    m = md5.new()
    f = file(filename, "rb")
    while True:
        data = f.read(2**16)
        if not data:
            break
        m.update(data)
    return unicode(m.hexdigest())


def verifyValidAlbumTag(tag):
    """Verify that an album tag is valid."""
    if not isinstance(tag, (str, unicode)):
        raise BadAlbumTagError(tag)
    try:
        int(tag)
    except ValueError:
        if not tag or tag[0] == "@" or re.search(r"\s", tag):
            raise BadAlbumTagError(tag)
    else:
        raise BadAlbumTagError(tag)


def verifyValidCategoryTag(tag):
    """Verify that a category tag is valid."""
    if not isinstance(tag, (str, unicode)):
        raise BadCategoryTagError(tag)
    try:
        int(tag)
    except ValueError:
        if (not tag or tag[0] == "@" or re.search(r"\s", tag) or
            tag in ["and", "exactly", "not", "or"]):
            raise BadCategoryTagError(tag)
    else:
        raise BadCategoryTagError(tag)


def makeValidTag(tag):
    """Make a string a valid tag.

    Returns the valid tag string.
    """
    tag = tag.lstrip("@")
    tag = re.sub(r"\s", "", tag)
    if re.match("^\d+$", tag):
        tag += u"_"
    if not tag:
        tag = u"_"
    return tag


######################################################################
### Public classes.

class Shelf:
    """A Kofoto shelf."""

    ##############################
    # Public methods.

    def __init__(self, location):
        """Constructor.

        Location is where the database is located.
        """
        self.location = location
        self.transactionLock = threading.Lock()
        self.inTransaction = False
        self.objectcache = {}
        self.imageversioncache = {}
        self.categorycache = {}
        self.orphanAlbumsCache = None
        self.orphanImagesCache = None
        self.modified = False
        self.modificationCallbacks = []
        if False: # Set to True for debug log.
            self.logfile = file("sql.log", "a")
        else:
            self.logfile = None
        self.connection = None
        self.categorydag = None


    def create(self):
        """Create the shelf."""
        assert not self.inTransaction
        if os.path.exists(self.location):
            raise FailedWritingError(self.location)
        try:
            self.connection = _UnicodeConnectionDecorator(
                sql.connect(self.location,
                            client_encoding="UTF-8",
                            command_logfile=self.logfile),
                "UTF-8")
        except sql.DatabaseError:
            raise FailedWritingError(self.location)
        self._createShelf()


    def isUpgradable(self):
        """Check whether the database format is upgradable.

        This method must currently be called outside a transaction.

        If this method returns True, run Shelf.tryUpgrade.
        """
        assert not self.inTransaction
        return kofoto.shelfupgrade.isUpgradable(self.location)


    def tryUpgrade(self):
        """Try to upgrade the database to a newer format.

        This method must currently be called outside a transaction.

        Returns True if upgrade was successful, otherwise False.
        """
        assert not self.inTransaction
        return kofoto.shelfupgrade.tryUpgrade(
            self.location, _SHELF_FORMAT_VERSION)


    def begin(self):
        """Begin working with the shelf."""
        assert not self.inTransaction
        self.transactionLock.acquire()
        self.inTransaction = True
        if not os.path.exists(self.location):
            raise ShelfNotFoundError(self.location)
        try:
            self.connection = _UnicodeConnectionDecorator(
                sql.connect(self.location,
                            client_encoding="UTF-8",
                            command_logfile=self.logfile),
                "UTF-8")
        except sql.OperationalError:
            raise ShelfLockedError(self.location)
        except sql.DatabaseError:
            raise ShelfNotFoundError(self.location)
        self.categorydag = CachedObject(_createCategoryDAG, (self.connection,))
        try:
            self._openShelf() # Starts the SQLite transaction.
        except:
            self.inTransaction = False
            self.transactionLock.release()
            raise


    def commit(self):
        """Commit the work on the shelf."""
        assert self.inTransaction
        try:
            self.connection.commit()
        finally:
            self.flushCategoryCache()
            self.flushObjectCache()
            self.flushImageVersionCache()
            self._unsetModified()
            self.inTransaction = False
            self.transactionLock.release()


    def rollback(self):
        """Abort the work on the shelf.

        The changes (if any) will not be saved."""
        assert self.inTransaction
        try:
            self.connection.rollback()
        finally:
            self.flushCategoryCache()
            self.flushObjectCache()
            self.flushImageVersionCache()
            self._unsetModified()
            self.inTransaction = False
            self.transactionLock.release()


    def isModified(self):
        """Check whether the shelf has uncommited changes."""
        assert self.inTransaction
        return self.modified


    def registerModificationCallback(self, callback):
        """Register a function that will be called when the
        modification status changes.

        The function will receive a single argument: True if the shelf
        has been modified, otherwise False. """
        self.modificationCallbacks.append(callback)


    def unregisterModificationCallback(self, callback):
        """Unregister a modification callback function."""
        try:
            self.modificationCallbacks.remove(callback)
        except ValueError:
            pass


    def flushCategoryCache(self):
        """Flush the category cache."""
        assert self.inTransaction
        self.categorydag.invalidate()
        self.categorycache = {}


    def flushObjectCache(self):
        """Flush the object cache."""
        assert self.inTransaction
        self.objectcache = {}
        self.orphanAlbumsCache = None
        self.orphanImagesCache = None


    def flushImageVersionCache(self):
        """Flush the image version cache."""
        assert self.inTransaction
        self.imageversioncache = {}


    def getStatistics(self):
        """Get statistics about the metadata database.

        The returned value is a mapping with the following keys:

        nalbums        -- Number of albums.
        ncategories    -- Number of categories.
        nimages        -- Number of images.
        nimageversions -- Number of image versions.
        """
        assert self.inTransaction
        cursor = self.connection.cursor()
        cursor.execute(
            " select count(*)"
            " from   album")
        nalbums = int(cursor.fetchone()[0])
        cursor.execute(
            " select count(*)"
            " from   category")
        ncategories = int(cursor.fetchone()[0])
        cursor.execute(
            " select count(*)"
            " from   image")
        nimages = int(cursor.fetchone()[0])
        cursor.execute(
            " select count(*)"
            " from   image_version")
        nimageversions = int(cursor.fetchone()[0])
        return {
            "nalbums": nalbums,
            "ncategories": ncategories,
            "nimages": nimages,
            "nimageversions": nimageversions,
            }


    def createAlbum(self, tag, albumtype=AlbumType.Plain):
        """Create an empty, orphaned album.

        Returns an Album instance."""
        assert self.inTransaction
        verifyValidAlbumTag(tag)
        cursor = self.connection.cursor()
        try:
            cursor.execute(
                " insert into object (id)"
                " values (null)")
            lastrowid = cursor.lastrowid
            cursor.execute(
                " insert into album (id, tag, deletable, type)"
                " values (%s, %s, 1, %s)",
                lastrowid,
                tag,
                _albumTypeToIdentifier(albumtype))
            self._setModified()
            self.orphanAlbumsCache = None
            return self.getAlbum(lastrowid)
        except sql.IntegrityError:
            cursor.execute(
                " delete from object"
                " where id = %s",
                cursor.lastrowid)
            raise AlbumExistsError(tag)


    def getAlbum(self, albumid):
        """Get the album for a given album ID.

        Returns an Album instance.
        """
        assert self.inTransaction
        if albumid in self.objectcache:
            album = self.objectcache[albumid]
            if not album.isAlbum():
                raise AlbumDoesNotExistError(albumid)
            return album
        cursor = self.connection.cursor()
        cursor.execute(
            " select id, tag, type"
            " from   album"
            " where  id = %s",
            albumid)
        row = cursor.fetchone()
        if not row:
            raise AlbumDoesNotExistError(albumid)
        albumid, tag, albumtype = row
        albumtype = _albumTypeIdentifierToType(albumtype)
        album = self._albumFactory(albumid, tag, albumtype)
        return album


    def getAlbumByTag(self, tag):
        """Get the album for a given album tag.

        Returns an Album instance.
        """
        assert self.inTransaction
        cursor = self.connection.cursor()
        cursor.execute(
            " select id"
            " from   album"
            " where  tag = %s",
            tag)
        row = cursor.fetchone()
        if not row:
            raise AlbumDoesNotExistError(tag)
        return self.getAlbum(int(row[0]))


    def getRootAlbum(self):
        """Get the root album.

        Returns an Album instance.
        """
        assert self.inTransaction
        return self.getAlbum(_ROOT_ALBUM_ID)


    def getAllAlbums(self):
        """Get all albums in the shelf (unsorted).

        Returns an iterable returning the albums."""
        assert self.inTransaction
        cursor = self.connection.cursor()
        cursor.execute(
            " select id, tag, type"
            " from   album")
        for albumid, tag, albumtype in cursor:
            if albumid in self.objectcache:
                yield self.objectcache[albumid]
            else:
                albumtype = _albumTypeIdentifierToType(albumtype)
                yield self._albumFactory(albumid, tag, albumtype)


    def getAllImages(self):
        """Get all images in the shelf (unsorted).

        Returns an iterable returning the images."""
        assert self.inTransaction
        cursor = self.connection.cursor()
        cursor.execute(
            " select id, primary_version"
            " from   image")
        for (imageid, primary_version_id) in cursor:
            if imageid in self.objectcache:
                yield self.objectcache[imageid]
            else:
                yield self._imageFactory(imageid, primary_version_id)


    def getAllImageVersions(self):
        """Get all image versions in the shelf (unsorted).

        Returns an iterable returning the image versions."""
        assert self.inTransaction
        cursor = self.connection.cursor()
        cursor.execute(
            " select id, image, type, hash, directory, filename, mtime,"
            "        width, height, comment"
            " from   image_version")
        for (ivid, imageid, ivtype, ivhash, directory,
             filename, mtime, width, height, comment) in cursor:
            location = os.path.join(directory, filename)
            if ivid in self.imageversioncache:
                yield self.imageversioncache[ivid]
            else:
                ivtype = _imageVersionTypeIdentifierToType(ivtype)
                yield self._imageVersionFactory(
                    ivid, imageid, ivtype, ivhash, location, mtime,
                    width, height, comment)


    def getImageVersionsInDirectory(self, directory):
        """Get all image versions that are expected to be in a given
        directory (unsorted).

        Returns an iterable returning the image versions."""
        assert self.inTransaction
        directory = unicode(os.path.realpath(directory))
        cursor = self.connection.cursor()
        cursor.execute(
            " select id, image, type, hash, directory, filename, mtime,"
            "        width, height, comment"
            " from   image_version"
            " where  directory = %s",
            directory)
        for (ivid, imageid, ivtype, ivhash, directory, filename,
             mtime, width, height, comment) in cursor:
            location = os.path.join(directory, filename)
            if ivid in self.imageversioncache:
                yield self.imageversioncache[ivid]
            else:
                ivtype = _imageVersionTypeIdentifierToType(ivtype)
                yield self._imageVersionFactory(
                    ivid, imageid, ivtype, ivhash, location, mtime,
                    width, height, comment)


    def deleteAlbum(self, albumid):
        """Delete an album."""
        assert self.inTransaction
        cursor = self.connection.cursor()
        cursor.execute(
            " select id, tag"
            " from   album"
            " where  id = %s",
            albumid)
        row = cursor.fetchone()
        if not row:
            raise AlbumDoesNotExistError(albumid)
        albumid, tag = row
        if albumid == _ROOT_ALBUM_ID:
            # Don't delete the root album!
            raise UndeletableAlbumError(tag)
        cursor.execute(
            " delete from album"
            " where  id = %s",
            albumid)
        self._deleteObjectFromParents(albumid)
        cursor.execute(
            " delete from member"
            " where  album = %s",
            albumid)
        cursor.execute(
            " delete from object"
            " where  id = %s",
            albumid)
        cursor.execute(
            " delete from attribute"
            " where  object = %s",
            albumid)
        cursor.execute(
            " delete from object_category"
            " where  object = %s",
            albumid)
        if albumid in self.objectcache:
            del self.objectcache[albumid]
        self._setModified()
        self.orphanAlbumsCache = None


    def createImage(self):
        """Create a new, orphaned image.

        Returns an Image instance."""
        assert self.inTransaction
        cursor = self.connection.cursor()
        cursor.execute(
            " insert into object (id)"
            " values (null)")
        imageid = cursor.lastrowid
        cursor.execute(
            " insert into image (id, primary_version)"
            " values (%s, NULL)",
            imageid)
        self._setModified()
        self.orphanImagesCache = None
        return self.getImage(imageid)


    def getImage(self, imageid):
        """Get the image for a given ID.

        Returns an Image instance.
        """
        assert self.inTransaction
        if imageid in self.objectcache:
            image = self.objectcache[imageid]
            if image.isAlbum():
                raise ImageDoesNotExistError(imageid)
            return image
        cursor = self.connection.cursor()
        cursor.execute(
            " select id, primary_version"
            " from   image"
            " where  id = %s",
            imageid)
        row = cursor.fetchone()
        if not row:
            raise ImageDoesNotExistError(imageid)
        imageid, primary_version_id = row
        image = self._imageFactory(imageid, primary_version_id)
        return image


    def createImageVersion(self, image, location, ivtype):
        """Create a new image version.

        Returns an ImageVersion instance."""
        assert ivtype in ImageVersionType
        assert self.inTransaction
        import Image as PILImage
        try:
            pilimg = PILImage.open(location)
            if not pilimg.mode in ("L", "RGB", "CMYK"):
                pilimg = pilimg.convert("RGB")
#        except IOError:
        except: # Work-around for buggy PIL.
            raise NotAnImageFileError(location)
        width, height = pilimg.size
        location = os.path.realpath(location)
        mtime = os.path.getmtime(location)
        ivhash = computeImageHash(location)
        cursor = self.connection.cursor()
        try:
            cursor.execute(
                " insert into image_version"
                "     (image, type, hash, directory, filename,"
                "      mtime, width, height, comment)"
                " values"
                "     (%s, %s, %s, %s, %s, %s, %s, %s, '')",
                image.getId(),
                _imageVersionTypeToIdentifier(ivtype),
                ivhash,
                os.path.dirname(location),
                os.path.basename(location),
                mtime,
                width,
                height)
        except sql.IntegrityError:
            raise ImageVersionExistsError(location)
        ivid = cursor.lastrowid
        imageversion = self._imageVersionFactory(
            ivid, image.getId(), ivtype, ivhash, location, mtime,
            width, height, u"")
        try:
            imageversion.importExifTags(False)
        except ExifImportError:
            # Ignore exceptions from buggy EXIF library for now.
            pass
        if image.getPrimaryVersion() == None:
            image._makeNewPrimaryVersion()
        self._setModified()
        return imageversion


    def getImageVersion(self, ivid):
        """Get the image version for a given ID.

        Returns an ImageVersion instance.
        """
        assert self.inTransaction

        if ivid in self.imageversioncache:
            return self.imageversioncache[ivid]

        cursor = self.connection.cursor()
        cursor.execute(
            " select id, image, type, hash, directory, filename, mtime,"
            "        width, height, comment"
            " from   image_version"
            " where  id = %s",
            ivid)
        row = cursor.fetchone()
        if not row:
            raise ImageVersionDoesNotExistError(ivid)
        ivid, imageid, ivtype, ivhash, directory, filename, mtime, \
            width, height, comment = row
        location = os.path.join(directory, filename)
        ivtype = _imageVersionTypeIdentifierToType(ivtype)
        return self._imageVersionFactory(
            ivid, imageid, ivtype, ivhash, location, mtime,
            width, height, comment)


    def getImageVersionByHash(self, ivhash):
        """Get the image version for a given hash.

        Returns an ImageVersion instance.
        """
        assert self.inTransaction

        cursor = self.connection.cursor()
        cursor.execute(
            " select id"
            " from   image_version"
            " where  hash = %s",
            ivhash)
        row = cursor.fetchone()
        if not row:
            raise ImageVersionDoesNotExistError(ivhash)
        return self.getImageVersion(row[0])


    def getImageVersionByLocation(self, location):
        """Get the image version for a given location.

        Note, though, that an image location is not required to be
        unique in the shelf; if several image versions have the same
        location, MultipleImageVersionsAtOneLocationError is raised.

        Returns an ImageVersion instance.
        """
        assert self.inTransaction

        location = os.path.abspath(location)
        cursor = self.connection.cursor()
        cursor.execute(
            " select id"
            " from   image_version"
            " where  directory = %s and filename = %s",
            os.path.dirname(location),
            os.path.basename(location))
        if cursor.rowcount > 1:
            raise MultipleImageVersionsAtOneLocationError(location)
        row = cursor.fetchone()
        if not row:
            raise ImageVersionDoesNotExistError(location)
        return self.getImageVersion(row[0])


    def deleteImage(self, imageid):
        """Delete an image."""
        assert self.inTransaction

        cursor = self.connection.cursor()
        cursor.execute(
            " select 1"
            " from   image"
            " where  id = %s",
            imageid)
        if cursor.rowcount == 0:
            raise ImageDoesNotExistError(imageid)
        cursor.execute(
            " select id"
            " from   image_version"
            " where  image = %s",
            imageid)
        for (ivid,) in cursor:
            if ivid in self.imageversioncache:
                del self.imageversioncache[ivid]
        cursor.execute(
            " delete from image_version"
            " where  image = %s",
            imageid)
        cursor.execute(
            " delete from image"
            " where  id = %s",
            imageid)
        self._deleteObjectFromParents(imageid)
        cursor.execute(
            " delete from object"
            " where  id = %s",
            imageid)
        cursor.execute(
            " delete from attribute"
            " where  object = %s",
            imageid)
        cursor.execute(
            " delete from object_category"
            " where  object = %s",
            imageid)
        if imageid in self.objectcache:
            del self.objectcache[imageid]
        self._setModified()
        self.orphanImagesCache = None


    def deleteImageVersion(self, ivid):
        """Delete an image version."""
        assert self.inTransaction

        image = self.getImageVersion(ivid).getImage()
        primary_version_id = image.getPrimaryVersion().getId()
        cursor = self.connection.cursor()
        cursor.execute(
            " delete from image_version"
            " where  id = %s",
            ivid)
        if primary_version_id == ivid:
            image._makeNewPrimaryVersion()
        if ivid in self.imageversioncache:
            del self.imageversioncache[ivid]
        self._setModified()


    def getObject(self, objid):
        """Get the object for a given object ID."""
        assert self.inTransaction
        if objid in self.objectcache:
            return self.objectcache[objid]
        try:
            return self.getImage(objid)
        except ImageDoesNotExistError:
            try:
                return self.getAlbum(objid)
            except AlbumDoesNotExistError:
                raise ObjectDoesNotExistError(objid)


    def deleteObject(self, objid):
        """Get the object for a given object ID."""
        assert self.inTransaction
        try:
            self.deleteImage(objid)
        except ImageDoesNotExistError:
            try:
                self.deleteAlbum(objid)
            except AlbumDoesNotExistError:
                raise ObjectDoesNotExistError(objid)


    def getAllAttributeNames(self):
        """Get all used attribute names in the shelf (sorted).

        Returns an iterable returning the attribute names."""
        assert self.inTransaction
        cursor = self.connection.cursor()
        cursor.execute(
            " select distinct name"
            " from   attribute"
            " order by name")
        for (name,) in cursor:
            yield name


    def createCategory(self, tag, desc):
        """Create a category.

        Returns a Category instance."""
        assert self.inTransaction
        verifyValidCategoryTag(tag)
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                " insert into category (tag, description)"
                " values (%s, %s)",
                tag,
                desc)
            self.categorydag.get().add(cursor.lastrowid)
            self._setModified()
            return self.getCategory(cursor.lastrowid)
        except sql.IntegrityError:
            raise CategoryExistsError(tag)


    def deleteCategory(self, catid):
        """Delete a category for a given category ID."""
        assert self.inTransaction

        cursor = self.connection.cursor()
        cursor.execute(
            " select tag"
            " from   category"
            " where  id = %s",
            catid)
        row = cursor.fetchone()
        if not row:
            raise CategoryDoesNotExistError(catid)
        cursor.execute(
            " delete from category_child"
            " where  parent = %s",
            catid)
        cursor.execute(
            " delete from category_child"
            " where  child = %s",
            catid)
        cursor.execute(
            " select object from object_category"
            " where  category = %s",
            catid)
        for (objectid,) in cursor:
            if objectid in self.objectcache:
                self.objectcache[objectid]._categoriesDirty()
        cursor.execute(
            " delete from object_category"
            " where  category = %s",
            catid)
        cursor.execute(
            " delete from category"
            " where  id = %s",
            catid)
        catdag = self.categorydag.get()
        if catid in catdag:
            catdag.remove(catid)
        if catid in self.categorycache:
            del self.categorycache[catid]
        self._setModified()


    def getCategory(self, catid):
        """Get a category for a given category tag/ID.

        Returns a Category instance."""
        assert self.inTransaction

        if catid in self.categorycache:
            return self.categorycache[catid]
        cursor = self.connection.cursor()
        cursor.execute(
            " select tag, description"
            " from   category"
            " where  id = %s",
            catid)
        row = cursor.fetchone()
        if not row:
            raise CategoryDoesNotExistError(catid)
        tag, desc = row
        category = Category(self, catid, tag, desc)
        self.categorycache[catid] = category
        return category


    def getCategoryByTag(self, tag):
        """Get a category for a given category tag.

        Returns a Category instance."""
        assert self.inTransaction

        cursor = self.connection.cursor()
        cursor.execute(
            " select id"
            " from   category"
            " where  tag = %s",
            tag)
        row = cursor.fetchone()
        if not row:
            raise CategoryDoesNotExistError(tag)
        return self.getCategory(row[0])


    def getRootCategories(self):
        """Get the categories that are roots, i.e. have no parents.

        Returns an iterable returning Category instances."""
        assert self.inTransaction
        for catid in self.categorydag.get().getRoots():
            yield self.getCategory(catid)


    def getMatchingCategories(self, regexp):
        """Get the categories that case insensitively match a given
        compiled regexp object.

        Returns an iterable returning Category instances."""
        assert self.inTransaction
        for catid in self.categorydag.get():
            category = self.getCategory(catid)
            if (regexp.match(category.getTag().lower()) or
                regexp.match(category.getDescription().lower())):
                yield category


    def search(self, searchtree):
        """Search for objects matching a search node tree.

        Use kofoto.search.Parser to construct a search node tree from
        a string.

        Returns an iterable returning the objects."""
        assert self.inTransaction
        cursor = self.connection.cursor()
        cursor.execute(searchtree.getQuery())
        for (objid,) in cursor:
            yield self.getObject(objid)

    ##############################
    # Internal methods.

    def _createShelf(self):
        """Helper method for Shelf.create."""
        cursor = self.connection.cursor()
        cursor.execute(kofoto.shelfschema.schema)
        cursor.execute(
            " insert into dbinfo (version)"
            " values (%s)",
            _SHELF_FORMAT_VERSION)
        cursor.execute(
            " insert into object (id)"
            " values (%s)",
            _ROOT_ALBUM_ID)
        cursor.execute(
            " insert into album (id, tag, deletable, type)"
            " values (%s, %s, 0, 'plain')",
            _ROOT_ALBUM_ID,
            u"root")
        self.connection.commit()

        self.begin()
        rootalbum = self.getRootAlbum()
        rootalbum.setAttribute(u"title", u"Root album")
        orphansalbum = self.createAlbum(u"orphans", AlbumType.Orphans)
        orphansalbum.setAttribute(u"title", u"Orphans")
        orphansalbum.setAttribute(
            u"description",
            u"This album contains albums and images that are not" +
            u" linked from any album.")
        self.getRootAlbum().setChildren([orphansalbum])
        self.createCategory(u"events", u"Events")
        self.createCategory(u"locations", u"Locations")
        self.createCategory(u"people", u"People")
        self.commit()


    def _openShelf(self):
        """Helper method for Shelf.open."""
        cursor = self.connection.cursor()
        try:
            cursor.execute(
                " select version"
                " from   dbinfo")
        except sql.OperationalError:
            raise ShelfLockedError(self.location)
        except sql.DatabaseError:
            raise UnsupportedShelfError(self.location)
        version = cursor.fetchone()[0]
        if version != _SHELF_FORMAT_VERSION:
            raise UnsupportedShelfError(self.location)


    def _albumFactory(self, albumid, tag, albumtype):
        """Factory method for creating Album instances.

        Arguments:

        albumid   -- ID of the album.
        tag       -- Tag of the album.
        albumtype -- An instance of the AlbumType alternative.
        """
        albumtypemap = {
            AlbumType.Orphans: OrphansAlbum,
            AlbumType.Plain: PlainAlbum,
            AlbumType.Search: SearchAlbum,
        }
        album = albumtypemap[albumtype](self, albumid, tag, albumtype)
        self.objectcache[albumid] = album
        return album


    def _imageFactory(self, imageid, primary_version_id):
        """Factory method for creating Image instances.

        Arguments:

        imageid            -- ID of the image.
        primary_version_id -- ID of the primary image version.
        """
        image = Image(self, imageid, primary_version_id)
        self.objectcache[imageid] = image
        return image


    def _imageVersionFactory(self, ivid, imageid, ivtype, ivhash,
                             location, mtime, width, height, comment):
        """Factory method for creating ImageVersion instances.

        Arguments:

        ivid     -- ID of the image version.
        imageid  -- ID of the image the image version belongs to.
        ivtype   -- An instance of the ImageVersionType alternative.
        ivhash   -- Hash of the image version file.
        location -- Location of the image version file.
        mtime    -- mtime of the image version file.
        width    -- Width of the image version.
        height   -- Height of the image version.
        comment  -- Comment of the image version.
        """
        imageversion = ImageVersion(
            self, ivid, imageid, ivtype, ivhash, location, mtime, width,
            height, comment)
        self.imageversioncache[ivid] = imageversion
        return imageversion


    def _deleteObjectFromParents(self, objid):
        """Helper method that deletes an object from its parents."""
        cursor = self.connection.cursor()
        cursor.execute(
            " select distinct album.id, album.tag"
            " from   member, album"
            " where  member.object = %s and member.album = album.id",
            objid)
        parentinfolist = cursor.fetchall()
        for parentid, _ in parentinfolist:
            cursor.execute(
                " select position"
                " from   member"
                " where  album = %s and object = %s"
                " order by position desc",
                parentid,
                objid)
            positions = [x[0] for x in cursor.fetchall()]
            for position in positions:
                cursor.execute(
                    " delete from member"
                    " where  album = %s and position = %s",
                    parentid,
                    position)
                cursor.execute(
                    " update member"
                    " set    position = position - 1"
                    " where  album = %s and position > %s",
                    parentid,
                    position)
            if parentid in self.objectcache:
                del self.objectcache[parentid]


    def _setModified(self):
        """Set the modified flag."""
        self.modified = True
        for fn in self.modificationCallbacks:
            fn(True)


    def _unsetModified(self):
        """Unset the modified flag."""
        self.modified = False
        for fn in self.modificationCallbacks:
            fn(False)


    def _getConnection(self):
        """Get the database connection instance."""
        assert self.inTransaction
        return self.connection


    def _getOrphanAlbumsCache(self):
        """Get the cache of the orphaned albums."""
        assert self.inTransaction
        return self.orphanAlbumsCache


    def _setOrphanAlbumsCache(self, albums):
        """Set the cache of the orphaned albums."""
        assert self.inTransaction
        self.orphanAlbumsCache = albums


    def _getOrphanImagesCache(self):
        """Get the cache of the orphaned images."""
        assert self.inTransaction
        return self.orphanImagesCache


    def _setOrphanImagesCache(self, images):
        """Set the cache of the orphaned images."""
        assert self.inTransaction
        self.orphanImagesCache = images


class Category:
    """A Kofoto category."""

    ##############################
    # Public methods.

    def getId(self):
        """Get category ID."""
        return self.catid


    def getTag(self):
        """Get category tag."""
        return self.tag


    def setTag(self, newtag):
        """Set category tag."""
        verifyValidCategoryTag(newtag)
        cursor = self.shelf._getConnection().cursor()
        cursor.execute(
            " update category"
            " set    tag = %s"
            " where  id = %s",
            newtag,
            self.getId())
        self.tag = newtag
        self.shelf._setModified()


    def getDescription(self):
        """Get category description."""
        return self.description


    def setDescription(self, newdesc):
        """Set category description."""
        cursor = self.shelf._getConnection().cursor()
        cursor.execute(
            " update category"
            " set    description = %s"
            " where  id = %s",
            newdesc,
            self.getId())
        self.description = newdesc
        self.shelf._setModified()


    def getChildren(self, recursive=False):
        """Get child categories.

        If recursive is true, get all descendants. If recursive is
        false, get only immediate children. Returns an iterable
        returning of Category instances (unordered)."""
        catdag = self.shelf.categorydag.get()
        if recursive:
            catiter = catdag.getDescendants(self.getId())
        else:
            catiter = catdag.getChildren(self.getId())
        for catid in catiter:
            yield self.shelf.getCategory(catid)


    def getParents(self, recursive=False):
        """Get parent categories.

        If recursive is true, get all ancestors. If recursive is
        false, get only immediate parents. Returns an iterable
        returning of Category instances (unordered)."""
        catdag = self.shelf.categorydag.get()
        if recursive:
            catiter = catdag.getAncestors(self.getId())
        else:
            catiter = catdag.getParents(self.getId())
        for catid in catiter:
            yield self.shelf.getCategory(catid)


    def isChildOf(self, category, recursive=False):
        """Check whether this category is a child or descendant of a
        category.

        If recursive is true, check if the category is a descendant of
        this category, otherwise just consider immediate children."""
        parentid = category.getId()
        childid = self.getId()
        catdag = self.shelf.categorydag.get()
        if recursive:
            return catdag.reachable(parentid, childid)
        else:
            return catdag.connected(parentid, childid)


    def isParentOf(self, category, recursive=False):
        """Check whether this category is a parent or ancestor of a
        category.

        If recursive is true, check if the category is an ancestor of
        this category, otherwise just consider immediate parents."""
        return category.isChildOf(self, recursive)


    def connectChild(self, category):
        """Make parent-child link between this category and a category."""
        parentid = self.getId()
        childid = category.getId()
        if self.shelf.categorydag.get().connected(parentid, childid):
            raise CategoriesAlreadyConnectedError(
                self.getTag(), category.getTag())
        try:
            self.shelf.categorydag.get().connect(parentid, childid)
        except LoopError:
            raise CategoryLoopError(self.getTag(), category.getTag())
        cursor = self.shelf._getConnection().cursor()
        cursor.execute(
            " insert into category_child (parent, child)"
            " values (%s, %s)",
            parentid,
            childid)
        self.shelf._setModified()


    def disconnectChild(self, category):
        """Remove a parent-child link between this category and a category."""
        parentid = self.getId()
        childid = category.getId()
        self.shelf.categorydag.get().disconnect(parentid, childid)
        cursor = self.shelf._getConnection().cursor()
        cursor.execute(
            " delete from category_child"
            " where  parent = %s and child = %s",
            parentid,
            childid)
        self.shelf._setModified()


    ##############################
    # Internal methods.

    def __init__(self, shelf, catid, tag, description):
        self.shelf = shelf
        self.catid = catid
        self.tag = tag
        self.description = description


    def __eq__(self, obj):
        return isinstance(obj, Category) and obj.getId() == self.getId()


    def __ne__(self, obj):
        return not obj == self


    def __hash__(self):
        return self.getId()


class _Object:
    """Abstract base class of Kofoto objects (albums and images)."""

    ##############################
    # Public methods.

    def isAlbum(self):
        """Return True if this an album, False if this is an image."""
        raise UnimplementedError

    def getId(self):
        """Get the ID of an object."""
        return self.objid


    def getParents(self):
        """Get the parent albums of an object.

        Returns an iterable returning the albums.

        Note that the object may be included multiple times in a
        parent album."""
        cursor = self.shelf._getConnection().cursor()
        cursor.execute(
            " select distinct album.id"
            " from   member, album"
            " where  member.object = %s and"
            "        member.album = album.id",
            self.getId())
        for (albumid,) in cursor:
            yield self.shelf.getAlbum(albumid)


    def getAttribute(self, name):
        """Get the value of an attribute.

        Returns the value as string, or None if there was no matching
        attribute.
        """
        if name in self.attributes:
            return self.attributes[name]
        cursor = self.shelf._getConnection().cursor()
        cursor.execute(
            " select value"
            " from   attribute"
            " where  object = %s and name = %s",
            self.getId(),
            name)
        if cursor.rowcount > 0:
            value = cursor.fetchone()[0]
            self.attributes[name] = value
        else:
            value = None
        return value


    def getAttributeMap(self):
        """Get a map of all attributes."""
        if self.allAttributesFetched:
            return self.attributes
        cursor = self.shelf._getConnection().cursor()
        cursor.execute(
            " select name, value"
            " from   attribute"
            " where  object = %s",
            self.getId())
        amap = {}
        for key, value in cursor:
            amap[key] = value
        self.attributes = amap
        self.allAttributesFetched = True
        return amap


    def getAttributeNames(self):
        """Get all attribute names.

        Returns an iterable returning the attributes."""
        if not self.allAttributesFetched:
            self.getAttributeMap()
        return self.attributes.iterkeys()


    def setAttribute(self, name, value, overwrite=True):
        """Set an attribute value.

        Iff overwrite is true, an existing attribute will be
        overwritten.
        """
        if overwrite:
            method = "replace"
        else:
            method = "ignore"
        cursor = self.shelf._getConnection().cursor()
        cursor.execute(
            " insert or " + method + " into attribute"
            "     (object, name, value, lcvalue)"
            " values"
            "     (%s, %s, %s, %s)",
            self.getId(),
            name,
            value,
            value.lower())
        if cursor.rowcount > 0:
            self.attributes[name] = value
            self.shelf._setModified()


    def deleteAttribute(self, name):
        """Delete an attribute."""
        cursor = self.shelf._getConnection().cursor()
        cursor.execute(
            " delete from attribute"
            " where  object = %s and name = %s",
            self.getId(),
            name)
        if name in self.attributes:
            del self.attributes[name]
        self.shelf._setModified()


    def addCategory(self, category):
        """Add a category."""
        objid = self.getId()
        catid = category.getId()
        try:
            cursor = self.shelf._getConnection().cursor()
            cursor.execute(
                " insert into object_category (object, category)"
                " values (%s, %s)",
                objid,
                catid)
            self.categories.add(catid)
            self.shelf._setModified()
        except sql.IntegrityError:
            raise CategoryPresentError(objid, category.getTag())


    def removeCategory(self, category):
        """Remove a category."""
        cursor = self.shelf._getConnection().cursor()
        catid = category.getId()
        cursor.execute(
            " delete from object_category"
            " where object = %s and category = %s",
            self.getId(),
            catid)
        self.categories.discard(catid)
        self.shelf._setModified()


    def getCategories(self, recursive=False):
        """Get categories for this object.

        Returns an iterable returning the categories."""
        if not self.allCategoriesFetched:
            cursor = self.shelf._getConnection().cursor()
            cursor.execute(
                " select category from object_category"
                " where  object = %s",
                self.getId())
            self.categories = set([x[0] for x in cursor])
            self.allCategoriesFetched = True
        if recursive:
            allcategories = set()
            for catid in self.categories:
                allcategories |= set(
                    self.shelf.categorydag.get().getAncestors(catid))
        else:
            allcategories = self.categories
        for catid in allcategories:
            yield self.shelf.getCategory(catid)


    ##############################
    # Internal methods.

    def __init__(self, shelf, objid):
        self.shelf = shelf
        self.objid = objid
        self.attributes = {}
        self.allAttributesFetched = False
        self.categories = set()
        self.allCategoriesFetched = False

    def _categoriesDirty(self):
        """Set the categories dirty flag."""
        self.allCategoriesFetched = False


    def __eq__(self, obj):
        return isinstance(obj, _Object) and obj.getId() == self.getId()


    def __ne__(self, obj):
        return not obj == self


    def __hash__(self):
        return self.getId()


class Album(_Object):
    """Abstract base class of Kofoto albums."""

    ##############################
    # Public methods.

    def getType(self):
        """Get the album type.

        The returned value is an instance of the AlbumType alternative.
        """
        return self.albumtype


    def isMutable(self):
        """Whether the album can be modified with setChildren."""
        raise UnimplementedError


    def getTag(self):
        """Get the tag of the album."""
        return self.tag


    def setTag(self, newtag):
        """Set the tag of the album."""
        verifyValidAlbumTag(newtag)
        cursor = self.shelf._getConnection().cursor()
        cursor.execute(
            " update album"
            " set    tag = %s"
            " where  id = %s",
            newtag,
            self.getId())
        self.tag = newtag
        self.shelf._setModified()


    def getChildren(self):
        """Get the album's children.

        Returns an iterable returning Album/Image instances.
        """
        raise UnimplementedError


    def getAlbumChildren(self):
        """Get the album's album children.

        Returns an iterable returning Album instances.
        """
        raise UnimplementedError


    def getAlbumParents(self):
        """Get the album's (album) parents.

        Returns an iterable returning Album instances.
        """
        cursor = self.shelf._getConnection().cursor()
        cursor.execute(
            " select distinct member.album"
            " from   member, album"
            " where  member.object = %s and"
            "        member.album = album.id",
            self.getId())
        for (objid,) in cursor:
            yield self.shelf.getAlbum(objid)


    def setChildren(self, children):
        """Set the children of the album.

        Arguments:

        children -- A list of Album/Image instances.
        """
        raise UnimplementedError


    def isAlbum(self):
        """Return True if this an album, False if this is an image."""
        return True


    ##############################
    # Internal methods.

    def __init__(self, shelf, albumid, tag, albumtype):
        """Constructor of an Album."""
        _Object.__init__(self, shelf, albumid)
        self.shelf = shelf
        self.tag = tag
        self.albumtype = albumtype


class PlainAlbum(Album):
    """A plain Kofoto album."""

    ##############################
    # Public methods.

    def isMutable(self):
        """Whether the album can be modified with setChildren."""
        return True


    def getChildren(self):
        """Get the album's children.

        Returns an iterable returning Album/Images instances.
        """
        if self.children is not None:
            for child in self.children:
                yield child
            return
        cursor = self.shelf._getConnection().cursor()
        cursor.execute(
            " select object"
            " from   member"
            " where  album = %s"
            " order by position",
            self.getId())
        self.children = []
        for (objid,) in cursor:
            child = self.shelf.getObject(objid)
            self.children.append(child)
        for child in self.children:
            yield child


    def getAlbumChildren(self):
        """Get the album's album children.

        Returns an iterable returning Album instances.
        """
        if self.children is not None:
            for child in self.children:
                if child.isAlbum():
                    yield child
            return
        cursor = self.shelf._getConnection().cursor()
        cursor.execute(
            " select member.object"
            " from   member, album"
            " where  member.album = %s and"
            "        member.object = album.id"
            " order by position",
            self.getId())
        for (objid,) in cursor:
            yield self.shelf.getAlbum(objid)


    def setChildren(self, children):
        """Set the album's children.

        Arguments:

        children -- A list of Album/Image instances.
        """
        albumid = self.getId()
        cursor = self.shelf._getConnection().cursor()
        cursor.execute(
            "-- types int")
        cursor.execute(
            " select count(position)"
            " from   member"
            " where  album = %s",
            albumid)
        oldchcnt = cursor.fetchone()[0]
        newchcnt = len(children)
        for ix in range(newchcnt):
            childid = children[ix].getId()
            if ix < oldchcnt:
                cursor.execute(
                    " update member"
                    " set    object = %s"
                    " where  album = %s and position = %s",
                    childid,
                    albumid,
                    ix)
            else:
                cursor.execute(
                    " insert into member (album, position, object)"
                    " values (%s, %s, %s)",
                    albumid,
                    ix,
                    childid)
        cursor.execute(
            " delete from member"
            " where  album = %s and position >= %s",
            albumid,
            newchcnt)
        self.shelf._setModified()
        self.shelf._setOrphanAlbumsCache(None)
        self.shelf._setOrphanImagesCache(None)
        self.children = children[:]

    ##############################
    # Internal methods.

    def __init__(self, *args):
        """Constructor of an Album."""
        Album.__init__(self, *args)
        self.children = None


class Image(_Object):
    """A Kofoto image."""

    ##############################
    # Public methods.

    def isAlbum(self):
        """Return True if this an album, False if this is an image."""
        return False


    def getImageVersions(self):
        """Get the image versions for the image.

        Returns an iterable returning ImageVersion instances.
        """
        cursor = self.shelf._getConnection().cursor()
        cursor.execute(
            " select id"
            " from   image_version"
            " where  image = %s"
            " order by id",
            self.getId())
        for (ivid,) in cursor:
            yield self.shelf.getImageVersion(ivid)


    def getPrimaryVersion(self):
        """Get the image's primary version.

        Returns an ImageVersion instance, or None if the image has no
        versions.
        """
        if self.primary_version_id is None:
            return None
        else:
            return self.shelf.getImageVersion(self.primary_version_id)


    ##############################
    # Internal methods.

    def __init__(self, shelf, imageid, primary_version_id):
        _Object.__init__(self, shelf, imageid)
        self.shelf = shelf
        self.primary_version_id = primary_version_id


    def _makeNewPrimaryVersion(self):
        """Helper method to make a new primary image version of needed."""
        ivs = list(self.getImageVersions())
        if len(ivs) > 0:
            # The last version is probably the best.
            self.primary_version_id = ivs[-1].getId()
        else:
            self.primary_version_id = None
        cursor = self.shelf._getConnection().cursor()
        cursor.execute(
            " update image"
            " set    primary_version = %s"
            " where  id = %s",
            self.primary_version_id,
            self.getId())


    def _setPrimaryVersion(self, imageversion):
        """Helper method to set the primary image version."""
        self.primary_version_id = imageversion.getId()


class ImageVersion:
    """A Kofoto image version."""

    ##############################
    # Public methods.

    def getId(self):
        """Get the ID of the image version."""
        return self.id


    def getImage(self):
        """Get the image associated with the image version."""
        return self.shelf.getImage(self.imageid)


    def getType(self):
        """Get the type of the image version.

        Returns ImageVersionType.Important, ImageVersionType.Original
        or ImageVersionType.Other."""
        return self.type


    def getComment(self):
        """Get the comment of the image version."""
        return self.comment


    def getHash(self):
        """Get the hash of the image version."""
        return self.hash


    def getLocation(self):
        """Get the last known location of the image version."""
        return self.location


    def getModificationTime(self):
        """Get the last known modification time of the image version."""
        return self.mtime


    def getSize(self):
        """Get the size of the image version."""
        return self.size


    def setImage(self, image):
        """Associate the image version with an image."""
        oldimage = self.getImage()
        if image == oldimage:
            return
        if oldimage.getPrimaryVersion() == self:
            oldImageNeedsNewPrimaryVersion = True
        else:
            oldImageNeedsNewPrimaryVersion = False
        self.imageid = image.getId()
        cursor = self.shelf._getConnection().cursor()
        cursor.execute(
            " update image_version"
            " set    image = %s"
            " where  id = %s",
            self.imageid,
            self.id)
        if image.getPrimaryVersion() == None:
            image._makeNewPrimaryVersion()
        if oldImageNeedsNewPrimaryVersion:
            oldimage._makeNewPrimaryVersion()
        self.shelf._setModified()


    def setType(self, ivtype):
        """Set the type of the image version.

        Arguments:

        ivtype -- An instance of the ImageVersionType alternative.
        """
        self.type = ivtype
        cursor = self.shelf._getConnection().cursor()
        cursor.execute(
            " update image_version"
            " set    type = %s"
            " where  id = %s",
            _imageVersionTypeToIdentifier(ivtype),
            self.id)
        self.shelf._setModified()


    def setComment(self, comment):
        """Set the comment of the image version."""
        self.comment = comment
        cursor = self.shelf._getConnection().cursor()
        cursor.execute(
            " update image_version"
            " set    comment = %s"
            " where  id = %s",
            comment,
            self.id)
        self.shelf._setModified()


    def makePrimary(self):
        """Make this image version the primary image version."""
        cursor = self.shelf._getConnection().cursor()
        cursor.execute(
            " update image"
            " set    primary_version = %s"
            " where  id = %s",
            self.id,
            self.imageid)
        self.getImage()._setPrimaryVersion(self)
        self.shelf._setModified()


    def isPrimary(self):
        """Whether the image version is primary."""
        return self.getImage().getPrimaryVersion() == self


    def contentChanged(self):
        """Record new image information for an edited image version.

        Checksum, width, height and mtime are updated.

        It is assumed that the image version location is still correct.
        """
        self.hash = computeImageHash(self.location)
        import Image as PILImage
        try:
            pilimg = PILImage.open(self.location)
        except IOError:
            raise NotAnImageFileError(self.location)
        self.size = pilimg.size
        self.mtime = os.path.getmtime(self.location)
        cursor = self.shelf._getConnection().cursor()
        cursor.execute(
            " update image_version"
            " set    hash = %s, width = %s, height = %s, mtime = %s"
            " where  id = %s",
            self.hash,
            self.size[0],
            self.size[1],
            self.mtime,
            self.getId())
        self.shelf._setModified()


    def locationChanged(self, location):
        """Set the last known location of the image version.

        The mtime is also updated."""
        cursor = self.shelf._getConnection().cursor()
        location = unicode(os.path.realpath(location))
        try:
            self.mtime = os.path.getmtime(location)
        except OSError:
            self.mtime = 0
        cursor.execute(
            " update image_version"
            " set    directory = %s, filename = %s, mtime = %s"
            " where  id = %s",
            os.path.dirname(location),
            os.path.basename(location),
            self.mtime,
            self.getId())
        self.location = location
        self.shelf._setModified()


    def importExifTags(self, overwrite):
        """Read known EXIF tags and add them as attributes.

        Iff overwrite is true, existing attributes will be
        overwritten.

        Raises kofoto.shelfexceptions.ExifImportError on error.
        """
        from kofoto import EXIF
        image = self.getImage()
        fp = open(self.getLocation(), "rb")
        try:
            tags = EXIF.process_file(fp, details=False)
        except: # Work-around for buggy EXIF library.
            raise ExifImportError(self.getLocation())

        for tag in ["Image DateTime",
                    "EXIF DateTimeOriginal",
                    "EXIF DateTimeDigitized"]:
            value = tags.get(tag)
            if value and str(value) != "0000:00:00 00:00:00":
                m = re.match(
                    r"(\d{4})[:/-](\d{2})[:/-](\d{2}) (\d{2}):(\d{2}):(\d{2})",
                    str(value))
                if m:
                    image.setAttribute(
                        u"captured",
                        u"%s-%s-%s %s:%s:%s" % m.groups())

        value = tags.get("EXIF ExposureTime")
        if value:
            image.setAttribute(u"exposuretime", unicode(value), overwrite)
        value = tags.get("EXIF FNumber")
        if value:
            image.setAttribute(u"fnumber", unicode(value), overwrite)
        value = tags.get("EXIF Flash")
        if value:
            image.setAttribute(u"flash", unicode(value), overwrite)
        value = tags.get("EXIF FocalLength")
        if value:
            image.setAttribute(u"focallength", unicode(value), overwrite)
        value = tags.get("Image Make")
        if value:
            image.setAttribute(u"cameramake", unicode(value), overwrite)
        value = tags.get("Image Model")
        if value:
            image.setAttribute(u"cameramodel", unicode(value), overwrite)
        value = tags.get("Image Orientation")
        if value:
            try:
                m = {1: "up",
                     2: "up",
                     3: "down",
                     4: "up",
                     5: "up",
                     6: "left",
                     7: "up",
                     8: "right",
                     }
                image.setAttribute(
                    u"orientation", unicode(m[value.values[0]]), overwrite)
            except KeyError:
                pass
        value = tags.get("EXIF ExposureProgram")
        if value:
            image.setAttribute(u"exposureprogram", unicode(value), overwrite)
        value = tags.get("EXIF ISOSpeedRatings")
        if value:
            image.setAttribute(u"iso", unicode(value), overwrite)
        value = tags.get("EXIF ExposureBiasValue")
        if value:
            image.setAttribute(u"exposurebias", unicode(value), overwrite)
        self.shelf._setModified()

    ##############################
    # Internal methods.

    def __init__(
        self, shelf, ivid, imageid, ivtype, ivhash, location, mtime, width,
        height, comment):
        """Constructor of an ImageVersion."""
        self.shelf = shelf
        self.id = ivid
        self.imageid = imageid
        self.type = ivtype
        self.hash = ivhash
        self.location = location
        self.mtime = mtime
        self.size = width, height
        self.comment = comment


class MagicAlbum(Album):
    """Base class of magic albums."""

    ##############################
    # Public methods.

    def isMutable(self):
        """Whether the album can be modified with setChildren."""
        return False


    def setChildren(self, children):
        """Set the album's children.

        Arguments:

        children -- A list of Album/Image instances.
        """
        raise UnsettableChildrenError(self.getTag())


class OrphansAlbum(MagicAlbum):
    """An album with all albums and images that are orphans."""

    ##############################
    # Public methods.

    def getChildren(self):
        """Get the album's children.

        Returns an iterable returning the orphans.
        """
        return self._getChildren(True)


    def getAlbumChildren(self):
        """Get the album's album children.

        Returns an iterable returning the orphans.
        """
        return self._getChildren(False)


    ##############################
    # Internal methods.

    def _getChildren(self, includeimages):
        """Helper method to get the albums children.

        Arguments:

        includeimages -- Whether images should be included.
        """
        albums = self.shelf._getOrphanAlbumsCache()
        if albums != None:
            for album in albums:
                yield album
        else:
            cursor = self.shelf._getConnection().cursor()
            cursor.execute(
                " select   id"
                " from     album"
                " where    id not in (select object from member) and"
                "          id != %s"
                " order by tag",
                _ROOT_ALBUM_ID)
            albums = []
            for (albumid,) in cursor:
                album = self.shelf.getAlbum(albumid)
                albums.append(album)
                yield album
            self.shelf._setOrphanAlbumsCache(albums)
        if includeimages:
            images = self.shelf._getOrphanImagesCache()
            if images != None:
                for image in images:
                    yield image
            else:
                cursor = self.shelf._getConnection().cursor()
                cursor.execute(
                    " select   i.id, i.primary_version"
                    " from     image as i left join attribute as a"
                    " on       i.id = a.object and a.name = 'captured'"
                    " where    i.id not in (select object from member)"
                    " order by a.lcvalue")
                images = []
                for (imageid, primary_version_id) in cursor:
                    image = self.shelf._imageFactory(
                        imageid, primary_version_id)
                    images.append(image)
                    yield image
                self.shelf._setOrphanImagesCache(images)


class SearchAlbum(MagicAlbum):
    """An album whose content is defined by a search string."""

    ##############################
    # Public methods.

    def getChildren(self):
        """Get the album's children.

        Returns an iterable returning the children.
        """
        return self._getChildren(True)


    def getAlbumChildren(self):
        """Get the album's album children.

        Returns an iterable returning the children.
        """
        return self._getChildren(False)


    ##############################
    # Internal methods.

    def _getChildren(self, includeimages):
        """Helper method to get the albums children.

        Arguments:

        includeimages -- Whether images should be included.
        """
        query = self.getAttribute(u"query")
        if not query:
            return []
        from kofoto import search
        parser = search.Parser(self.shelf)
        try:
            tree = parser.parse(query)
        except (AlbumDoesNotExistError,
                CategoryDoesNotExistError,
                search.ParseError):
            return []
        objects = self.shelf.search(tree)
        if includeimages:
            objectlist = list(objects)
        else:
            objectlist = [x for x in objects if x.isAlbum()]

        def sortfn(x, y):
            """Helper function."""
            a = cmp(x.getAttribute(u"captured"), y.getAttribute(u"captured"))
            if a == 0:
                return cmp(x.getId(), y.getId())
            else:
                return a
        objectlist.sort(sortfn)

        return objectlist


######################################################################
### Internal helper functions and classes.

def _albumTypeIdentifierToType(atid):
    """Map an album type identifer string to an AlbumType alternative."""
    try:
        return {
            u"orphans": AlbumType.Orphans,
            u"plain": AlbumType.Plain,
            u"search": AlbumType.Search,
            }[atid]
    except KeyError:
        raise UnknownAlbumTypeError(atid)


def _albumTypeToIdentifier(atype):
    """Map an AlbumType alternative to an album type identifer string."""
    try:
        return {
            AlbumType.Orphans: u"orphans",
            AlbumType.Plain: u"plain",
            AlbumType.Search: u"search",
            }[atype]
    except KeyError:
        raise UnknownAlbumTypeError(atype)


def _createCategoryDAG(connection):
    """Create the category DAG."""
    cursor = connection.cursor()
    cursor.execute(
        " select id"
        " from   category")
    dag = DAG([x[0] for x in cursor])
    cursor.execute(
        " select parent, child"
        " from   category_child")
    for parent, child in cursor:
        dag.connect(parent, child)
    return dag


def _imageVersionTypeIdentifierToType(ivtype):
    """Map an image version type identifer string to an ImageVersionType
    alternative.
    """
    try:
        return {
            u"important": ImageVersionType.Important,
            u"original": ImageVersionType.Original,
            u"other": ImageVersionType.Other,
            }[ivtype]
    except KeyError:
        raise UnknownImageVersionTypeError(ivtype)


def _imageVersionTypeToIdentifier(ivtype):
    """Map an ImageVersionType alternative to an image version type identifer
    string.
    """
    try:
        return {
            ImageVersionType.Important: u"important",
            ImageVersionType.Original: u"original",
            ImageVersionType.Other: u"other",
            }[ivtype]
    except KeyError:
        raise UnknownImageVersionTypeError(ivtype)


class _UnicodeConnectionDecorator:
    """A class that makes a database connection Unicode-aware."""

    def __init__(self, connection, encoding):
        """Constructor.

        Arguments:

        connection -- The database connection to wrap.
        encoding   -- The encoding (e.g. utf-8) to use.
        """
        self.connection = connection
        self.encoding = encoding

    def __getattr__(self, attrname):
        return getattr(self.connection, attrname)

    def cursor(self):
        """Return a _UnicodeConnectionDecorator."""
        return _UnicodeCursorDecorator(
            self.connection.cursor(), self.encoding)


class _UnicodeCursorDecorator:
    """A class that makes database cursor Unicode-aware."""

    def __init__(self, cursor, encoding):
        """Constructor.

        Arguments:

        cursor   -- The database cursor to wrap.
        encoding -- The encoding (e.g. utf-8) to use.
        """
        self.cursor = cursor
        self.encoding = encoding

    def __getattr__(self, attrname):
        if attrname in ["lastrowid", "rowcount"]:
            return getattr(self.cursor, attrname)
        else:
            raise AttributeError

    def __iter__(self):
        while True:
            rows = self.cursor.fetchmany(17)
            if not rows:
                break
            for row in rows:
                yield self._unicodifyRow(row)

    def _unicodifyRow(self, row):
        """Helper method that decodes fields of a row into Unicode."""
        result = []
        for col in row:
            if isinstance(col, str):
                result.append(unicode(col, self.encoding))
            else:
                result.append(col)
        return result

    def _assertUnicode(self, obj):
        """Check that all strings in an object are in Unicode.

        Lists, tuples and maps are recursively checked.
        """
        if isinstance(obj, str):
            raise AssertionError("non-Unicode string", obj)
        elif isinstance(obj, (list, tuple)):
            for elem in obj:
                self._assertUnicode(elem)
        elif isinstance(obj, dict):
            for val in obj.itervalues():
                self._assertUnicode(val)

    def execute(self, statement, *parameters):
        """Execute an SQL statement.

        The SQL string must be Unicode.
        """
        self._assertUnicode(parameters)
        return self.cursor.execute(statement, *parameters)

    def fetchone(self):
        """Fetch a row from the result set.

        The returned row contains Unicode strings.
        """
        row = self.cursor.fetchone()
        if row:
            return self._unicodifyRow(row)
        else:
            return None

    def fetchall(self):
        """Fetch all row of the result set.

        The returned rows contain Unicode strings.
        """
        return list(self)
