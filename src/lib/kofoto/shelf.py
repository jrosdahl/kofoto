"""Interface to a Kofoto shelf."""

# Be compatible with Python 2.2.
from __future__ import generators

######################################################################
### Libraries.

import re
import threading
import sqlite as sql
from types import *
from kofoto.common import KofotoError
from kofoto.sqlset import SqlSetFactory

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
        -- Last known location (local pathname) of the image.
        location    VARCHAR(256) NOT NULL,

        UNIQUE      (hash),
        UNIQUE      (location),
        FOREIGN KEY (imageid) REFERENCES object,
        PRIMARY KEY (imageid)
    );

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
    try:
        int(tag)
    except ValueError:
        if re.search(r"\s", tag):
            raise BadAlbumTagError, tag
    else:
        raise BadAlbumTagError, tag


def verifyValidCategoryTag(tag):
    try:
        int(tag)
    except ValueError:
        if re.search(r"\s", tag):
            raise BadCategoryTagError, tag
    else:
        raise BadCategoryTagError, tag


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
        if _DEBUG:
            logfile = file("sql.log", "a")
        else:
            logfile = None
        self.connection = _UnicodeConnectionDecorator(
            sql.connect(location,
                        client_encoding="UTF-8",
                        command_log_file=logfile),
            "UTF-8")
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                " select version"
                " from   dbinfo")
            if cursor.fetchone()[0] != 0:
                raise UnsupportedShelfError, location
            self.connection.rollback()
            if create:
                raise FailedWritingError, location
        except sql.OperationalError:
            raise ShelfLockedError, location
        except sql.DatabaseError:
            if create:
                cursor.execute(schema)
                cursor.execute(
                    " insert into dbinfo"
                    " values (0)")
                cursor.execute(
                    " insert into object"
                    " values (%s)",
                    _ROOT_ALBUM_ID)
                cursor.execute(
                    " insert into album"
                    " values (%s, %s, 0, 'plain')",
                    _ROOT_ALBUM_ID,
                    _ROOT_ALBUM_DEFAULT_TAG)
                self.connection.commit()
            else:
                raise ShelfNotFoundError, location
        self.transactionLock = threading.Lock()


    def begin(self):
        """Begin working with the shelf."""
        self.transactionLock.acquire()
        # In PySQLite, the transaction starts when the first SQL
        # command is executed, so execute a dummy command here.
        cursor = self.connection.cursor()
        cursor.execute("select * from dbinfo")
        self.sqlsetFactory = SqlSetFactory(self.connection)


    def commit(self):
        """Commit the work on the shelf."""
        try:
            self.connection.commit()
        finally:
            self.transactionLock.release()


    def rollback(self):
        """Abort the work on the shelf.

        The changes (if any) will not be saved."""
        try:
            self.connection.rollback()
        finally:
            self.transactionLock.release()


    def getStatistics(self):
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
        """Create an empty, orphaned album."""
        verifyValidAlbumTag(tag)
        cursor = self.connection.cursor()
        try:
            cursor.execute(
                " insert into object"
                " values (null)")
            lastrowid = cursor.lastrowid
            cursor.execute(
                " insert into album"
                " values (%s, %s, 1, %s)",
                lastrowid,
                tag,
                albumtype)
            return self._albumFactory(lastrowid, albumtype)
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
        cursor = self.connection.cursor()
        try:
            albumid = int(tag)
            cursor.execute(
                " select type"
                " from album"
                " where albumid = %s",
                albumid)
            if cursor.rowcount > 0:
                albumtype = cursor.fetchone()[0]
            else:
                raise AlbumDoesNotExistError, tag
        except ValueError:
            cursor.execute(
                " select albumid, type"
                " from album"
                " where tag = %s",
                tag)
            if cursor.rowcount > 0:
                albumid, albumtype = cursor.fetchone()
            else:
                raise AlbumDoesNotExistError, tag
        return self._albumFactory(albumid, albumtype)


    def getRootAlbum(self):
        """Get the root album.

        Returns an Album object.
        """
        return self.getAlbum(_ROOT_ALBUM_ID)


    def getAllAlbums(self):
        """Get all albums in the shelf (unsorted).

        Returns an iterator returning the albums."""
        cursor = self.connection.cursor()
        cursor.execute(
            " select albumid, type"
            " from   album")
        for albumid, albumtype in cursor:
            yield self._albumFactory(albumid, albumtype)


    def getAllImages(self):
        """Get all images in the shelf (unsorted).

        Returns an iterator returning the images."""
        cursor = self.connection.cursor()
        cursor.execute(
            " select imageid"
            " from   image")
        for (imageid,) in cursor:
            yield Image(self, imageid)


    def deleteAlbum(self, tag):
        """Delete the album for a given album tag/ID."""
        cursor = self.connection.cursor()
        try:
            albumid = int(tag)
        except ValueError:
            cursor.execute(
                " select albumid, type"
                " from album"
                " where tag = %s",
                tag)
            row = cursor.fetchone()
            if not row:
                raise AlbumDoesNotExistError, tag
            albumid, albumtype = row
        if albumid == _ROOT_ALBUM_ID:
            # Don't delete the root album!
            raise UndeletableAlbumError, tag
        cursor.execute(
            " delete from album"
            " where  albumid = %s",
            albumid)
        if cursor.rowcount == 0:
            raise AlbumDoesNotExistError, tag
        self._deleteObjectFromParents(albumid)
        cursor.execute(
            " delete from object"
            " where  objectid = %s",
            albumid)
        cursor.execute(
            " delete from attribute"
            " where  objectid = %s",
            albumid)


    def createImage(self, path):
        """Add a new, orphaned image to the shelf.

        The ID of the image is returned."""
        import Image as PILImage
        try:
            pilimg = PILImage.open(path)
        except IOError:
            raise NotAnImageError, path

        import os
        location = os.path.abspath(path)
        hash = computeImageHash(location.encode(self.codeset))
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                " insert into object"
                " values (null)")
            imageid = cursor.lastrowid
            cursor.execute(
                " insert into image"
                " values (%s, %s, %s)",
                imageid,
                hash,
                location)
            width, height = pilimg.size
            cursor.execute(
                " insert into attribute"
                " values (%s, 'width', %s)",
                imageid,
                width)
            cursor.execute(
                " insert into attribute"
                " values (%s, 'height', %s)",
                imageid,
                height)
            image = Image(self, imageid)
            image.importExifTags()
            return image
        except sql.IntegrityError:
            cursor.execute(
                " delete from object"
                " where objectid = %s",
                imageid)
            raise ImageExistsError, path


    def getImage(self, ref):
        """Get the image for a given image hash/ID/path.

        Returns an Image object.
        """
        return Image(self, self._interpretImageReference(ref))


    def deleteImage(self, ref):
        """Delete the image for a given image hash/ID."""
        imageid = self._interpretImageReference(ref)
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


    def getObject(self, objid):
        """Get the object for a given object tag/ID."""
        try:
            return self.getAlbum(objid)
        except AlbumDoesNotExistError:
            try:
                return self.getImage(objid)
            except ImageDoesNotExistError:
                raise ObjectDoesNotExistError, objid


    def deleteObject(self, objid):
        """Get the object for a given object tag/ID."""
        try:
            self.deleteImage(objid)
        except ImageDoesNotExistError:
            try:
                self.deleteAlbum(objid)
            except AlbumDoesNotExistError:
                raise ObjectDoesNotExistError, objid


    def getAllAttributeNames(self):
        """Get all used attribute names in the shelf (sorted).

        Returns an iterator the attribute names."""
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
        verifyValidCategoryTag(tag)
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                " insert into category"
                " values (null, %s, %s)",
                tag,
                desc)
            return Category(self, cursor.lastrowid)
        except sql.IntegrityError:
            raise CategoryExistsError, tag


    def deleteCategory(self, tag):
        """Delete a category for a given category tag/ID."""
        cursor = self.connection.cursor()
        try:
            catid = int(tag)
        except ValueError:
            cursor.execute(
                " select categoryid"
                " from   category"
                " where  tag = %s",
                tag)
            row = cursor.fetchone()
            if not row:
                raise CategoryDoesNotExistError, tag
            catid = row[0]
        cursor.execute(
            " delete from category_child"
            " where  parent = %s or child = %s",
            catid,
            catid)
        cursor.execute(
            " delete from object_category"
            " where  categoryid = %s",
            catid)
        cursor.execute(
            " delete from category"
            " where  categoryid = %s",
            catid)


    def getCategory(self, catid):
        """Get a category for a given category tag/ID.

        Returns a Category instance."""
        cursor = self.connection.cursor()
        cursor.execute(
            " select categoryid"
            " from   category"
            " where  categoryid = %s or tag = %s",
            catid,
            catid)
        row = cursor.fetchone()
        if not row:
            raise CategoryDoesNotExistError, catid
        return Category(self, row[0])


    def getRootCategories(self):
        """Get the categories that are roots, i.e. have no parents.

        Returns an iterator returning Category instances."""
        cursor = self.connection.cursor()
        cursor.execute(
            " select categoryid"
            " from   category"
            " where  categoryid not in (select child from category_child)"
            " order by description")
        for (catid,) in cursor:
            yield Category(self, catid)


    def getObjectsForCategory(self, category, recursive=False):
        """Get all objects for a category.

        Returns an iterator returning Album/Image instances."""
        catid = category.getId()
        if recursive:
            categoryset = self._recursiveComputeCategoryIds([catid],
                                                            descendants=True)
        else:
            categoryset = self.sqlsetFactory.newSet()
            categoryset.add(catid)

        cursor = self.connection.cursor()
        cursor.execute(
            " select 'album', objectid, type"
            " from   object_category, album"
            " where  objectid = albumid and"
            "        categoryid in (select * from %(categorysetTablename)s)"
            " union"
            " select 'image', objectid, NULL"
            " from   object_category, image"
            " where  objectid = imageid and"
            "        categoryid in (select * from %(categorysetTablename)s)",
            {"categorysetTablename": categoryset.getTablename()})
        for objtype, objid, atype in cursor:
            if objtype == "album":
                yield self._albumFactory(objid, atype)
            else:
                yield Image(self, objid)


    def search(self, expr):
        """Search for objects matching an expression.

        Currently, you can only search for objects matching a single
        category tag.

        Returns an iterator returning the objects."""
        try:
            category = self.getCategory(expr)
            return self.getObjectsForCategory(category, True)
        except CategoryDoesNotExistError:
            raise SearchExpressionParseError, "unknown category: %s" % expr


    ##############################
    # Internal methods.

    def _albumFactory(shelf, albumid, albumtype=u"plain"):
        albumtypemap = {
            "allalbums": AllAlbumsAlbum,
            "allimages": AllImagesAlbum,
            "orphans": OrphansAlbum,
            "plain": PlainAlbum,
        }
        try:
            return albumtypemap[albumtype](shelf, albumid, albumtype)
        except KeyError:
            raise UnknownAlbumTypeError, albumtype


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


    def _interpretImageReference(self, ref):
        """Get the image ID for a given image hash/ID/path."""
        # Check if it's an integer and if so whether it's a valid
        # image ID.
        cursor = self.connection.cursor()
        try:
            imageid = int(ref)
            cursor.execute(
                " select imageid"
                " from   image"
                " where  imageid = %s",
                imageid)
            if cursor.rowcount > 0:
                return imageid
        except ValueError:
            pass

        # Next, check for a valid hash.
        cursor.execute(
            " select imageid"
            " from   image"
            " where  hash = %s",
            ref)
        if cursor.rowcount > 0:
            return int(cursor.fetchone()[0])

        # Finally, check whether it's a path to a known file.
        import os
        if os.path.isfile(ref.encode(self.codeset)):
            cursor.execute(
                " select imageid"
                " from   image"
                " where  hash = %s",
                computeImageHash(ref.encode(self.codeset)))
            if cursor.rowcount > 0:
                return int(cursor.fetchone()[0])

        # Oh well.
        raise ImageDoesNotExistError, ref


    def _getAncestorCategoryIds(self, catid):
        return self._recursiveComputeCategoryIds([catid], False)


    def _getDescendantCategoryIds(self, catid):
        return self._recursiveComputeCategoryIds([catid], True)


    def _recursiveComputeCategoryIds(self, catids, descendants):
        if descendants:
            fromcolumn = "parent"
            tocolumn = "child"
        else:
            fromcolumn = "child"
            tocolumn = "parent"

        startlevel = self.sqlsetFactory.newSet()
        for catid in catids:
            startlevel.add(catid)
        levels = [startlevel]
        while True:
            newlevel = self.sqlsetFactory.newSet()
            rows = newlevel.runQuery(
                " insert"
                " into   %%(tablename)s"
                " select distinct %(tocolumn)s"
                " from   category_child, %(prevleveltablename)s"
                " where  %(fromcolumn)s = number" % {
                    "fromcolumn": fromcolumn,
                    "prevleveltablename": levels[-1].getTablename(),
                    "tocolumn": tocolumn,
                })
            levels.append(newlevel)
            if rows == 0:
                break
        result = levels.pop()
        for level in levels:
            result |= level
        return result


class Category:
    """A Kofoto category."""

    ##############################
    # Public methods.

    def getId(self):
        """Get category ID."""
        return self.catid


    def getTag(self):
        """Get category tag."""
        cursor = self.shelf.connection.cursor()
        cursor.execute(
            " select tag"
            " from   category"
            " where  categoryid = %s",
            self.getId())
        return cursor.fetchone()[0]


    def setTag(self, newtag):
        """Set category tag."""
        verifyValidCategoryTag(newtag)
        cursor = self.shelf.connection.cursor()
        cursor.execute(
            " update category"
            " set    tag = %s"
            " where  categoryid = %s",
            newtag,
            self.getId())


    def getDescription(self):
        """Get category description."""
        cursor = self.shelf.connection.cursor()
        cursor.execute(
            " select description"
            " from   category"
            " where  categoryid = %s",
            self.getId())
        return cursor.fetchone()[0]


    def setDescription(self, newdesc):
        """Set category description."""
        cursor = self.shelf.connection.cursor()
        cursor.execute(
            " update category"
            " set    description = %s"
            " where  categoryid = %s",
            newdesc,
            self.getId())


    def getChildren(self, recursive=False):
        """Get child categories.

        If recursive is true, get all descendants. If recursive is
        false, get only immediate children. Returns an iterator
        returning of Category instances (unordered)."""
        catid = self.getId()
        if recursive:
            childids = self.shelf._getDescendantCategoryIds(catid)
        else:
            def helper():
                cursor = self.shelf.connection.cursor()
                cursor.execute(
                    " select child"
                    " from   category_child"
                    " where  parent = %s",
                    catid)
                for (childid,) in cursor:
                    yield childid
            childids = helper()
        for childid in childids:
            yield Category(self.shelf, childid)


    def getParents(self, recursive=False):
        """Get parent categories.

        If recursive is true, get all ancestors. If recursive is
        false, get only immediate parents. Returns an iterator
        returning of Category instances (unordered)."""
        catid = self.getId()
        if recursive:
            parentids = self.shelf._getAncestorCategoryIds(catid)
        else:
            def helper():
                cursor = self.shelf.connection.cursor()
                cursor.execute(
                    " select parent"
                    " from   category_child"
                    " where  child = %s",
                    catid)
                for (parentid,) in cursor:
                    yield parentid
            parentids = helper()
        for parentid in parentids:
            yield Category(self.shelf, parentid)


    def isChildOf(self, category, recursive=False):
        """Check whether this category is a child or descendant of a
        category.

        If recursive is true, check if the category is a descendant of
        this category, otherwise just consider immediate children."""
        parentid = category.getId()
        childid = self.getId()
        if recursive:
            return childid in self.shelf._getDescendantCategoryIds(parentid)
        else:
            cursor = self.shelf.connection.cursor()
            cursor.execute(
                " select child"
                " from   category_child"
                " where  parent = %s and child = %s",
                parentid,
                childid)
            return cursor.rowcount > 0


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
        childDescendants = self.shelf._recursiveComputeCategoryIds([childid],
                                                                   True)
        if parentid in childDescendants or parentid == childid:
            raise CategoryLoopError, (self.getTag(), category.getTag())
        try:
            cursor = self.shelf.connection.cursor()
            cursor.execute(
                " insert into category_child"
                " values (%s, %s)",
                parentid,
                childid)
        except sql.IntegrityError:
            raise CategoriesAlreadyConnectedError, (self.getTag(),
                                                    category.getTag())


    def disconnectChild(self, category):
        """Remove a parent-child link between this category and a category."""
        cursor = self.shelf.connection.cursor()
        cursor.execute(
            " delete from category_child"
            " where  parent = %s and child = %s",
            self.getId(),
            category.getId())


    ##############################
    # Internal methods.

    def __init__(self, shelf, catid):
        self.shelf = shelf
        self.catid = catid


class _Object:
    def __init__(self, shelf, objid):
        self.shelf = shelf
        self.objid = objid


    def getId(self):
        return self.objid


    def getAttribute(self, name):
        """Get the value of an attribute.

        Returns the value as string, or None if there was no matching
        attribute.
        """
        cursor = self.shelf.connection.cursor()
        cursor.execute(
            " select value"
            " from   attribute"
            " where  objectid = %s and name = %s",
            self.getId(),
            name)
        if cursor.rowcount > 0:
            return cursor.fetchone()[0]
        else:
            return None


    def getAttributeMap(self):
        """Get a map of all attributes."""
        cursor = self.shelf.connection.cursor()
        cursor.execute(
            " select name, value"
            " from   attribute"
            " where  objectid = %s",
            self.getId())
        map = {}
        for key, value in cursor:
            map[key] = value
        return map


    def getAttributeNames(self):
        """Get all attribute names.

        Returns an iterator returning the attributes."""
        cursor = self.shelf.connection.cursor()
        cursor.execute(
            " select name"
            " from   attribute"
            " where  objectid = %s"
            " order by name",
            self.getId())
        for (name,) in cursor:
            yield name


    def setAttribute(self, name, value):
        """Set an attribute value."""
        cursor = self.shelf.connection.cursor()
        cursor.execute(
            " update attribute"
            " set    value = %s"
            " where  objectid = %s and name = %s",
            value,
            self.getId(),
            name)
        if cursor.rowcount == 0:
            cursor.execute(
                " insert into attribute"
                " values (%s, %s, %s)",
                self.getId(),
                name,
                value)


    def deleteAttribute(self, name):
        """Delete an attribute."""
        cursor = self.shelf.connection.cursor()
        cursor.execute(
            " delete from attribute"
            " where  objectid = %s and name = %s",
            self.getId(),
            name)


    def addCategory(self, category):
        """Add a category."""
        objid = self.getId()
        catid = category.getId()
        try:
            cursor = self.shelf.connection.cursor()
            cursor.execute(
                " insert into object_category"
                " values (%s, %s)",
                objid,
                catid)
        except sql.IntegrityError:
            raise CategoryPresentError, (objid, catid)


    def removeCategory(self, category):
        """Remove a category."""
        cursor = self.shelf.connection.cursor()
        cursor.execute(
            " delete from object_category"
            " where objectid = %s and categoryid = %s",
            self.getId(),
            category.getId())


    def getCategories(self, recursive=False):
        """Get categories for this object.

        Returns an iterator returning the categories."""
        def helper():
            cursor = self.shelf.connection.cursor()
            cursor.execute(
                " select categoryid from object_category"
                " where  objectid = %s",
                self.getId())
            for (catid,) in cursor:
                yield catid
        categoryids = helper()
        if recursive:
            categoryids = self.shelf._recursiveComputeCategoryIds(categoryids,
                                                                  True)
        for catid in categoryids:
            yield Category(self.shelf, catid)


class Album(_Object):
    """Base class of Kofoto albums."""

    ##############################
    # Public methods.

    def getType(self):
        return self.albumtype


    def getTag(self):
        """Get the tag of the album."""
        cursor = self.shelf.connection.cursor()
        cursor.execute(
            " select tag"
            " from   album"
            " where  albumid = %s",
            self.getId())
        return cursor.fetchone()[0]


    def setTag(self, newtag):
        verifyValidAlbumTag(newtag)
        cursor = self.shelf.connection.cursor()
        cursor.execute(
            " update album"
            " set    tag = %s"
            " where  albumid = %s",
            newtag,
            self.getId())


    def getChildren(self):
        raise UnimplementedError


    def setChildren(self):
        raise UnimplementedError


    def isAlbum(self):
        return True


    ##############################
    # Internal methods.

    def __init__(self, shelf, albumid, albumtype):
        """Constructor of an Album."""
        _Object.__init__(self, shelf, albumid)
        self.shelf = shelf
        self.albumtype = albumtype


class PlainAlbum(Album):
    """A plain Kofoto album."""

    ##############################
    # Public methods.

    def getChildren(self):
        """Get the album's children.

        Returns an iterator returning Album/Images instances.
        """
        cursor = self.shelf.connection.cursor()
        cursor.execute(
            " select 'album', position, member.objectid, album.type"
            " from   member, album"
            " where  member.albumid = %(albumid)s and"
            "        member.objectid = album.albumid"
            " union"
            " select 'image', position, member.objectid, NULL"
            " from   member, image"
            " where  member.albumid = %(albumid)s and"
            "        member.objectid = image.imageid"
            " order by position",
            {"albumid": self.getId()})
        for objtype, position, objid, atype in cursor:
            if objtype == "album":
                yield self.shelf._albumFactory(objid, atype)
            else:
                yield Image(self.shelf, objid)


    def setChildren(self, children):
        """Set an album's children."""
        albumid = self.getId()
        cursor = self.shelf.connection.cursor()
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
                    " insert into member"
                    " values (%s, %s, %s)",
                    albumid,
                    ix,
                    childid)
        cursor.execute(
            " delete from member"
            " where  albumid = %s and position >= %s",
            albumid,
            newchcnt)


class Image(_Object):
    """A Kofoto image."""

    ##############################
    # Public methods.

    def getLocation(self):
        """Get the last known location of the image."""
        cursor = self.shelf.connection.cursor()
        cursor.execute(
            " select location"
            " from   image"
            " where  imageid = %s",
            self.getId())
        return cursor.fetchone()[0]


    def setLocation(self, location):
        """Set the last known location of the image."""
        cursor = self.shelf.connection.cursor()
        cursor.execute(
            " update image"
            " set    location = %s"
            " where  imageid = %s",
            location,
            self.getId())


    def getHash(self):
        """Get the hash of the image."""
        cursor = self.shelf.connection.cursor()
        cursor.execute(
            " select hash"
            " from   image"
            " where  imageid = %s",
            self.getId())
        return cursor.fetchone()[0]


    def setHash(self, hash):
        """Set the hash of the image."""
        cursor = self.shelf.connection.cursor()
        cursor.execute(
            " update image"
            " set    hash = %s"
            " where  imageid = %s",
            hash,
            self.getId())


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
            if value:
                a = str(value).split(":")
                if len(a) == 5:
                    value = u"-".join(a[0:2] + [":".join(a[2:5])])
                    self.setAttribute(u"timestamp", value)

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


    ##############################
    # Internal methods.

    def __init__(self, shelf, imageid):
        """Constructor of an Image."""
        _Object.__init__(self, shelf, imageid)
        self.shelf = shelf
        self.imageid = imageid
        self.attributeMap = {}
        self.children = []


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

        Returns an iterator returning the albums.
        """
        cursor = self.shelf.connection.cursor()
        cursor.execute(
            " select   albumid, type"
            " from     album"
            " order by tag")
        for (objid, albumtype) in cursor:
            yield self.shelf._albumFactory(objid, albumtype)


class AllImagesAlbum(MagicAlbum):
    """An album with all images, sorted by timestamp."""

    ##############################
    # Public methods.

    def getChildren(self):
        """Get the album's children.

        Returns an iterator returning the images.
        """
        cursor = self.shelf.connection.cursor()
        cursor.execute(
            " select   imageid"
            " from     image left join attribute"
            " on       imageid = objectid"
            " where    name = 'timestamp'"
            " order by value, location")
        for (objid,) in cursor:
            yield Image(self.shelf, objid)


class OrphansAlbum(MagicAlbum):
    """An album with all albums and images that are orphans."""

    ##############################
    # Public methods.

    def getChildren(self):
        """Get the album's children.

        Returns an iterator returning the images.
        """
        cursor = self.shelf.connection.cursor()
        cursor.execute(
            " select   albumid, type"
            " from     album"
            " where    albumid not in (select objectid from member) and"
            "          albumid != %s"
            " order by tag",
            _ROOT_ALBUM_ID)
        for albumid, albumtype in cursor:
            yield self.shelf._albumFactory(albumid, albumtype)
        cursor.execute(
            " select   imageid"
            " from     image left join attribute"
            " on       imageid = objectid"
            " where    imageid not in (select objectid from member) and"
            "          name = 'timestamp'"
            " order by value, location")
        for (imageid,) in cursor:
            yield Image(self.shelf, imageid)


######################################################################
### Internal helper functions and classes.

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
            if isinstance(col, StringType):
                result.append(unicode(col, self.encoding))
            else:
                result.append(col)
        return result

    def _assertUnicode(self, obj):
        if isinstance(obj, StringType):
            raise AssertionError, ("non-Unicode string", obj)
        elif isinstance(obj, ListType) or isinstance(obj, TupleType):
            for elem in obj:
                self._assertUnicode(elem)
        elif isinstance(obj, DictType):
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
