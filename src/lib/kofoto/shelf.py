"""Interface to a Kofoto shelf."""

######################################################################
### Public names.

__all__ = [
    "AlbumDoesNotExistError",
    "AlbumExistsError",
    "BadAlbumTagError",
    "BadCategoryTagError",
    "CategoriesAlreadyConnectedError",
    "CategoryDoesNotExistError",
    "CategoryExistsError",
    "CategoryLoopError",
    "CategoryPresentError",
    "FailedWritingError",
    "ImageDoesNotExistError",
    "ImageExistsError",
    "NotAnImageError",
    "ObjectDoesNotExistError",
    "ObjectExistsError",
    "SearchExpressionParseError",
    "Shelf",
    "ShelfLockedError",
    "ShelfNotFoundError",
    "UndeletableAlbumError",
    "UnimplementedError",
    "UnknownAlbumTypeError",
    "UnsettableChildrenError",
    "UnsupportedShelfError",
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
import time
import sqlite as sql
from sets import Set
from kofoto.common import KofotoError
from kofoto.dag import DAG, LoopError
from kofoto.cachedobject import CachedObject

import warnings
warnings.filterwarnings("ignore", "DB-API extension")

######################################################################
### Database schema.

schema = """
    -- EER diagram without attributes:
    --
    --                                          .----.
    --                                        ,'      |
    --                   ,^.                ,' N    ,^.
    --                 ,'   '.  N +----------+    ,'   '.
    --                <  has  >===| category |---< child >
    --                 '.   .'    +----------+ 0  '.   .'
    --                   'v'                        'v'
    --                    | 0
    --                    |           ,^.
    --              N +--------+ 0  ,'   '.  N +-----------+
    --      .---------| object |---<  has  >===| attribute |
    --      |         +--------+    '.   ,'    +-----------+
    --    ,/\.          |    |        'v'
    --  ,'    '.     __/      \__
    -- < member >   |            |
    --  '.    ,'   \|/          \|/
    --    '\/'      |            |
    --      | 1 +-------+    +-------+
    --      '---| album |    | image |
    --          +-------+    +-------+
    --
    --        |
    -- where \|/ is supposed to look like the subclass relation symbol.
    --        |

    -- Administrative information about the database.
    CREATE TABLE dbinfo (
        version   INTEGER NOT NULL
    );

    -- Superclass of objects in an album.
    CREATE TABLE object (
        -- Identifier of the object.
        objectid    INTEGER NOT NULL,

        PRIMARY KEY (objectid)
    );

    -- Albums in the shelf. Subclass of object.
    CREATE TABLE album (
        -- Identifier of the album. Shared primary key with object.
        albumid     INTEGER NOT NULL,
        -- Human-memorizable tag.
        tag         VARCHAR(256) NOT NULL,
        -- Whether it is possible to delete the album.
        deletable   INTEGER NOT NULL,
        -- Album type (plain, orphans, allalbums, ...).
        type        VARCHAR(256) NOT NULL,

        UNIQUE      (tag),
        FOREIGN KEY (albumid) REFERENCES object,
        PRIMARY KEY (albumid)
    );

    -- Images in the shelf. Subclass of object.
    CREATE TABLE image (
        -- Internal identifier of the image. Shared primary key with
        -- object.
        imageid     INTEGER NOT NULL,
        -- Identifier string which is derived from the image data and
        -- identifies the image uniquely. Currently an MD5 checksum
        -- (in hex format) of all image data.
        hash        CHAR(32) NOT NULL,
        -- Directory part of the last known location (local pathname)
        -- of the image.
        directory   VARCHAR(256) NOT NULL,
        -- Filename part of the last known location (local pathname)
        -- of the image.
        filename    VARCHAR(256) NOT NULL,

        UNIQUE      (hash),
        FOREIGN KEY (imageid) REFERENCES object,
        PRIMARY KEY (imageid)
    );

    CREATE INDEX image_location_index ON image (directory, filename);

    -- Members in an album.
    CREATE TABLE member (
        -- Identifier of the album.
        albumid     INTEGER NOT NULL,
        -- Member position, from 0 and up.
        position    UNSIGNED NOT NULL,
        -- Key of the member object.
        objectid    INTEGER NOT NULL,

        FOREIGN KEY (albumid) REFERENCES album,
        FOREIGN KEY (objectid) REFERENCES object,
        PRIMARY KEY (albumid, position)
    );

    CREATE INDEX member_objectid_index ON member (objectid);

    -- Attributes for objects.
    CREATE TABLE attribute (
        -- Key of the object.
        objectid    INTEGER NOT NULL,
        -- Name of the attribute.
        name        TEXT NOT NULL,
        -- Value of the attribute.
        value       TEXT NOT NULL,
        -- Lowercased value of the attribute.
        lcvalue     TEXT NOT NULL,

        FOREIGN KEY (objectid) REFERENCES object,
        PRIMARY KEY (objectid, name)
    );

    -- Categories in the shelf.
    CREATE TABLE category (
        -- Key of the category.
        categoryid  INTEGER NOT NULL,
        -- Human-memorizable tag.
        tag         TEXT NOT NULL,
        -- Short description of the category.
        description TEXT NOT NULL,

        UNIQUE      (tag),
        PRIMARY KEY (categoryid)
    );

    -- Parent-child relations between categories.
    CREATE TABLE category_child (
        -- Parent category.
        parent      INTEGER NOT NULL,

        -- Child category.
        child       INTEGER NOT NULL,

        FOREIGN KEY (parent) REFERENCES category,
        FOREIGN KEY (child) REFERENCES category,
        PRIMARY KEY (parent, child)
    );

    CREATE INDEX category_child_child ON category_child (child);

    -- Category-object mapping.
    CREATE TABLE object_category (
        -- Object.
        objectid    INTEGER NOT NULL,

        -- Category.
        categoryid  INTEGER NOT NULL,

        FOREIGN KEY (objectid) REFERENCES object,
        FOREIGN KEY (categoryid) REFERENCES category,
        PRIMARY KEY (objectid, categoryid)
    );

    CREATE INDEX object_category_categoryid ON object_category (categoryid);
"""

_ROOT_ALBUM_ID = 0
_ROOT_ALBUM_DEFAULT_TAG = u"root"
_SHELF_FORMAT_VERSION = 1

######################################################################
### Exceptions.

class FailedWritingError(KofotoError):
    """Kofoto shelf already exists."""
    pass


class ShelfNotFoundError(KofotoError):
    """Kofoto shelf not found."""
    pass


class UnsupportedShelfError(KofotoError):
    """Unsupported shelf database format."""


class ShelfLockedError(KofotoError):
    """The shelf is locked by another process."""
    pass


class ObjectExistsError(KofotoError):
    """Object already exists in the shelf."""
    pass


class AlbumExistsError(ObjectExistsError):
    """Album already exists in the shelf."""
    pass


class ImageExistsError(ObjectExistsError):
    """Album already exists in the shelf."""
    pass


class ObjectDoesNotExistError(KofotoError):
    """Object does not exist in the album."""
    pass


class AlbumDoesNotExistError(ObjectDoesNotExistError):
    """Album does not exist in the album."""
    pass


class ImageDoesNotExistError(ObjectDoesNotExistError):
    """Image does not exist in the album."""
    pass


class NotAnImageError(KofotoError):
    """Could not recognise file as an image."""
    pass


class UnknownAlbumTypeError(KofotoError):
    """The album type is unknown."""
    pass


class UndeletableAlbumError(KofotoError):
    """Album is not deletable."""
    pass


class BadAlbumTagError(KofotoError):
    """Bad album tag."""
    pass


class UnsettableChildrenError(KofotoError):
    """The album is magic and doesn't have any explicit children."""
    pass


class CategoryExistsError(KofotoError):
    """Category already exists."""
    pass


class CategoryDoesNotExistError(KofotoError):
    """Category does not exist."""
    pass


class BadCategoryTagError(KofotoError):
    """Bad category tag."""
    pass


class CategoryPresentError(KofotoError):
    """The object is already associated with this category."""
    pass


class CategoriesAlreadyConnectedError(KofotoError):
    """The categories are already connected."""
    pass


class CategoryLoopError(KofotoError):
    """Connecting the categories would create a loop in the category DAG."""
    pass


class SearchExpressionParseError(KofotoError):
    """Could not parse search expression."""
    pass


class UnimplementedError(KofotoError):
    """Unimplemented action."""
    pass


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
    if not isinstance(tag, (str, unicode)):
        raise BadAlbumTagError, tag
    try:
        int(tag)
    except ValueError:
        if not tag or tag[0] == "@" or re.search(r"\s", tag):
            raise BadAlbumTagError, tag
    else:
        raise BadAlbumTagError, tag


def verifyValidCategoryTag(tag):
    if not isinstance(tag, (str, unicode)):
        raise BadCategoryTagError, tag
    try:
        int(tag)
    except ValueError:
        if (not tag or tag[0] == "@" or re.search(r"\s", tag) or
            tag in ["and", "exactly", "not", "or"]):
            raise BadCategoryTagError, tag
    else:
        raise BadCategoryTagError, tag


def makeValidTag(tag):
    tag = tag.lstrip("@")
    tag = re.sub(r"\s", "", tag)
    if re.match("^\d+$", tag):
        tag += "_"
    if not tag:
        tag = "_"
    return tag


######################################################################
### Public classes.

_DEBUG = False

class Shelf:
    """A Kofoto shelf."""

    ##############################
    # Public methods.

    def __init__(self, location, codeset, create=False):
        """Constructor.

        Location is where the database is located. Codeset is the
        character encoding to use when encoding filenames stored in
        the database. (Thus, the codeset parameter does not specify
        how data is stored in the database.)"""
        self.location = location
        self.codeset = codeset
        self.transactionLock = threading.Lock()
        self.inTransaction = False
        self.objectcache = {}
        self.categorycache = {}
        self.modified = False
        self.modificationCallbacks = []

        if _DEBUG:
            logfile = file("sql.log", "a")
        else:
            logfile = None

        if os.path.exists(location):
            if create:
                raise FailedWritingError, location
        else:
            if not create:
                raise ShelfNotFoundError, location
        try:
            self.connection = _UnicodeConnectionDecorator(
                sql.connect(location,
                            client_encoding="UTF-8",
                            command_logfile=logfile),
                "UTF-8")
        except sql.DatabaseError:
            if create:
                raise FailedWritingError, location
            else:
                raise ShelfNotFoundError, location

        self.categorydag = CachedObject(_createCategoryDAG, (self.connection,))

        if create:
            self._createShelf(logfile)
        else:
            self._openShelf(logfile)


    def begin(self):
        """Begin working with the shelf."""
        assert not self.inTransaction
        self.transactionLock.acquire()
        self.inTransaction = True
        # In PySQLite, the transaction starts when the first SQL
        # command is executed, so execute a dummy command here.
        cursor = self.connection.cursor()
        cursor.execute("select * from dbinfo")


    def commit(self):
        """Commit the work on the shelf."""
        assert self.inTransaction
        try:
            self.connection.commit()
        finally:
            self.flushCategoryCache()
            self.flushObjectCache()
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


    def getStatistics(self):
        assert self.inTransaction
        cursor = self.connection.cursor()
        cursor.execute(
            " select count(*)"
            " from   album")
        nalbums = int(cursor.fetchone()[0])
        cursor.execute(
            " select count(*)"
            " from   image")
        nimages = int(cursor.fetchone()[0])
        return {"nalbums": nalbums, "nimages": nimages}


    def createAlbum(self, tag, albumtype=u"plain"):
        """Create an empty, orphaned album.

        Returns an Album instance."""
        assert self.inTransaction
        verifyValidAlbumTag(tag)
        cursor = self.connection.cursor()
        try:
            cursor.execute(
                " insert into object (objectid)"
                " values (null)")
            lastrowid = cursor.lastrowid
            cursor.execute(
                " insert into album (albumid, tag, deletable, type)"
                " values (%s, %s, 1, %s)",
                lastrowid,
                tag,
                albumtype)
            self._setModified()
            return self.getAlbum(lastrowid)
        except sql.IntegrityError:
            cursor.execute(
                " delete from object"
                " where objectid = %s",
                cursor.lastrowid)
            raise AlbumExistsError, tag


    def getAlbum(self, tag):
        """Get the album for a given album tag/ID.

        Returns an Album instance.
        """
        assert self.inTransaction
        if tag in self.objectcache:
            return self.objectcache[tag]
        cursor = self.connection.cursor()
        cursor.execute(
            " select albumid, tag, type"
            " from   album"
            " where  albumid = %s"
            " union"
            " select albumid, tag, type"
            " from   album"
            " where  tag = %s",
            tag,
            tag)
        row = cursor.fetchone()
        if not row:
            raise AlbumDoesNotExistError, tag
        albumid, tag, albumtype = row
        album = self._albumFactory(albumid, tag, albumtype)
        return album


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
            " select albumid, tag, type"
            " from   album")
        for albumid, tag, albumtype in cursor:
            if albumid in self.objectcache:
                yield self.objectcache[albumid]
            else:
                yield self._albumFactory(albumid, tag, albumtype)


    def getAllImages(self):
        """Get all images in the shelf (unsorted).

        Returns an iterable returning the images."""
        assert self.inTransaction
        cursor = self.connection.cursor()
        cursor.execute(
            " select imageid, hash, directory, filename"
            " from   image")
        for imageid, hash, directory, filename in cursor:
            location = os.path.join(directory, filename)
            if imageid in self.objectcache:
                yield self.objectcache[imageid]
            else:
                yield self._imageFactory(self, imageid, hash, location)


    def getImagesInDirectory(self, directory):
        """Get all images that are expected to be in a given directory
        (unsorted).

        Returns an iterable returning the images."""
        assert self.inTransaction
        directory = unicode(os.path.realpath(directory))
        cursor = self.connection.cursor()
        cursor.execute(
            " select imageid, hash, directory, filename"
            " from   image"
            " where  directory = %s",
            directory)
        for imageid, hash, directory, filename in cursor:
            location = os.path.join(directory, filename)
            if imageid in self.objectcache:
                yield self.objectcache[imageid]
            else:
                yield self._imageFactory(self, imageid, hash, location)


    def deleteAlbum(self, tag):
        """Delete the album for a given album tag/ID."""
        assert self.inTransaction
        cursor = self.connection.cursor()
        cursor.execute(
            " select albumid, tag"
            " from   album"
            " where  albumid = %s"
            " union"
            " select albumid, tag"
            " from   album"
            " where  tag = %s",
            tag,
            tag)
        row = cursor.fetchone()
        if not row:
            raise AlbumDoesNotExistError, tag
        albumid, tag = row
        if albumid == _ROOT_ALBUM_ID:
            # Don't delete the root album!
            raise UndeletableAlbumError, tag
        cursor.execute(
            " delete from album"
            " where  albumid = %s",
            albumid)
        self._deleteObjectFromParents(albumid)
        cursor.execute(
            " delete from member"
            " where  albumid = %s",
            albumid)
        cursor.execute(
            " delete from object"
            " where  objectid = %s",
            albumid)
        cursor.execute(
            " delete from attribute"
            " where  objectid = %s",
            albumid)
        cursor.execute(
            " delete from object_category"
            " where  objectid = %s",
            albumid)
        for x in albumid, tag:
            if x in self.objectcache:
                del self.objectcache[x]
        self._setModified()


    def createImage(self, path):
        """Add a new, orphaned image to the shelf.

        Returns an Image instance."""
        assert self.inTransaction
        import Image as PILImage
        try:
            pilimg = PILImage.open(path)
        except IOError:
            raise NotAnImageError, path

        location = unicode(os.path.realpath(path.encode(self.codeset)),
                           self.codeset)
        hash = computeImageHash(location.encode(self.codeset))
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                " insert into object (objectid)"
                " values (null)")
            imageid = cursor.lastrowid
            cursor.execute(
                " insert into image (imageid, hash, directory, filename)"
                " values (%s, %s, %s, %s)",
                imageid,
                hash,
                os.path.dirname(location),
                os.path.basename(location))
            width, height = pilimg.size
            cursor.execute(
                " insert into attribute (objectid, name, value, lcvalue)"
                " values (%s, 'width', %s, %s)",
                imageid,
                width,
                width)
            cursor.execute(
                " insert into attribute (objectid, name, value, lcvalue)"
                " values (%s, 'height', %s, %s)",
                imageid,
                height,
                height)
            now = unicode(time.strftime("%Y-%m-%d %H:%M:%S"))
            cursor.execute(
                " insert into attribute (objectid, name, value, lcvalue)"
                " values (%s, 'registered', %s, %s)",
                imageid,
                now,
                now)
            image = self._imageFactory(imageid, hash, location)
            image.importExifTags()
            self._setModified()
            return image
        except sql.IntegrityError:
            cursor.execute(
                " delete from object"
                " where objectid = %s",
                imageid)
            raise ImageExistsError, path


    def getImage(self, ref):
        """Get the image for a given image hash/ID/path.

        Returns an Image instance.
        """
        assert self.inTransaction
        if ref in self.objectcache:
            return self.objectcache[ref]
        cursor = self.connection.cursor()
        cursor.execute(
            " select imageid, hash, directory, filename"
            " from   image"
            " where  imageid = %s"
            " union"
            " select imageid, hash, directory, filename"
            " from   image"
            " where  hash = %s",
            ref,
            ref)
        row = cursor.fetchone()
        if not row:
            if os.path.isfile(ref.encode(self.codeset)):
                cursor.execute(
                    " select imageid, hash, directory, filename"
                    " from   image"
                    " where  hash = %s",
                    computeImageHash(ref.encode(self.codeset)))
                row = cursor.fetchone()
            if not row:
                raise ImageDoesNotExistError, ref
        imageid, hash, directory, filename = row
        location = os.path.join(directory, filename)
        return self._imageFactory(imageid, hash, location)


    def deleteImage(self, ref):
        """Delete the image for a given image hash/ID."""
        assert self.inTransaction
        cursor = self.connection.cursor()
        cursor.execute(
            " select imageid, hash"
            " from   image"
            " where  imageid = %s"
            " union"
            " select imageid, hash"
            " from   image"
            " where  hash = %s",
            ref,
            ref)
        row = cursor.fetchone()
        if row:
            imageid, hash = row
        else:
            # No match. Check whether it's a path to a known file.
            imageid = None
            if os.path.isfile(ref.encode(self.codeset)):
                cursor.execute(
                    " select imageid, hash"
                    " from   image"
                    " where  hash = %s",
                    computeImageHash(ref.encode(self.codeset)))
                row = cursor.fetchone()
                if row:
                    imageid, hash = row
        if not imageid:
            # Oh well.
            raise ImageDoesNotExistError, ref

        cursor = self.connection.cursor()
        cursor.execute(
            " delete from image"
            " where  imageid = %s",
            imageid)
        self._deleteObjectFromParents(imageid)
        cursor.execute(
            " delete from object"
            " where  objectid = %s",
            imageid)
        cursor.execute(
            " delete from attribute"
            " where  objectid = %s",
            imageid)
        cursor.execute(
            " delete from object_category"
            " where  objectid = %s",
            imageid)
        for x in imageid, hash:
            if x in self.objectcache:
                del self.objectcache[x]
        self._setModified()


    def getObject(self, objid):
        """Get the object for a given object tag/ID."""
        assert self.inTransaction
        if objid in self.objectcache:
            return self.objectcache[objid]
        try:
            return self.getAlbum(objid)
        except AlbumDoesNotExistError:
            try:
                return self.getImage(objid)
            except ImageDoesNotExistError:
                raise ObjectDoesNotExistError, objid


    def deleteObject(self, objid):
        """Get the object for a given object tag/ID."""
        assert self.inTransaction
        try:
            self.deleteImage(objid)
        except ImageDoesNotExistError:
            try:
                self.deleteAlbum(objid)
            except AlbumDoesNotExistError:
                raise ObjectDoesNotExistError, objid


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
            raise CategoryExistsError, tag


    def deleteCategory(self, tag):
        """Delete a category for a given category tag/ID."""
        assert self.inTransaction
        cursor = self.connection.cursor()
        cursor.execute(
            " select categoryid, tag"
            " from   category"
            " where  categoryid = %s"
            " union"
            " select categoryid, tag"
            " from   category"
            " where  tag = %s",
            tag,
            tag)
        row = cursor.fetchone()
        if not row:
            raise CategoryDoesNotExistError, tag
        catid, tag = row
        cursor.execute(
            " delete from category_child"
            " where  parent = %s",
            catid)
        cursor.execute(
            " delete from category_child"
            " where  child = %s",
            catid)
        cursor.execute(
            " delete from object_category"
            " where  categoryid = %s",
            catid)
        cursor.execute(
            " delete from category"
            " where  categoryid = %s",
            catid)
        catdag = self.categorydag.get()
        if catid in catdag:
            catdag.remove(catid)
        for x in catid, tag:
            if x in self.categorycache:
                del self.categorycache[x]
        self._setModified()


    def getCategory(self, catid):
        """Get a category for a given category tag/ID.

        Returns a Category instance."""
        assert self.inTransaction
        if catid in self.categorycache:
            return self.categorycache[catid]
        cursor = self.connection.cursor()
        cursor.execute(
            " select categoryid, tag, description"
            " from   category"
            " where  categoryid = %s"
            " union"
            " select categoryid, tag, description"
            " from   category"
            " where  tag = %s",
            catid,
            catid)
        row = cursor.fetchone()
        if not row:
            raise CategoryDoesNotExistError, catid
        catid, tag, desc = row
        category = Category(self, catid, tag, desc)
        self.categorycache[catid] = category
        self.categorycache[tag] = category
        return category


    def getRootCategories(self):
        """Get the categories that are roots, i.e. have no parents.

        Returns an iterable returning Category instances."""
        assert self.inTransaction
        for catid in self.categorydag.get().getRoots():
            yield self.getCategory(catid)


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

    def _createShelf(self, logfile):
        cursor = self.connection.cursor()
        cursor.execute(schema)
        cursor.execute(
            " insert into dbinfo (version)"
            " values (%s)",
            _SHELF_FORMAT_VERSION)
        cursor.execute(
            " insert into object (objectid)"
            " values (%s)",
            _ROOT_ALBUM_ID)
        cursor.execute(
            " insert into album (albumid, tag, deletable, type)"
            " values (%s, %s, 0, 'plain')",
            _ROOT_ALBUM_ID,
            _ROOT_ALBUM_DEFAULT_TAG)
        self.connection.commit()

        self.begin()
        orphansalbum = self.createAlbum(u"orphans", u"orphans")
        orphansalbum.setAttribute(u"title", u"Orphans")
        orphansalbum.setAttribute(
            u"description",
            u"This album contains albums and images that are not" +
            u" linked from any album.")
        self.getRootAlbum().setChildren([orphansalbum])
        self.commit()


    def _openShelf(self, logfile):
        cursor = self.connection.cursor()
        try:
            cursor.execute(
                " select version"
                " from   dbinfo")
        except sql.DatabaseError:
            raise UnsupportedShelfError, self.location
        version = cursor.fetchone()[0]
        self.connection.rollback()
        if version > _SHELF_FORMAT_VERSION:
            raise UnsupportedShelfError, location
        if version < _SHELF_FORMAT_VERSION:
            import kofoto.shelfupgrade
            kofoto.shelfupgrade.upgradeShelf(
                self.connection, version, _SHELF_FORMAT_VERSION)


    def _albumFactory(self, albumid, tag, albumtype):
        albumtypemap = {
            "allalbums": AllAlbumsAlbum,
            "allimages": AllImagesAlbum,
            "orphans": OrphansAlbum,
            "plain": PlainAlbum,
        }
        try:
            album = albumtypemap[albumtype](self, albumid, tag, albumtype)
        except KeyError:
            raise UnknownAlbumTypeError, albumtype
        self.objectcache[albumid] = album
        self.objectcache[tag] = album
        return album


    def _imageFactory(self, imageid, hash, location):
        image = Image(self, imageid, hash, location)
        self.objectcache[imageid] = image
        self.objectcache[unicode(imageid)] = image
        self.objectcache[hash] = image
        return image


    def _deleteObjectFromParents(self, objid):
        cursor = self.connection.cursor()
        cursor.execute(
            " select distinct albumid"
            " from member"
            " where objectid = %s",
            objid)
        parents = [x[0] for x in cursor.fetchall()]
        for parentid in parents:
            cursor.execute(
                " select   position"
                " from     member"
                " where    albumid = %s and objectid = %s"
                " order by position desc",
                parentid,
                objid)
            positions = [x[0] for x in cursor.fetchall()]
            for position in positions:
                cursor.execute(
                    " delete from member"
                    " where  albumid = %s and position = %s",
                    parentid,
                    position)
                cursor.execute(
                    " update member"
                    " set    position = position - 1"
                    " where  albumid = %s and position > %s",
                    parentid,
                    position)


    def _setModified(self):
        self.modified = True
        for fn in self.modificationCallbacks:
            fn(True)


    def _unsetModified(self):
        self.modified = False
        for fn in self.modificationCallbacks:
            fn(False)


    def _getConnection(self):
        assert self.inTransaction
        return self.connection


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
            " where  categoryid = %s",
            newtag,
            self.getId())
        del self.shelf.categorycache[self.tag]
        self.shelf.categorycache[newtag] = self
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
            " where  categoryid = %s",
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
            raise CategoriesAlreadyConnectedError, (self.getTag(),
                                                    category.getTag())
        try:
            self.shelf.categorydag.get().connect(parentid, childid)
        except LoopError:
            raise CategoryLoopError, (self.getTag(), category.getTag())
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


class _Object:
    def __init__(self, shelf, objid):
        self.shelf = shelf
        self.objid = objid
        self.attributes = {}
        self.allAttributesFetched = False
        self.categories = Set()
        self.allCategoriesFetched = False


    def getId(self):
        return self.objid


    def getParents(self):
        """Get the parent albums of an object.

        Returns an iterable returning the albums.
        
        Note that the object may be included multiple times in a
        parent album."""
        cursor = self.shelf._getConnection().cursor()
        cursor.execute(
            " select distinct album.albumid"
            " from   member, album"
            " where  member.objectid = %s and"
            "        member.albumid = album.albumid",
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
            " where  objectid = %s and name = %s",
            self.getId(),
            name)
        if cursor.rowcount > 0:
            value = cursor.fetchone()[0]
        else:
            value = None
        self.attributes[name] = value
        return value


    def getAttributeMap(self):
        """Get a map of all attributes."""
        if self.allAttributesFetched:
            return self.attributes
        cursor = self.shelf._getConnection().cursor()
        cursor.execute(
            " select name, value"
            " from   attribute"
            " where  objectid = %s",
            self.getId())
        map = {}
        for key, value in cursor:
            map[key] = value
        self.attributes = map
        self.allAttributesFetched = True
        return map


    def getAttributeNames(self):
        """Get all attribute names.

        Returns an iterable returning the attributes."""
        if not self.allAttributesFetched:
            self.getAttributeMap()
        return self.attributes.iterkeys()


    def setAttribute(self, name, value):
        """Set an attribute value."""
        cursor = self.shelf._getConnection().cursor()
        cursor.execute(
            " update attribute"
            " set    value = %s, lcvalue = %s"
            " where  objectid = %s and name = %s",
            value,
            value.lower(),
            self.getId(),
            name)
        if cursor.rowcount == 0:
            cursor.execute(
                " insert into attribute (objectid, name, value, lcvalue)"
                " values (%s, %s, %s, %s)",
                self.getId(),
                name,
                value,
                value.lower())
        self.attributes[name] = value
        self.shelf._setModified()


    def deleteAttribute(self, name):
        """Delete an attribute."""
        cursor = self.shelf._getConnection().cursor()
        cursor.execute(
            " delete from attribute"
            " where  objectid = %s and name = %s",
            self.getId(),
            name)
        self.attributes[name] = None
        self.shelf._setModified()


    def addCategory(self, category):
        """Add a category."""
        objid = self.getId()
        catid = category.getId()
        try:
            cursor = self.shelf._getConnection().cursor()
            cursor.execute(
                " insert into object_category (objectid, categoryid)"
                " values (%s, %s)",
                objid,
                catid)
            self.categories.add(catid)
            self.shelf._setModified()
        except sql.IntegrityError:
            raise CategoryPresentError, (objid, category.getTag())


    def removeCategory(self, category):
        """Remove a category."""
        cursor = self.shelf._getConnection().cursor()
        catid = category.getId()
        cursor.execute(
            " delete from object_category"
            " where objectid = %s and categoryid = %s",
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
                " select categoryid from object_category"
                " where  objectid = %s",
                self.getId())
            self.categories = Set([x[0] for x in cursor])
            self.allCategoriesFetched = True
        if recursive:
            allcategories = Set()
            for catid in self.categories:
                allcategories |= Set(
                    self.shelf.categorydag.get().getAncestors(catid))
        else:
            allcategories = self.categories
        for catid in allcategories:
            yield self.shelf.getCategory(catid)


class Album(_Object):
    """Base class of Kofoto albums."""

    ##############################
    # Public methods.

    def getType(self):
        return self.albumtype


    def getTag(self):
        """Get the tag of the album."""
        return self.tag


    def setTag(self, newtag):
        verifyValidAlbumTag(newtag)
        cursor = self.shelf._getConnection().cursor()
        cursor.execute(
            " update album"
            " set    tag = %s"
            " where  albumid = %s",
            newtag,
            self.getId())
        self.tag = newtag
        self.shelf._setModified()


    def getChildren(self):
        raise UnimplementedError


    def getAlbumChildren(self):
        raise UnimplementedError


    def getAlbumParents(self):
        """Get the album's (album) parents.

        Returns an iterable returning Album instances.
        """
        cursor = self.shelf._getConnection().cursor()
        cursor.execute(
            " select distinct member.albumid"
            " from   member, album"
            " where  member.objectid = %s and"
            "        member.albumid = album.albumid",
            self.getId())
        for (objid,) in cursor:
            yield self.shelf.getAlbum(objid)


    def setChildren(self, children):
        raise UnimplementedError


    def isAlbum(self):
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
            " select objectid"
            " from   member"
            " where  albumid = %s"
            " order by position",
            self.getId())
        self.children = []
        for (objid,) in cursor:
            child = self.shelf.getObject(objid)
            self.children.append(child)
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
            " select member.objectid"
            " from   member, album"
            " where  member.albumid = %s and"
            "        member.objectid = album.albumid"
            " order by position",
            self.getId())
        for (objid,) in cursor:
            yield self.shelf.getAlbum(objid)


    def setChildren(self, children):
        """Set an album's children."""
        albumid = self.getId()
        cursor = self.shelf._getConnection().cursor()
        cursor.execute(
            "-- types int")
        cursor.execute(
            " select count(position)"
            " from   member"
            " where  albumid = %s",
            albumid)
        oldchcnt = cursor.fetchone()[0]
        newchcnt = len(children)
        for ix in range(newchcnt):
            childid = children[ix].getId()
            if ix < oldchcnt:
                cursor.execute(
                    " update member"
                    " set    objectid = %s"
                    " where  albumid = %s and position = %s",
                    childid,
                    albumid,
                    ix)
            else:
                cursor.execute(
                    " insert into member (albumid, position, objectid)"
                    " values (%s, %s, %s)",
                    albumid,
                    ix,
                    childid)
        cursor.execute(
            " delete from member"
            " where  albumid = %s and position >= %s",
            albumid,
            newchcnt)
        self.shelf._setModified()
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

    def getLocation(self):
        """Get the last known location of the image."""
        return self.location


    def setLocation(self, location):
        """Set the last known location of the image."""
        cursor = self.shelf._getConnection().cursor()
        location = unicode(os.path.realpath(location))
        cursor.execute(
            " update image"
            " set    directory = %s, filename = %s"
            " where  imageid = %s",
            os.path.dirname(location),
            os.path.basename(location),
            self.getId())
        self.location = location
        self.shelf._setModified()


    def getHash(self):
        """Get the hash of the image."""
        return self.hash


    def setHash(self, hash):
        """Set the hash of the image."""
        cursor = self.shelf._getConnection().cursor()
        cursor.execute(
            " update image"
            " set    hash = %s"
            " where  imageid = %s",
            hash,
            self.getId())
        self.hash = hash
        import Image as PILImage
        try:
            pilimg = PILImage.open(self.location)
        except IOError:
            raise NotAnImageError, self.location
        self.setAttribute(u"width", unicode(pilimg.size[0]))
        self.setAttribute(u"height", unicode(pilimg.size[1]))
        self.shelf._setModified()


    def isAlbum(self):
        return False


    def importExifTags(self):
        """Read known EXIF tags and add them as attributes."""
        import EXIF
        tags = EXIF.process_file(
            file(self.getLocation().encode(self.shelf.codeset), "rb"))

        for tag in ["Image DateTime",
                    "EXIF DateTimeOriginal",
                    "EXIF DateTimeDigitized"]:
            value = tags.get(tag)
            if value and str(value) != "0000:00:00 00:00:00":
                a = str(value).split(":")
                if len(a) == 5:
                    value = u"-".join(a[0:2] + [":".join(a[2:5])])
                    self.setAttribute(u"captured", value)

        value = tags.get("EXIF ExposureTime")
        if value:
            self.setAttribute(u"exposuretime", unicode(value))
        value = tags.get("EXIF FNumber")
        if value:
            self.setAttribute(u"fnumber", unicode(value))
        value = tags.get("EXIF Flash")
        if value:
            self.setAttribute(u"flash", unicode(value))
        value = tags.get("EXIF FocalLength")
        if value:
            self.setAttribute(u"focallength", unicode(value))
        value = tags.get("Image Make")
        if value:
            self.setAttribute(u"cameramake", unicode(value))
        value = tags.get("Image Model")
        if value:
            self.setAttribute(u"cameramodel", unicode(value))
        value = tags.get("Image Orientation")
        if value:
            try:
                m = {"1": "up",
                     "2": "up",
                     "3": "down",
                     "4": "up",
                     "5": "up",
                     "6": "left",
                     "7": "up",
                     "8": "right",
                     }
                self.setAttribute(u"orientation", unicode(m[str(value)]))
            except KeyError:
                pass
        value = tags.get("EXIF ExposureProgram")
        if value:
            self.setAttribute(u"exposureprogram", unicode(value))
        value = tags.get("EXIF ISOSpeedRatings")
        if value:
            self.setAttribute(u"iso", unicode(value))
        value = tags.get("EXIF ExposureBiasValue")
        if value:
            self.setAttribute(u"exposurebias", unicode(value))
        value = tags.get("MakerNote SpecialMode")
        if value:
            self.setAttribute(u"specialmode", unicode(value))
        value = tags.get("MakerNote JPEGQual")
        if value:
            self.setAttribute(u"jpegquality", unicode(value))
        value = tags.get("MakerNote Macro")
        if value:
            self.setAttribute(u"macro", unicode(value))
        value = tags.get("MakerNote DigitalZoom")
        if value:
            self.setAttribute(u"digitalzoom", unicode(value))

    ##############################
    # Internal methods.

    def __init__(self, shelf, imageid, hash, location):
        """Constructor of an Image."""
        _Object.__init__(self, shelf, imageid)
        self.shelf = shelf
        self.hash = hash
        self.location = location


class MagicAlbum(Album):
    """Base class of magic albums."""

    ##############################
    # Public methods.

    def setChildren(self, children):
        raise UnsettableChildrenError, self.getTag()


class AllAlbumsAlbum(MagicAlbum):
    """An album with all albums, sorted by tag."""

    ##############################
    # Public methods.

    def getChildren(self):
        """Get the album's children.

        Returns an iterable returning the albums.
        """
        cursor = self.shelf._getConnection().cursor()
        cursor.execute(
            " select   albumid"
            " from     album"
            " order by tag")
        for (albumid,) in cursor:
            yield self.shelf.getAlbum(albumid)


    def getAlbumChildren(self):
        """Get the album's album children.

        Returns an iterable returning the albums.
        """
        return self.getChildren()


class AllImagesAlbum(MagicAlbum):
    """An album with all images, sorted by capture timestamp."""

    ##############################
    # Public methods.

    def getChildren(self):
        """Get the album's children.

        Returns an iterable returning the images.
        """
        cursor = self.shelf._getConnection().cursor()
        cursor.execute(
            " select   imageid, hash, directory, filename"
            " from     image left join attribute"
            " on       imageid = objectid and name = 'captured'"
            " order by lcvalue, directory, filename")
        for imageid, hash, directory, filename in cursor:
            location = os.path.join(directory, filename)
            yield self.shelf._imageFactory(imageid, hash, location)


    def getAlbumChildren(self):
        """Get the album's album children.

        Returns an iterable returning the images.
        """
        return []


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
        cursor = self.shelf._getConnection().cursor()
        cursor.execute(
            " select   albumid"
            " from     album"
            " where    albumid not in (select objectid from member) and"
            "          albumid != %s"
            " order by tag",
            _ROOT_ALBUM_ID)
        for (albumid,) in cursor:
            yield self.shelf.getAlbum(albumid)
        if includeimages:
            cursor.execute(
                " select   imageid, hash, directory, filename"
                " from     image left join attribute"
                " on       imageid = objectid and name = 'captured'"
                " where    imageid not in (select objectid from member)"
                " order by lcvalue, directory, filename")
            for imageid, hash, directory, filename in cursor:
                location = os.path.join(directory, filename)
                yield self.shelf._imageFactory(imageid, hash, location)


######################################################################
### Internal helper functions and classes.

def _createCategoryDAG(connection):
    cursor = connection.cursor()
    cursor.execute(
        " select categoryid"
        " from   category")
    dag = DAG([x[0] for x in cursor])
    cursor.execute(
        " select parent, child"
        " from   category_child")
    for parent, child in cursor:
        dag.connect(parent, child)
    return dag


class _UnicodeConnectionDecorator:
    def __init__(self, connection, encoding):
        self.connection = connection
        self.encoding = encoding

    def __getattr__(self, attrname):
        return getattr(self.connection, attrname)

    def cursor(self):
        return _UnicodeCursorDecorator(
            self.connection.cursor(), self.encoding)


class _UnicodeCursorDecorator:
    def __init__(self, cursor, encoding):
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
        result = []
        for col in row:
            if isinstance(col, str):
                result.append(unicode(col, self.encoding))
            else:
                result.append(col)
        return result

    def _assertUnicode(self, obj):
        if isinstance(obj, str):
            raise AssertionError, ("non-Unicode string", obj)
        elif isinstance(obj, (list, tuple)):
            for elem in obj:
                self._assertUnicode(elem)
        elif isinstance(obj, dict):
            for val in obj.itervalues():
                self._assertUnicode(val)

    def execute(self, sql, *parameters):
        self._assertUnicode(parameters)
        return self.cursor.execute(sql, *parameters)

    def fetchone(self):
        row = self.cursor.fetchone()
        if row:
            return self._unicodifyRow(row)
        else:
            return None

    def fetchall(self):
        return list(self)
