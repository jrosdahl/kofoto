"""Interface to a Kofoto shelf."""

# Be compatible with Python 2.2.
from __future__ import generators

######################################################################
### Libraries.

import sqlite as sql
from kofoto.common import KofotoError
from kofoto.sqlset import SqlSetFactory
import threading

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
_ROOT_ALBUM_DEFAULT_TAG = "root"

######################################################################
### Exceptions.

class FailedWritingError(KofotoError):
    """Kofoto shelf already exists."""
    pass


class ShelfNotFoundError(KofotoError):
    """Kofoto shelf not found."""
    pass


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


class ReservedAlbumTagError(KofotoError):
    """The album tag is reserved for internal purposes."""
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


class ReservedCategoryTagError(KofotoError):
    """The category tag is reserved for internal purposes."""
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
    return m.hexdigest()


def verifyValidAlbumTag(tag):
    try:
        int(tag)
    except ValueError:
        pass
    else:
        raise ReservedAlbumTagError, tag


def verifyValidCategoryTag(tag):
    try:
        int(tag)
    except ValueError:
        pass
    else:
        raise ReservedCategoryTagError, tag


######################################################################
### Public classes.

class Shelf:
    """A Kofoto shelf."""

    ##############################
    # Public methods.

    def __init__(self, location, create=False):
        """Constructor.
        """
        self.location = location
        self.connection = sql.connect(location)
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                " select count(*)"
                " from album")
            self.connection.rollback()
            if create:
                raise FailedWritingError, location
        except sql.OperationalError:
            raise ShelfLockedError, location
        except sql.DatabaseError:
            if create:
                cursor.execute(schema)
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
        # Instantiation of the first cursor starts the transaction in
        # PySQLite, so create one here.
        self.cursor = self.connection.cursor()
        self.sqlsetFactory = SqlSetFactory(self.connection)


    def commit(self):
        """Commit the work on the shelf."""
        try:
            del self.cursor
            self.connection.commit()
        finally:
            self.transactionLock.release()


    def rollback(self):
        """Abort the work on the shelf.

        The changes (if any) will not be saved."""
        try:
            del self.cursor
            self.connection.rollback()
        finally:
            self.transactionLock.release()


    def getStatistics(self):
        self.cursor.execute(
            " select count(*)"
            " from   album")
        nalbums = int(self.cursor.fetchone()[0])
        self.cursor.execute(
            " select count(*)"
            " from   image")
        nimages = int(self.cursor.fetchone()[0])
        return {"nalbums": nalbums, "nimages": nimages}


    def createAlbum(self, tag, albumtype="plain"):
        """Create an empty, orphaned album."""
        verifyValidAlbumTag(tag)
        try:
            self.cursor.execute(
                " insert into object"
                " values (null)",
                locals())
            lastrowid = self.cursor.lastrowid
            self.cursor.execute(
                " insert into album"
                " values (%(lastrowid)s, %(tag)s, 1, %(albumtype)s)",
                locals())
            return self._albumFactory(lastrowid, albumtype)
        except sql.IntegrityError:
            self.cursor.execute(
                " delete from object"
                " where objectid = %(lastrowid)s",
                locals())
            raise AlbumExistsError, tag


    def getAlbum(self, tag):
        """Get the album for a given album tag/ID.

        Returns an Album instance.
        """
        try:
            albumid = int(tag)
            self.cursor.execute(
                " select type"
                " from album"
                " where albumid = %(albumid)s",
                locals())
            if self.cursor.rowcount > 0:
                albumtype = self.cursor.fetchone()[0]
            else:
                raise AlbumDoesNotExistError, tag
        except ValueError:
            self.cursor.execute(
                " select albumid, type"
                " from album"
                " where tag = %(tag)s",
                locals())
            if self.cursor.rowcount > 0:
                albumid, albumtype = self.cursor.fetchone()
            else:
                raise AlbumDoesNotExistError, tag
        return self._albumFactory(albumid, albumtype)


    def getRootAlbum(self):
        """Get the root album.

        Returns an Album object.
        """
        return self.getAlbum("0")


    def getAllAlbums(self):
        """Get all albums in the shelf (unsorted).

        Returns an iterator returning the albums."""
        self.cursor.execute(
            " select albumid, type"
            " from   album")
        for albumid, albumtype in _cursoriter(self.cursor):
            yield self._albumFactory(albumid, albumtype)


    def getAllImages(self):
        """Get all images in the shelf (unsorted).

        Returns an iterator returning the images."""
        self.cursor.execute(
            " select imageid"
            " from   image")
        for (imageid,) in _cursoriter(self.cursor):
            yield Image(self, imageid)


    def deleteAlbum(self, tag):
        """Delete the album for a given album tag/ID."""
        try:
            albumid = int(tag)
        except ValueError:
            self.cursor.execute(
                " select albumid, type"
                " from album"
                " where tag = %(tag)s",
                locals())
            row = self.cursor.fetchone()
            if not row:
                raise AlbumDoesNotExistError, tag
            albumid, albumtype = row
        if albumid == _ROOT_ALBUM_ID:
            # Don't delete the root album!
            raise UndeletableAlbumError, tag
        self.cursor.execute(
            " delete from album"
            " where  albumid = %(albumid)s",
            locals())
        if self.cursor.rowcount == 0:
            raise AlbumDoesNotExistError, tag
        self._deleteObjectFromParents(albumid)
        self.cursor.execute(
            " delete from object"
            " where  objectid = %(albumid)s",
            locals())
        self.cursor.execute(
            " delete from attribute"
            " where  objectid = %(albumid)s",
            locals())


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
        hash = computeImageHash(location)
        try:
            self.cursor.execute(
                " insert into object"
                " values (null)",
                locals())
            imageid = self.cursor.lastrowid
            self.cursor.execute(
                " insert into image"
                " values (%(imageid)s, %(hash)s, %(location)s)",
                locals())
            width, height = pilimg.size
            self.cursor.execute(
                " insert into attribute"
                " values (%(imageid)s, 'width', %(width)s)",
                locals())
            self.cursor.execute(
                " insert into attribute"
                " values (%(imageid)s, 'height', %(height)s)",
                locals())
            image = Image(self, imageid)
            image.importExifTags()
            return image
        except sql.IntegrityError:
            self.cursor.execute(
                " delete from object"
                " where objectid = %(imageid)s",
                locals())
            raise ImageExistsError, path


    def getImage(self, ref):
        """Get the image for a given image hash/ID/path.

        Returns an Image object.
        """
        return Image(self, self._interpretImageReference(ref))


    def deleteImage(self, ref):
        """Delete the image for a given image hash/ID."""
        imageid = self._interpretImageReference(ref)
        self.cursor.execute(
            " delete from image"
            " where  imageid = %(imageid)s",
            locals())
        self._deleteObjectFromParents(imageid)
        self.cursor.execute(
            " delete from object"
            " where  objectid = %(imageid)s",
            locals())
        self.cursor.execute(
            " delete from attribute"
            " where  objectid = %(imageid)s",
            locals())


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
        self.cursor.execute(
            " select distinct name"
            " from   attribute"
            " order by name")
        for (name,) in _cursoriter(self.cursor):
            yield name


    def createCategory(self, tag, desc):
        """Create a category.

        Returns a Category instance."""
        verifyValidCategoryTag(tag)
        try:
            self.cursor.execute(
                " insert into category"
                " values (null, %(tag)s, %(desc)s)",
                locals())
            return Category(self, self.cursor.lastrowid)
        except sql.IntegrityError:
            raise CategoryExistsError, tag


    def deleteCategory(self, tag):
        """Delete a category for a given category tag/ID."""
        try:
            catid = int(tag)
        except ValueError:
            self.cursor.execute(
                " select categoryid"
                " from   category"
                " where  tag = %(tag)s",
                locals())
            row = self.cursor.fetchone()
            if not row:
                raise CategoryDoesNotExistError, tag
            catid = row[0]
        self.cursor.execute(
            " delete from category_child"
            " where  parent = %(catid)s or child = %(catid)s",
            locals())
        self.cursor.execute(
            " delete from object_category"
            " where  categoryid = %(catid)s",
            locals())
        self.cursor.execute(
            " delete from category"
            " where  categoryid = %(catid)s",
            locals())


    def getCategory(self, catid):
        """Get a category for a given category tag/ID.

        Returns a Category instance."""
        self.cursor.execute(
            " select categoryid"
            " from   category"
            " where  categoryid = %(catid)s or tag = %(catid)s",
            locals())
        row = self.cursor.fetchone()
        if not row:
            raise CategoryDoesNotExistError, catid
        return Category(self, row[0])


    def getRootCategories(self):
        """Get the categories that are roots, i.e. have no parents.

        Returns an iterator returning Category instances."""
        self.cursor.execute(
            " select categoryid"
            " from   category"
            " where  categoryid not in (select child from category_child)"
            " order by description",
            locals())
        for (catid,) in _cursoriter(self.cursor):
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

        categorysetTablename = categoryset.getTablename()
        self.cursor.execute(
            " select 'album', objectid, type"
            " from   object_category, album"
            " where  objectid = albumid and"
            "        categoryid in (select * from %(categorysetTablename)s)"
            " union"
            " select 'image', objectid, NULL"
            " from   object_category, image"
            " where  objectid = imageid and"
            "        categoryid in (select * from %(categorysetTablename)s)",
            locals())
        for objtype, objid, atype in _cursoriter(self.cursor):
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

    def _albumFactory(shelf, albumid, albumtype="plain"):
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
        self.cursor.execute(
            " select distinct albumid"
            " from member"
            " where objectid = %(objid)s",
            locals())
        parents = [x[0] for x in self.cursor.fetchall()]
        for parentid in parents:
            self.cursor.execute(
                " select   position"
                " from     member"
                " where    albumid = %(parentid)s and"
                "          objectid = %(objid)s"
                " order by position desc",
                locals())
            positions = [x[0] for x in self.cursor.fetchall()]
            for position in positions:
                self.cursor.execute(
                    " delete from member"
                    " where  albumid = %(parentid)s and"
                    "        position = %(position)s",
                    locals())
                self.cursor.execute(
                    " update member"
                    " set    position = position - 1"
                    " where  albumid = %(parentid)s and"
                    "        position > %(position)s",
                    locals())


    def _interpretImageReference(self, ref):
        """Get the image ID for a given image hash/ID/path."""
        # Check if it's an integer and if so whether it's a valid
        # image ID.
        try:
            imageid = int(ref)
            self.cursor.execute(
                " select imageid"
                " from image"
                " where imageid = %(imageid)s",
                locals())
            if self.cursor.rowcount > 0:
                return int(self.cursor.fetchone()[0])
        except ValueError:
            pass

        # Next, check for a valid hash.
        self.cursor.execute(
            " select imageid"
            " from   image"
            " where  hash = %(ref)s",
            locals())
        if self.cursor.rowcount > 0:
            return int(self.cursor.fetchone()[0])

        # Finally, check whether it's a path to a known file.
        import os
        if os.path.isfile(ref):
            hash = computeImageHash(ref)
            self.cursor.execute(
                " select imageid"
                " from   image"
                " where  hash = %(hash)s",
                locals())
            if self.cursor.rowcount > 0:
                return int(self.cursor.fetchone()[0])

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
            prevleveltablename = levels[-1].getTablename()
            rows = newlevel.runQuery(
                " insert"
                " into   %%(tablename)s"
                " select distinct %(tocolumn)s"
                " from   category_child, %(prevleveltablename)s"
                " where  %(fromcolumn)s = number" % locals())
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
        catid = self.getId()
        self.shelf.cursor.execute(
            " select tag"
            " from   category"
            " where  categoryid = %(catid)s",
            locals())
        return self.shelf.cursor.fetchone()[0]


    def setTag(self, newtag):
        """Set category tag."""
        verifyValidCategoryTag(newtag)
        catid = self.getId()
        self.shelf.cursor.execute(
            " update category"
            " set    tag = %(newtag)s"
            " where  categoryid = %(catid)s",
            locals())


    def getDescription(self):
        """Get category description."""
        catid = self.getId()
        self.shelf.cursor.execute(
            " select description"
            " from   category"
            " where  categoryid = %(catid)s",
            locals())
        return self.shelf.cursor.fetchone()[0]


    def setDescription(self, newdesc):
        """Set category description."""
        catid = self.getId()
        self.shelf.cursor.execute(
            " update category"
            " set    description = %(newdesc)s"
            " where  categoryid = %(catid)s",
            locals())


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
                self.shelf.cursor.execute(
                    " select child"
                    " from   category_child"
                    " where  parent = %(catid)s",
                    {"catid": catid})
                for (childid,) in _cursoriter(self.shelf.cursor):
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
                self.shelf.cursor.execute(
                    " select parent"
                    " from   category_child"
                    " where  child = %(catid)s",
                    {"catid": catid})
                for (parentid,) in self._cursoriter(self.shelf.cursor):
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
            self.shelf.cursor.execute(
                " select child"
                " from   category_child"
                " where  parent = %(parentid)s and child = %(childid)s",
                locals())
            return self.shelf.cursor.rowcount > 0


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
            self.shelf.cursor.execute(
                " insert into category_child"
                " values (%(parentid)s, %(childid)s)",
                locals())
        except sql.IntegrityError:
            raise CategoriesAlreadyConnectedError, (self.getTag(),
                                                    category.getTag())


    def disconnectChild(self, category):
        """Remove a parent-child link between this category and a category."""
        parentid = self.getId()
        childid = category.getId()
        self.shelf.cursor.execute(
            " delete from category_child"
            " where  parent = %(parentid)s and child = %(childid)s",
            locals())


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
        objid = self.objid
        self.shelf.cursor.execute(
            " select value"
            " from   attribute"
            " where  objectid = %(objid)s and"
            "        name = %(name)s",
            locals())
        if self.shelf.cursor.rowcount > 0:
            return self.shelf.cursor.fetchone()[0]
        else:
            return None


    def getAttributeMap(self):
        """Get a map of all attributes."""
        objid = self.objid
        self.shelf.cursor.execute(
            " select name, value"
            " from   attribute"
            " where  objectid = %(objid)s",
            locals())
        map = {}
        for key, value in self.shelf.cursor.fetchall():
            map[key] = value
        return map


    def getAttributeNames(self):
        """Get all attribute names.

        Returns an iterator returning the attributes."""
        objid = self.objid
        self.shelf.cursor.execute(
            " select name"
            " from   attribute"
            " where  objectid = %(objid)s"
            " order by name",
            locals())
        for (name,) in _cursoriter(self.shelf.cursor):
            yield name


    def setAttribute(self, name, value):
        """Set an attribute value."""
        objid = self.objid
        self.shelf.cursor.execute(
            " update attribute"
            " set    value = %(value)s"
            " where  objectid = %(objid)s and"
            "        name = %(name)s",
            locals())
        if self.shelf.cursor.rowcount == 0:
            self.shelf.cursor.execute(
                " insert into attribute"
                " values (%(objid)s, %(name)s, %(value)s)",
            locals())


    def deleteAttribute(self, name):
        """Delete an attribute."""
        objid = self.objid
        self.shelf.cursor.execute(
            " delete from attribute"
            " where  objectid = %(objid)s and"
            "        name = %(name)s",
            locals())


    def addCategory(self, category):
        """Add a category."""
        objid = self.getId()
        catid = category.getId()
        try:
            self.shelf.cursor.execute(
                " insert into object_category"
                " values (%(objid)s, %(catid)s)",
                locals())
        except sql.IntegrityError:
            raise CategoryPresentError, (objid, catid)


    def removeCategory(self, category):
        """Remove a category."""
        objid = self.getId()
        catid = category.getId()
        self.shelf.cursor.execute(
            " delete from object_category"
            " where objectid = %(objid)s and categoryid = %(catid)s",
            locals())


    def getCategories(self, recursive=False):
        """Get categories for this object.

        Returns an iterator returning the categories."""
        def helper():
            objid = self.getId()
            self.shelf.cursor.execute(
                " select categoryid from object_category"
                " where  objectid = %(objid)s",
                locals())
            for (catid,) in _cursoriter(self.shelf.cursor):
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
        albumid = self.getId()
        self.shelf.cursor.execute(
            " select tag"
            " from   album"
            " where  albumid = %(albumid)s",
            locals())
        return self.shelf.cursor.fetchone()[0]


    def setTag(self, newtag):
        verifyValidAlbumTag(newtag)
        albumid = self.getId()
        self.shelf.cursor.execute(
            " update album"
            " set    tag = %(newtag)s"
            " where  albumid = %(albumid)s",
            locals())


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
        albumid = self.getId()
        self.shelf.cursor.execute(
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
            locals())
        for objtype, position, objid, atype in _cursoriter(self.shelf.cursor):
            if objtype == "album":
                yield self.shelf._albumFactory(objid, atype)
            else:
                yield Image(self.shelf, objid)


    def setChildren(self, children):
        """Set an album's children."""
        albumid = self.getId()
        self.shelf.cursor.execute(
            "-- types int")
        self.shelf.cursor.execute(
            " select count(position)"
            " from   member"
            " where  albumid = %(albumid)s",
            locals())
        oldchcnt = self.shelf.cursor.fetchone()[0]
        newchcnt = len(children)
        for ix in range(newchcnt):
            childid = children[ix].getId()
            if ix < oldchcnt:
                self.shelf.cursor.execute(
                    " update member"
                    " set    objectid = %(childid)s"
                    " where  albumid = %(albumid)s and"
                    "        position = %(ix)s",
                    locals())
            else:
                self.shelf.cursor.execute(
                    " insert into member"
                    " values (%(albumid)s, %(ix)s, %(childid)s)",
                    locals())
        self.shelf.cursor.execute(
            " delete from member"
            " where  albumid = %(albumid)s and"
            "        position >= %(newchcnt)s",
            locals())


class Image(_Object):
    """A Kofoto image."""

    ##############################
    # Public methods.

    def getLocation(self):
        """Get the last known location of the image."""
        imageid = self.getId()
        self.shelf.cursor.execute(
            " select location"
            " from   image"
            " where  imageid = %(imageid)s",
            locals())
        return self.shelf.cursor.fetchone()[0]


    def setLocation(self, location):
        """Set the last known location of the image."""
        imageid = self.getId()
        self.shelf.cursor.execute(
            " update image"
            " set    location = %(location)s"
            " where  imageid = %(imageid)s",
            locals())


    def getHash(self):
        """Get the hash of the image."""
        imageid = self.getId()
        self.shelf.cursor.execute(
            " select hash"
            " from   image"
            " where  imageid = %(imageid)s",
            locals())
        return self.shelf.cursor.fetchone()[0]


    def setHash(self, hash):
        """Set the hash of the image."""
        imageid = self.getId()
        self.shelf.cursor.execute(
            " update image"
            " set    hash = %(hash)s"
            " where  imageid = %(imageid)s",
            locals())


    def isAlbum(self):
        return False


    def importExifTags(self):
        """Read known EXIF tags and add them as attributes."""
        import EXIF
        tags = EXIF.process_file(file(self.getLocation(), "rb"))

        for tag in ["Image DateTime",
                    "EXIF DateTimeOriginal",
                    "EXIF DateTimeDigitized"]:
            value = tags.get(tag)
            if value:
                a = str(value).split(":")
                if len(a) == 5:
                    value = "-".join(a[0:2] + [":".join(a[2:5])])
                    self.setAttribute("timestamp", value)

        value = tags.get("EXIF ExposureTime")
        if value:
            self.setAttribute("exposuretime", str(value))
        value = tags.get("EXIF FNumber")
        if value:
            self.setAttribute("fnumber", str(value))
        value = tags.get("EXIF Flash")
        if value:
            self.setAttribute("flash", str(value))
        value = tags.get("EXIF FocalLength")
        if value:
            self.setAttribute("focallength", str(value))
        value = tags.get("Image Make")
        if value:
            self.setAttribute("cameramake", str(value))
        value = tags.get("Image Model")
        if value:
            self.setAttribute("cameramodel", str(value))
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
                self.setAttribute("orientation", m[str(value)])
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
        self.shelf.cursor.execute(
            " select   albumid, type"
            " from     album"
            " order by tag")
        for (objid, albumtype) in _cursoriter(self.shelf.cursor):
            yield self.shelf._albumFactory(objid, albumtype)


class AllImagesAlbum(MagicAlbum):
    """An album with all images, sorted by timestamp."""

    ##############################
    # Public methods.

    def getChildren(self):
        """Get the album's children.

        Returns an iterator returning the images.
        """
        self.shelf.cursor.execute(
            " select   imageid"
            " from     image left join attribute"
            " on       imageid = objectid"
            " where    name = 'timestamp'"
            " order by value, location")
        for (objid,) in _cursoriter(self.shelf.cursor):
            yield Image(self.shelf, objid)


class OrphansAlbum(MagicAlbum):
    """An album with all albums and images that are orphans."""

    ##############################
    # Public methods.

    def getChildren(self):
        """Get the album's children.

        Returns an iterator returning the images.
        """
        rootid = _ROOT_ALBUM_ID
        self.shelf.cursor.execute(
            " select   albumid, type"
            " from     album"
            " where    albumid not in (select objectid from member) and"
            "          albumid != %(rootid)s"
            " order by tag",
            locals())
        for albumid, albumtype in _cursoriter(self.shelf.cursor):
            yield self.shelf._albumFactory(albumid, albumtype)
        self.shelf.cursor.execute(
            " select   imageid"
            " from     image left join attribute"
            " on       imageid = objectid"
            " where    imageid not in (select objectid from member) and"
            "          name = 'timestamp'"
            " order by value, location")
        for (imageid,) in _cursoriter(self.shelf.cursor):
            yield Image(self.shelf, imageid)


######################################################################
### Internal helper functions.

def _cursoriter(cursor):
    while True:
        rows = cursor.fetchmany(17)
        if not rows:
            break
        for row in rows:
            yield row
