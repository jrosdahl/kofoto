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
    "MultipleImagesAtOneLocationError",
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
    "schema",
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
import kofoto.shelfupgrade

import warnings
warnings.filterwarnings("ignore", "DB-API extension")
warnings.filterwarnings(
    "ignore",
    ".*losing bits or changing sign will return a long.*",
    FutureWarning)

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
    --                        1 | | 1
    --                       ,-'   '-.
    --                     ,^.       ,^.
    --                   ,'   '.   ,'   '.
    --                  <  has  > <primary>
    --                   '.   .'   '.   .'
    --                     'v'       'v'
    --                     N \       / 1
    --                      +---------+
    --                      | version |
    --                      +---------+
    --
    --        |
    -- where \|/ is supposed to look like the subclass relation symbol.
    --        |

    -- Administrative information about the database.
    CREATE TABLE dbinfo (
        version     INTEGER NOT NULL
    );

    -- Superclass of objects in an album.
    CREATE TABLE object (
        -- Identifier of the object.
        id          INTEGER NOT NULL,

        PRIMARY KEY (id)
    );

    -- Albums in the shelf. Subclass of object.
    CREATE TABLE album (
        -- Identifier of the album. Shared primary key with object.
        id          INTEGER NOT NULL,
        -- Human-memorizable tag.
        tag         VARCHAR(256) NOT NULL,
        -- Whether it is possible to delete the album.
        deletable   INTEGER NOT NULL,
        -- Album type (plain, orphans, allalbums, ...).
        type        VARCHAR(256) NOT NULL,

        UNIQUE      (tag),
        FOREIGN KEY (id) REFERENCES object,
        PRIMARY KEY (id)
    );

    -- Images in the shelf. Subclass of object.
    CREATE TABLE image (
        -- Internal identifier of the image. Shared primary key with
        -- object.
        id          INTEGER NOT NULL,

        -- The primary version.
        primary_version INTEGER NOT NULL,

        FOREIGN KEY (id) REFERENCES object,
        FOREIGN KEY (primary_version) REFERENCES image_version,
        PRIMARY KEY (id)
    );

    -- Image versions.
    CREATE TABLE image_version (
        -- Identifier of the image version.
        id          INTEGER NOT NULL,

        -- Identifier of the image associated with this version.
        image       INTEGER NOT NULL,

        -- Type (original, important or other).
        type        VARCHAR(20) NOT NULL,

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
        -- Last known time of modification (UNIX epoch time).
        mtime       INTEGER NOT NULL,
        -- Image width.
        width       INTEGER NOT NULL,
        -- Image height.
        height      INTEGER NOT NULL,
        
        FOREIGN KEY (image) REFERENCES image,
        UNIQUE      (hash),
        PRIMARY KEY (id, version)
    );

    CREATE INDEX image_version_location_index ON image_version (directory, filename);

    -- Members in an album.
    CREATE TABLE member (
        -- Identifier of the album.
        album       INTEGER NOT NULL,
        -- Member position, from 0 and up.
        position    UNSIGNED NOT NULL,
        -- Key of the member object.
        object      INTEGER NOT NULL,

        FOREIGN KEY (album) REFERENCES album,
        FOREIGN KEY (object) REFERENCES object,
        PRIMARY KEY (album, position)
    );

    CREATE INDEX member_object_index ON member (object);

    -- Attributes for objects.
    CREATE TABLE attribute (
        -- Key of the object.
        object      INTEGER NOT NULL,
        -- Name of the attribute.
        name        TEXT NOT NULL,
        -- Value of the attribute.
        value       TEXT NOT NULL,
        -- Lowercased value of the attribute.
        lcvalue     TEXT NOT NULL,

        FOREIGN KEY (object) REFERENCES object,
        PRIMARY KEY (object, name)
    );

    -- Categories in the shelf.
    CREATE TABLE category (
        -- Key of the category.
        id          INTEGER NOT NULL,
        -- Human-memorizable tag.
        tag         TEXT NOT NULL,
        -- Short description of the category.
        description TEXT NOT NULL,

        UNIQUE      (tag),
        PRIMARY KEY (id)
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
        object      INTEGER NOT NULL,

        -- Category.
        category    INTEGER NOT NULL,

        FOREIGN KEY (object) REFERENCES object,
        FOREIGN KEY (category) REFERENCES category,
        PRIMARY KEY (object, category)
    );

    CREATE INDEX object_category_category ON object_category (category);
"""

_ROOT_ALBUM_ID = 0
_SHELF_FORMAT_VERSION = 3

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


class MultipleImagesAtOneLocationError(KofotoError):
    """Failed to identify image by location since the location isn't
    unique."""
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

    def __init__(self, location, codeset):
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
        self.orphanAlbumsCache = None
        self.orphanImagesCache = None
        self.allAlbumsCache = None
        self.allImagesCache = None
        self.modified = False
        self.modificationCallbacks = []
        if _DEBUG:
            self.logfile = file("sql.log", "a")
        else:
            self.logfile = None


    def create(self):
        """Create the shelf."""
        assert not self.inTransaction
        if os.path.exists(self.location):
            raise FailedWritingError, self.location
        try:
            self.connection = _UnicodeConnectionDecorator(
                sql.connect(self.location,
                            client_encoding="UTF-8",
                            command_logfile=self.logfile),
                "UTF-8")
        except sql.DatabaseError:
            raise FailedWritingError, self.location
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
        return kofoto.shelfupgrade.tryUpgrade(self.location, _SHELF_FORMAT_VERSION)


    def begin(self):
        """Begin working with the shelf."""
        assert not self.inTransaction
        self.transactionLock.acquire()
        self.inTransaction = True
        if not os.path.exists(self.location):
            raise ShelfNotFoundError, self.location
        try:
            self.connection = _UnicodeConnectionDecorator(
                sql.connect(self.location,
                            client_encoding="UTF-8",
                            command_logfile=self.logfile),
                "UTF-8")
        except sql.DatabaseError:
            raise ShelfNotFoundError, self.location
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
        self.orphanAlbumsCache = None
        self.orphanImagesCache = None
        self.allAlbumsCache = None
        self.allImagesCache = None


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
                " insert into object (id)"
                " values (null)")
            lastrowid = cursor.lastrowid
            cursor.execute(
                " insert into album (id, tag, deletable, type)"
                " values (%s, %s, 1, %s)",
                lastrowid,
                tag,
                albumtype)
            self._setModified()
            self.allAlbumsCache = None
            self.orphanAlbumsCache = None
            return self.getAlbum(lastrowid)
        except sql.IntegrityError:
            cursor.execute(
                " delete from object"
                " where id = %s",
                cursor.lastrowid)
            raise AlbumExistsError, tag


    def getAlbum(self, tag):
        """Get the album for a given album tag/ID.

        Returns an Album instance.
        """
        assert self.inTransaction
        if tag in self.objectcache:
            album = self.objectcache[tag]
            if not album.isAlbum():
                raise AlbumDoesNotExistError, tag
            return album
        try:
            albumid = int(tag)
        except ValueError:
            albumid = None
        cursor = self.connection.cursor()
        if albumid is None:
            # Tag.
            cursor.execute(
                " select id, tag, type"
                " from   album"
                " where  tag = %s",
                tag)
        else:
            # ID.
            cursor.execute(
                " select id, tag, type"
                " from   album"
                " where  id = %s",
                albumid)
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
            " select id, tag, type"
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
            " select id, hash, directory, filename, mtime, width, height"
            " from   image")
        for (imageid, imghash, directory, filename, mtime, width,
             height) in cursor:
            location = os.path.join(directory, filename)
            if imageid in self.objectcache:
                yield self.objectcache[imageid]
            else:
                yield self._imageFactory(
                    imageid, imghash, location, mtime, width, height)


    def getImagesInDirectory(self, directory):
        """Get all images that are expected to be in a given directory
        (unsorted).

        Returns an iterable returning the images."""
        assert self.inTransaction
        directory = unicode(os.path.realpath(directory))
        cursor = self.connection.cursor()
        cursor.execute(
            " select id, hash, directory, filename, mtime, width, height"
            " from   image"
            " where  directory = %s",
            directory)
        for (imageid, imghash, directory, filename, mtime, width,
             height) in cursor:
            location = os.path.join(directory, filename)
            if imageid in self.objectcache:
                yield self.objectcache[imageid]
            else:
                yield self._imageFactory(
                    imageid, imghash, location, mtime, width, height)


    def deleteAlbum(self, tag):
        """Delete the album for a given album tag/ID."""
        assert self.inTransaction
        cursor = self.connection.cursor()
        try:
            albumid = int(tag)
        except ValueError:
            albumid = None
        if albumid is None:
            # Tag.
            cursor.execute(
                " select id, tag"
                " from   album"
                " where  tag = %s",
                tag)
        else:
            # ID.
            cursor.execute(
                " select id, tag"
                " from   album"
                " where  id = %s",
                albumid)
        row = cursor.fetchone()
        if not row:
            raise AlbumDoesNotExistError, tag
        albumid, tag = row
        if albumid == _ROOT_ALBUM_ID:
            # Don't delete the root album!
            raise UndeletableAlbumError, tag
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
        for x in albumid, tag:
            if x in self.objectcache:
                del self.objectcache[x]
        self._setModified()
        self.allAlbumsCache = None
        self.orphanAlbumsCache = None


    def createImage(self, path):
        """Add a new, orphaned image to the shelf.

        Returns an Image instance."""
        assert self.inTransaction
        import Image as PILImage
        try:
            pilimg = PILImage.open(path)
            if not pilimg.mode in ("L", "RGB", "CMYK"):
                pilimg = pilimg.convert("RGB")
#        except IOError:
        except: # Work-around for buggy PIL.
            raise NotAnImageError, path
        width, height = pilimg.size
        location = unicode(os.path.realpath(path.encode(self.codeset)),
                           self.codeset)
        mtime = os.path.getmtime(location)
        imghash = computeImageHash(location.encode(self.codeset))
        cursor = self.connection.cursor()
        try:
            cursor.execute(
                " insert into object (id)"
                " values (null)")
            imageid = cursor.lastrowid
            cursor.execute(
                " insert into image (id, hash, directory, filename, mtime,"
                "                    width, height)"
                " values (%s, %s, %s, %s, %s, %s, %s)",
                imageid,
                imghash,
                os.path.dirname(location),
                os.path.basename(location),
                mtime,
                width,
                height)
        except sql.IntegrityError:
            cursor.execute(
                " delete from object"
                " where id = %s",
                imageid)
            raise ImageExistsError, path
        image = self._imageFactory(
            imageid, imghash, location, mtime, width, height)
        image = self.getImage(imageid)
        image.importExifTags()
        self._setModified()
        self.allImagesCache = None
        self.orphanImagesCache = None
        return image


    def getImage(self, ref, identifyByLocation=False):
        """Get the image for a given image ID/hash/location.

        ref should be a reference to an image registered with Kofoto.
        It should be one of the following:

        * An integer (or long) representing an image ID.
        * A string convertible to an integer representing an image ID.
        * A string containing an image hash.
        * A location (path) to an image.

        If ref is a location and identifyByLocation is False (the
        default), the checksum of the image at the given location will
        be computed and used for identification. If ref is a location
        and identifyByLocation is True, the image is identified just
        by the location. Note, though, that an image location is not
        required to be unique in the shelf; if several images have the
        same location, MultipleImagesAtOneLocationError is raised. If
        ref isn't a location, the value of identifyByLocation is
        irrelevant.

        Returns an Image instance.
        """
        assert self.inTransaction
        # Image ID or stringified image ID of an image already in the
        # cache?
        try:
            imageid = int(ref)
        except ValueError:
            imageid = None
        else:
            if imageid in self.objectcache:
                img = self.objectcache[imageid]
                if img.isAlbum():
                    raise ImageDoesNotExistError, imageid
                return img

        queryHeader = (
            " select id, hash, directory, filename, mtime, width, height"
            " from   image")
        if imageid is None:
            #
            # It's a hash or location.
            #

            # Hash of an image already in the cache?
            if ref in self.objectcache:
                img = self.objectcache[ref]
                if img.isAlbum():
                    raise ImageDoesNotExistError, ref
                return img

            # A path to an image in the cache?
            location = ref.encode(self.codeset)
            if os.path.isfile(location):
                if identifyByLocation:
                    location = os.path.realpath(location)
                    cursor = self.connection.cursor()
                    cursor.execute(queryHeader +
                                   " where  directory = %s and filename = %s",
                                   os.path.dirname(
                                       location.decode(self.codeset)),
                                   os.path.basename(
                                       location.decode(self.codeset)))
                    if cursor.rowcount > 1:
                        raise MultipleImagesAtOneLocationError, \
                              location.decode(self.codeset)
                else:
                    imghash = computeImageHash(location)
                    if imghash in self.objectcache:
                        img = self.objectcache[imghash]
                        if img.isAlbum():
                            raise ImageDoesNotExistError, imghash
                        return img
                    cursor = self.connection.cursor()
                    cursor.execute(queryHeader + " where  hash = %s", imghash)
            else:
                imghash = ref
                cursor = self.connection.cursor()
                cursor.execute(queryHeader + " where  hash = %s", imghash)
        else:
            #
            # It's an image ID, but the image wasn't in the cache.
            #
            cursor = self.connection.cursor()
            cursor.execute(queryHeader + " where  id = %s", imageid)
        row = cursor.fetchone()
        if not row:
            raise ImageDoesNotExistError, ref
        imageid, imghash, directory, filename, mtime, width, height = row
        if identifyByLocation:
            if imageid in self.objectcache:
                return self.objectcache[imageid]
        location = os.path.join(directory, filename)
        return self._imageFactory(
            imageid, imghash, location, mtime, width, height)


    def deleteImage(self, ref):
        """Delete the image for a given image ID/hash/location.

        ref should be a reference to an image registered with Kofoto.
        It should be one of the following:

        * An integer (or long) representing an image ID.
        * A string convertible to an integer representing an image ID.
        * A string containing an image hash.
        * A location (path) to an image.
        """
        assert self.inTransaction
        try:
            imageid = int(ref)
        except ValueError:
            imageid = None

        queryHeader = (
            " select id, hash"
            " from   image")
        assert self.inTransaction
        cursor = self.connection.cursor()
        if imageid is None:
            #
            # It's a hash or location.
            #

            # A path to an image in the cache?
            location = ref.encode(self.codeset)
            if os.path.isfile(location):
                imghash = computeImageHash(location)
            else:
                imghash = ref
            cursor.execute(queryHeader + " where  hash = %s", imghash)
        else:
            #
            # It's an image ID.
            #
            cursor.execute(queryHeader + " where  id = %s", imageid)
        row = cursor.fetchone()
        if not row:
            raise ImageDoesNotExistError, ref
        imageid, imghash = row
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
        for x in imageid, imghash:
            if x in self.objectcache:
                del self.objectcache[x]
        self._setModified()
        self.allImagesCache = None
        self.orphanImagesCache = None


    def getObject(self, objid):
        """Get the object for a given object tag/ID."""
        assert self.inTransaction
        if objid in self.objectcache:
            return self.objectcache[objid]
        try:
            return self.getImage(objid)
        except ImageDoesNotExistError:
            try:
                return self.getAlbum(objid)
            except AlbumDoesNotExistError:
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
        try:
            catid = int(tag)
        except ValueError:
            catid = None
        if catid is None:
            # Tag.
            cursor.execute(
                " select id, tag"
                " from   category"
                " where  tag = %s",
                tag)
        else:
            # ID.
            cursor.execute(
                " select id, tag"
                " from   category"
                " where  id = %s",
                catid)
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
        for x in catid, tag:
            if x in self.categorycache:
                del self.categorycache[x]
        self._setModified()


    def getCategory(self, tag):
        """Get a category for a given category tag/ID.

        Returns a Category instance."""
        assert self.inTransaction
        if tag in self.categorycache:
            return self.categorycache[tag]
        cursor = self.connection.cursor()
        try:
            catid = int(tag)
        except ValueError:
            catid = None
        if catid is None:
            # Tag.
            cursor.execute(
                " select id, tag, description"
                " from   category"
                " where  tag = %s",
                tag)
        else:
            # ID.
            cursor.execute(
                " select id, tag, description"
                " from   category"
                " where  id = %s",
                catid)
        row = cursor.fetchone()
        if not row:
            raise CategoryDoesNotExistError, tag
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
        cursor = self.connection.cursor()
        cursor.execute(schema)
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
        orphansalbum = self.createAlbum(u"orphans", u"orphans")
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
        cursor = self.connection.cursor()
        try:
            cursor.execute(
                " select version"
                " from   dbinfo")
        except sql.OperationalError:
            raise ShelfLockedError, self.location
        except sql.DatabaseError:
            raise UnsupportedShelfError, self.location
        version = cursor.fetchone()[0]
        if version != _SHELF_FORMAT_VERSION:
            raise UnsupportedShelfError, self.location


    def _albumFactory(self, albumid, tag, albumtype):
        albumtypemap = {
            "allalbums": AllAlbumsAlbum,
            "allimages": AllImagesAlbum,
            "orphans": OrphansAlbum,
            "plain": PlainAlbum,
            "search": SearchAlbum,
        }
        try:
            album = albumtypemap[albumtype](self, albumid, tag, albumtype)
        except KeyError:
            raise UnknownAlbumTypeError, albumtype
        self.objectcache[albumid] = album
        self.objectcache[tag] = album
        return album


    def _imageFactory(self, imageid, imghash, location, mtime, width, height):
        image = Image(self, imageid, imghash, location, mtime, width, height)
        self.objectcache[imageid] = image
        self.objectcache[unicode(imageid)] = image
        self.objectcache[imghash] = image
        return image


    def _deleteObjectFromParents(self, objid):
        cursor = self.connection.cursor()
        cursor.execute(
            " select distinct album.id, album.tag"
            " from member, album"
            " where member.object = %s and member.album = album.id",
            objid)
        parentinfolist = cursor.fetchall()
        for parentid, parenttag in parentinfolist:
            cursor.execute(
                " select   position"
                " from     member"
                " where    album = %s and object = %s"
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
            for x in parentid, parenttag:
                if x in self.objectcache:
                    del self.objectcache[x]


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


    def _getOrphanAlbumsCache(self):
        assert self.inTransaction
        return self.orphanAlbumsCache


    def _setOrphanAlbumsCache(self, albums):
        assert self.inTransaction
        self.orphanAlbumsCache = albums


    def _getOrphanImagesCache(self):
        assert self.inTransaction
        return self.orphanImagesCache


    def _setOrphanImagesCache(self, images):
        assert self.inTransaction
        self.orphanImagesCache = images


    def _getAllAlbumsCache(self):
        assert self.inTransaction
        return self.allAlbumsCache


    def _setAllAlbumsCache(self, albums):
        assert self.inTransaction
        self.allAlbumsCache = albums


    def _getAllImagesCache(self):
        assert self.inTransaction
        return self.allImagesCache


    def _setAllImagesCache(self, images):
        assert self.inTransaction
        self.allImagesCache = images


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


    def __eq__(self, obj):
        return isinstance(obj, Category) and obj.getId() == self.getId()


    def __ne__(self, obj):
        return not obj == self


    def __hash__(self):
        return self.getId()


class _Object:
    ##############################
    # Public methods.

    def getId(self):
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
            " where  object = %s",
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
            " where  object = %s and name = %s",
            value,
            value.lower(),
            self.getId(),
            name)
        if cursor.rowcount == 0:
            cursor.execute(
                " insert into attribute (object, name, value, lcvalue)"
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
            " where  object = %s and name = %s",
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
                " insert into object_category (object, category)"
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


    ##############################
    # Internal methods.

    def __init__(self, shelf, objid):
        self.shelf = shelf
        self.objid = objid
        self.attributes = {}
        self.allAttributesFetched = False
        self.categories = Set()
        self.allCategoriesFetched = False

    def _categoriesDirty(self):
        self.allCategoriesFetched = False


    def __eq__(self, obj):
        return isinstance(obj, _Object) and obj.getId() == self.getId()


    def __ne__(self, obj):
        return not obj == self


    def __hash__(self):
        return self.getId()


class Album(_Object):
    """Base class of Kofoto albums."""

    ##############################
    # Public methods.

    def getType(self):
        return self.albumtype


    def isMutable(self):
        """Whether the album can be modified with setChildren."""
        raise UnimplementedError


    def getTag(self):
        """Get the tag of the album."""
        return self.tag


    def setTag(self, newtag):
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
        raise UnimplementedError


    def getAlbumChildren(self):
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

    def isMutable(self):
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
        """Set an album's children."""
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

    def getHash(self):
        """Get the hash of the image."""
        return self.hash


    def getLocation(self):
        """Get the last known location of the image."""
        return self.location


    def getModificationTime(self):
        return self.mtime


    def getSize(self):
        return self.size


    def contentChanged(self):
        """Record new image information for an edited image.

        Checksum, width, height and mtime are updated.

        It is assumed that the image location is still correct."""
        self.hash = computeImageHash(self.location)
        import Image as PILImage
        try:
            pilimg = PILImage.open(self.location)
        except IOError:
            raise NotAnImageError, self.location
        self.size = pilimg.size
        self.mtime = os.path.getmtime(self.location)
        cursor = self.shelf._getConnection().cursor()
        cursor.execute(
            " update image"
            " set    hash = %s, width = %s, height = %s, mtime = %s"
            " where  id = %s",
            self.hash,
            self.size[0],
            self.size[1],
            self.mtime,
            self.getId())
        self.shelf._setModified()


    def locationChanged(self, location):
        """Set the last known location of the image.

        The mtime is also updated."""
        cursor = self.shelf._getConnection().cursor()
        location = unicode(os.path.realpath(location))
        try:
            self.mtime = os.path.getmtime(location)
        except OSError:
            self.mtime = 0
        cursor.execute(
            " update image"
            " set    directory = %s, filename = %s, mtime = %s"
            " where  id = %s",
            os.path.dirname(location),
            os.path.basename(location),
            self.mtime,
            self.getId())
        self.location = location
        self.shelf._setModified()


    def isAlbum(self):
        return False


    def importExifTags(self):
        """Read known EXIF tags and add them as attributes."""
        from kofoto import EXIF
        tags = EXIF.process_file(
            file(self.getLocation().encode(self.shelf.codeset), "rb"))

        for tag in ["Image DateTime",
                    "EXIF DateTimeOriginal",
                    "EXIF DateTimeDigitized"]:
            value = tags.get(tag)
            if value and str(value) != "0000:00:00 00:00:00":
                m = re.match(
                    r"(\d{4})[:/-](\d{2})[:/-](\d{2}) (\d{2}):(\d{2}):(\d{2})",
                    str(value))
                if m:
                    self.setAttribute(
                        u"captured",
                        u"%s-%s-%s %s:%s:%s" % m.groups())

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

    def __init__(
        self, shelf, imageid, imghash, location, mtime, width,
        height):
        """Constructor of an Image."""
        _Object.__init__(self, shelf, imageid)
        self.shelf = shelf
        self.hash = imghash
        self.location = location
        self.mtime = mtime
        self.size = width, height


class MagicAlbum(Album):
    """Base class of magic albums."""

    ##############################
    # Public methods.

    def isMutable(self):
        return False


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
        albums = self.shelf._getAllAlbumsCache()
        if albums != None:
            for album in albums:
                yield album
        else:
            cursor = self.shelf._getConnection().cursor()
            cursor.execute(
                " select   id"
                " from     album"
                " order by tag")
            albums = []
            for (albumid,) in cursor:
                album = self.shelf.getAlbum(albumid)
                albums.append(album)
                yield album
            self.shelf._setAllAlbumsCache(albums)


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
        images = self.shelf._getAllImagesCache()
        if images != None:
            for image in images:
                yield image
        else:
            cursor = self.shelf._getConnection().cursor()
            cursor.execute(
                " select   i.id, i.hash, i.directory, i.filename, i.mtime,"
                "          i.width, i.height"
                " from     image as i left join attribute as a"
                " on       i.id = a.object and a.name = 'captured'"
                " order by a.lcvalue, i.directory, i.filename")
            images = []
            for (imageid, imghash, directory, filename, mtime, width,
                 height) in cursor:
                location = os.path.join(directory, filename)
                image = self.shelf._imageFactory(
                    imageid, imghash, location, mtime, width, height)
                images.append(image)
                yield image
            self.shelf._setAllImagesCache(images)


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
                    " select   i.id, i.hash, i.directory, i.filename, i.mtime,"
                    "          i.width, i.height"
                    " from     image as i left join attribute as a"
                    " on       i.id = a.object and a.name = 'captured'"
                    " where    i.id not in (select object from member)"
                    " order by a.lcvalue, i.directory, i.filename")
                images = []
                for (imageid, imghash, directory, filename, mtime, width,
                     height) in cursor:
                    location = os.path.join(directory, filename)
                    image = self.shelf._imageFactory(
                        imageid, imghash, location, mtime, width, height)
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
        query = self.getAttribute(u"query")
        if not query:
            return []
        import kofoto.search
        parser = kofoto.search.Parser(self.shelf)
        try:
            tree = parser.parse(query)
        except (AlbumDoesNotExistError,
                CategoryDoesNotExistError,
                kofoto.search.ParseError):
            return []
        objects = self.shelf.search(tree)
        if includeimages:
            objectlist = list(objects)
        else:
            objectlist = [x for x in objects if x.isAlbum()]

        def sortfn(x, y):
            a = cmp(x.getAttribute(u"captured"), y.getAttribute(u"captured"))
            if a == 0:
                return cmp(x.getId(), y.getId())
            else:
                return a
        objectlist.sort(sortfn)

        return objectlist



######################################################################
### Internal helper functions and classes.

def _createCategoryDAG(connection):
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
