"""Interface to a Kofoto shelf."""

######################################################################
### Libraries.

import sqlite as sql
from kofoto.common import KofotoError

import warnings
warnings.filterwarnings("ignore", "DB-API extension")

######################################################################
### Database schema.

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
        -- Album type (plain, orphans, allalbums, ...).
        type        VARCHAR(256) NOT NULL,

        UNIQUE      (tag),
        FOREIGN KEY (albumid) REFERENCES object,
        PRIMARY KEY (albumid)
    );

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


class UnimplementedError(KofotoError):
    """Unimplemented action."""
    pass


######################################################################
### Public functions.

def computeImageHash(filename):
    """Compute the canonical image ID for an image file."""
    import md5
    m = md5.new()
    f = open(filename, "rb")
    while 1:
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
        self.cursor.execute(
            " select albumid, type"
            " from   album")
        albums = []
        for albumid, albumtype in self.cursor.fetchall():
            albums.append(self._albumFactory(albumid, albumtype))
        return albums


    def getAllImages(self):
        self.cursor.execute(
            " select imageid"
            " from   image")
        images = []
        for (imageid,) in self.cursor.fetchall():
            images.append(Image(self, imageid))
        return images


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
        """Returns a map of available attributes."""
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
        """Returns a sorted list of available attributes."""
        objid = self.objid
        self.shelf.cursor.execute(
            " select name"
            " from   attribute"
            " where  objectid = %(objid)s"
            " order by name",
            locals())
        return [x[0] for x in self.shelf.cursor.fetchall()]


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
        return 1


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

        Returns a list of Albums and Images.
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
        objects = []
        for objtype, position, objid, atype in self.shelf.cursor.fetchall():
            if objtype == "album":
                child = self.shelf._albumFactory(objid, atype)
            else:
                child = Image(self.shelf, objid)
            objects.append(child)
        return objects


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
        return 0


    def importExifTags(self):
        """Read known EXIF tags and add them as attributes."""
        import EXIF
        tags = EXIF.process_file(open(self.getLocation(), "rb"))

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

        Returns a list of all albums.
        """
        objects = []
        self.shelf.cursor.execute(
            " select   albumid, type"
            " from     album"
            " order by tag")
        for (objid, albumtype) in self.shelf.cursor.fetchall():
            objects.append(self.shelf._albumFactory(objid, albumtype))
        return objects


class AllImagesAlbum(MagicAlbum):
    """An album with all images, sorted by timestamp."""

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
            " order by value, location")
        for (objid,) in self.shelf.cursor.fetchall():
            objects.append(Image(self.shelf, objid))
        return objects


class OrphansAlbum(MagicAlbum):
    """An album with all albums and images that are orphans."""

    ##############################
    # Public methods.

    def getChildren(self):
        """Get the album's children.

        Returns a list of all images.
        """
        rootid = _ROOT_ALBUM_ID
        albums = []
        self.shelf.cursor.execute(
            " select   albumid, type"
            " from     album"
            " where    albumid not in (select objectid from member) and"
            "          albumid != %(rootid)s"
            " order by tag",
            locals())
        for albumid, albumtype in self.shelf.cursor.fetchall():
            albums.append(self.shelf._albumFactory(albumid, albumtype))
        images = []
        self.shelf.cursor.execute(
            " select   imageid"
            " from     image left join attribute"
            " on       imageid = objectid"
            " where    imageid not in (select objectid from member) and"
            "          name = 'timestamp'"
            " order by value, location")
        for (imageid,) in self.shelf.cursor.fetchall():
            images.append(Image(self.shelf, imageid))
        return albums + images
