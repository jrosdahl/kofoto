"""Interface to a Kofoto shelf."""

######################################################################
### Libraries

import md5
import sqlite as sql
from kofoto.common import KofotoError

schema = """
    -- EER diagram without attributes:
    -- 
    --                                ,^.
    --              N +--------+ 1  ,'   '.  N +-----------+
    --      +---------| object |---<  has  >===| attribute |
    --      |         +--------+    '.   ,'    +-----------+
    --    ,/\.          |    |        'v'
    --  ,'    '.     __/      \__
    -- < member >   |            |
    --  '.    ,'   \|/          \|/
    --    '\/'      |            |
    --      | 1 +-------+    +-------+
    --      +---| album |    | image |
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

    CREATE TABLE album (
        -- Identifier of the album. Shared primary key with object.
        albumid     INTEGER NOT NULL,
        -- Human-memorizable tag.
        tag         VARCHAR(256) NOT NULL,
        -- Whether it is possible to delete the album.
        deletable   INTEGER NOT NULL,

        UNIQUE      (tag),
        FOREIGN KEY (albumid) REFERENCES object,
        PRIMARY KEY (albumid)
    );

    CREATE TABLE image (
        -- Identifier of the image. Shared primary key with object.
        imageid     INTEGER NOT NULL,
        -- MD5 sum in hex format of the first 4711 bytes of the image.
        hash        CHAR(32) NOT NULL,
        -- Last known location (local pathname) of the image.
        location    VARCHAR(256) NOT NULL,

        UNIQUE      (hash),
        FOREIGN KEY (imageid) REFERENCES object,
        PRIMARY KEY (imageid)
    );

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
"""

_ALLIMAGES_ALBUM_ID = -2
_ALLALBUMS_ALBUM_ID = -1
_ROOT_ALBUM_ID = 0
_magic_albums = {
    _ALLIMAGES_ALBUM_ID: "_allimages",
    _ALLALBUMS_ALBUM_ID: "_allalbums",
    _ROOT_ALBUM_ID: "root", # Just the default.
}

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


class ObjectDoesNotExist(KofotoError):
    """Object does not exist in the album."""
    pass


class AlbumDoesNotExist(KofotoError):
    """Album does not exist in the album."""
    pass


class ImageDoesNotExist(KofotoError):
    """Image does not exist in the album."""
    pass


class ReservedAlbumError(KofotoError):
    """The album (tag/ID) is reserved for other internal purposes."""
    pass


class UnimplementedError(KofotoError):
    """Unimplemented action."""
    pass


######################################################################
### Public functions.

def computeImageHash(filename):
    """Compute the canonical image ID for an image file."""
    m = md5.new()
    f = open(filename)
    while 1:
        data = f.read(4711)
        if not data:
            break
        m.update(data)
    return m.hexdigest()


def verifyValidAlbumTag(tag, allowid):
    if not tag or not type(tag) == type("") or tag[0] == "_" or "\0" in tag:
        raise ReservedAlbumError, tag
    if not allowid:
        try:
            int(tag)
        except ValueError:
            pass
        else:
            raise ReservedAlbumError, tag

######################################################################
### Public classes.

class Shelf:
    """A Kofoto shelf."""

    ##############################
    # Public methods.

    def __init__(self, location, create=0):
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
                for id, tag in _magic_albums.items():
                    cursor.execute(
                        " insert into album"
                        " values (%(id)s, %(tag)s, 0)",
                        locals())
                cursor.execute(
                    " insert into member"
                    " values (%s, 0, %s)",
                    _ROOT_ALBUM_ID,
                    _ALLALBUMS_ALBUM_ID)
                cursor.execute(
                    " insert into member"
                    " values (%s, 1, %s)",
                    _ROOT_ALBUM_ID,
                    _ALLIMAGES_ALBUM_ID)
                self.connection.commit()
            else:
                raise ShelfNotFoundError, location


    def begin(self):
        """Begin working with the shelf."""
        # Instantiation of the first cursor starts the transaction in
        # PySQLite, so create one here.
        self.cursor = self.connection.cursor()


    def commit(self):
        """Commit the work on the shelf."""
        self.connection.commit()
        del self.cursor


    def rollback(self):
        """Abort the work on the shelf.

        The changes (if any) will not be saved."""
        self.connection.rollback()
        del self.cursor


    def createAlbum(self, tag):
        """Create an empty, unlinked album."""
        verifyValidAlbumTag(tag, allowid=0)
        try:
            self.cursor.execute(
                " insert into object"
                " values (null)",
                locals())
            self.cursor.execute(
                " insert into album"
                " values (last_insert_rowid(), %(tag)s, 1)",
                locals())
        except sql.IntegrityError:
            raise AlbumExistsError, tag


    def getAlbum(self, tag):
        """Get the album for a given album tag/ID.

        Returns an Album instance.
        """
        if tag == _magic_albums[_ALLALBUMS_ALBUM_ID]:
            return self.getAllAlbumsAlbum()
        elif tag == _magic_albums[_ALLIMAGES_ALBUM_ID]:
            return self.getAllImagesAlbum()
        try:
            albumid = int(tag)
        except ValueError:
            self.cursor.execute(
                " select albumid"
                " from album"
                " where tag = %(tag)s",
                locals())
            if self.cursor.rowcount > 0:
                albumid = self.cursor.fetchone()[0]
            else:
                raise AlbumDoesNotExist, tag
        return Album(self, albumid)


    def getRootAlbum(self):
        """Get the root album.

        Returns an Album object.
        """
        return Album(self, 0)


    def getAllAlbumsAlbum(self):
        """Get the magic \"all albums\" album."""
        return AllAlbumsAlbum(self, _ALLALBUMS_ALBUM_ID)


    def getAllImagesAlbum(self):
        """Get the magic \"all images\" album."""
        return AllImagesAlbum(self, _ALLIMAGES_ALBUM_ID)


    def deleteAlbum(self, tag):
        verifyValidAlbumTag(tag, allowid=1)
        try:
            albumid = int(tag)
        except ValueError:
            self.cursor.execute(
                " select albumid"
                " from album"
                " where tag = %(tag)s",
                locals())
            row = self.cursor.fetchone()
            if not row:
                raise AlbumDoesNotExist, tag
            albumid = row[0]
        if albumid == _ROOT_ALBUM_ID:
            # Don't delete the root album!
            raise ReservedAlbumError, tag
        self.cursor.execute(
            " select albumid"
            " from member"
            " where objectid = %(albumid)s",
            locals())
        parents = [x[0] for x in self.cursor.fetchall()]
        for parentid in parents:
            self.cursor.execute(
                " select position"
                " from   member"
                " where  albumid = %(parentid)s and"
                "        objectid = %(delid)s",
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
                    " where  position > %(position)s",
                    locals())
        self.cursor.execute(
            " delete from album"
            " where  albumid = %(delid)s",
            locals())
        self.cursor.execute(
            " delete from attribute"
            " where  objectid = %(delid)s",
            locals())


    def createImage(self, filename):
        """Add a new, unlinked image to the shelf.

        The ID of the image is returned."""
        imageid = computeImageHash(filename)
        try:
            self.cursor.execute(
                " insert into object"
                " values (null)",
                locals())
            self.cursor.execute(
                " insert into image"
                " values (last_insert_rowid(), %(imageid)s, %(location)s)",
                locals())
        except sql.IntegrityError:
            raise ImageExistsError, tag


    def getImage(self, hash):
        """Get the image for a given image hash/ID.

        Returns an Image object.
        """
        try:
            imageid = int(hash)
        except ValueError:
            self.cursor.execute(
                " select imageid"
                " from   image"
                " where  hash = %(hash)s",
                locals())
            if self.cursor.rowcount > 0:
                imageid = self.cursor.fetchone()[0]
            else:
                raise ImageDoesNotExist, hash
        return Image(self, imageid)


    ##############################
    # Internal methods.

class _Object:
    def __init__(self, shelf, objid):
        self.shelf = shelf
        self.objid = objid


    def getId(self):
        return self.objid


    def getAttributeNames(self):
        """Returns a (unsorted) list of available attributes."""
        objid = self.objid
        self.shelf.cursor.execute(
            " select name"
            " from   attribute"
            " where  objectid = %(objid)s",
            locals())
        return [x[0] for x in self.shelf.cursor.fetchall()]


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
                " insert attribute"
                " set    value = %(value)s"
                " where  objectid = %(objid)s and"
                "        name = %(name)s",
            locals())


    def deleteAttribute(self, name):
        """Delete an attribute."""
        objid = self.objid
        self.shelf.cursor.execute(
            " delete from attribute"
            " where  objectid = %(objid)s and"
            "        name = %(name)s",
            locals())


class Album(_Object):
    """A Kofoto album."""

    ##############################
    # Public methods.

    def getChildren(self):
        """Get the album's children.

        Returns a list of Albums and Images.
        """
        albumid = self.getId()
        self.shelf.cursor.execute(
            " select 'album', position, member.objectid"
            " from   member, album"
            " where  member.albumid = %(albumid)s and"
            "        member.objectid = album.albumid"
            " union"
            " select 'image', position, member.objectid"
            " from   member, image"
            " where  member.albumid = %(albumid)s and"
            "        member.objectid = image.imageid"
            " order by position",
            locals())
        objects = []
        for objtype, position, objid in self.shelf.cursor.fetchall():
            if objtype == "album":
                if objid == _ALLALBUMS_ALBUM_ID:
                    childtype = AllAlbumsAlbum
                elif objid == _ALLIMAGES_ALBUM_ID:
                    childtype = AllImagesAlbum
                else:
                    childtype = Album
            else:
                childtype = Image
            objects.append(childtype(self.shelf, objid))
        return objects


    def setChildren(self, children):
        """Set an album's children."""
        albumid = self.getId()
        self.shelf.cursor.execute(
            "-- types int")
        self.shelf.cursor.execute(
            " select max(position)"
            " from   member"
            " where  albumid = %(albumid)s",
            locals())
        oldchcnt = self.shelf.fetchone()[0]
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
                    " values (%(albumid)s, %(position)s, %(childid)s",
                    locals())
        self.shelf.cursor.execute(
            " delete from member"
            " where  albumid = %(albumid)s and"
            "        position >= %(newchcnt)s",
            locals())


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
        verifyAlbumTag(newtag, allowid=0)
        albumid = self.getId()
        self.shelf.cursor.execute(
            " update album"
            " set    tag = %(newtag)s"
            " where  albumid = %(albumid)s",
            locals())


    ##############################
    # Internal methods.

    def __init__(self, shelf, albumid):
        """Constructor of an Album."""
        _Object.__init__(self, shelf, albumid)
        self.shelf = shelf


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


    ##############################
    # Internal methods.

    def __init__(self, shelf, imageid):
        """Constructor of an Image."""
        _Object.__init__(self, shelf, imageid)
        self.shelf = shelf
        self.imageid = imageid
        self.attributeMap = {}
        self.children = []


# Magic albums have the following public methods:
#
# getChildren()
# getId()
# getTag()

class AllAlbumsAlbum:
    """A magic \"all albums\" album."""

    ##############################
    # Public methods.

    def getChildren(self):
        """Get the album's children.

        Returns a list of all albums.
        """
        objects = []
        self.shelf.cursor.execute(
            " select   albumid"
            " from     album"
            " order by tag")
        for (objid,) in self.shelf.cursor.fetchall():
            objects.append(Album(self.shelf, objid))
        return objects


    def getId(self):
        return _ALLALBUMS_ALBUM_ID


    def getTag(self):
        return _magic_albums[_ALLALBUMS_ALBUM_ID]


    def setTag(self, tag):
        raise ReservedAlbumError, _magic_albums[_ALLALBUMS_ALBUM_ID]


    ##############################
    # Internal methods.

    def __init__(self, shelf, albumid):
        assert albumid == _ALLALBUMS_ALBUM_ID
        self.shelf = shelf


class AllImagesAlbum:
    """A magic \"all images\" album."""

    ##############################
    # Public methods.

    def getChildren(self):
        """Get the album's children.

        Returns a list of all images.
        """
        objects = []
        self.shelf.cursor.execute(
            " select   imageid"
            " from     image left join attribute"
            " on       imageid = objectid"
            " where    name = 'timestamp'"
            " order by value")
        for (objid,) in self.shelf.cursor.fetchall():
            objects.append(Image(self.shelf, objid))
        return objects


    def getId(self):
        return _ALLIMAGES_ALBUM_ID


    def getTag(self):
        return _magic_albums[_ALLIMAGES_ALBUM_ID]


    def setTag(self, tag):
        raise ReservedAlbumError, _magic_albums[_ALLIMAGES_ALBUM_ID]


    ##############################
    # Internal methods.

    def __init__(self, shelf, albumid):
        assert albumid == _ALLIMAGES_ALBUM_ID
        self.shelf = shelf

######################################################################
# Internal functions.

def _latin1(unicodeString):
    """Converts a Unicode string to Latin1."""
    return unicodeString.encode("latin1")
