"""Interface to a Kofoto shelf."""

######################################################################
### Libraries

import fcntl
import md5
import os
import shutil
import time
from xml.dom.minidom import parse as parseXmlFile
from kofoto.common import KofotoError


######################################################################
### Exceptions.

class FailedWritingError(KofotoError):
    """Kofoto shelf file already exists."""
    pass


class ShelfNotFoundError(KofotoError):
    """Kofoto shelf file not found."""
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


class NameExistsError(KofotoError):
    """Name already exists in the album."""
    pass


class ReservedAlbumIdError(KofotoError):
    """The album ID is reserved for other internal purposes."""
    pass


######################################################################
### Public functions.

def computeImageId(filename):
    """Compute the canonical image ID for an image file."""
    m = md5.new()
    f = open(filename)
    while 1:
        data = f.read(2**16)
        if not data:
            break
        m.update(data)
    return m.hexdigest()


def createNewShelfFile(filename):
    """Create a new Kofoto shelf file.

    The file is written to FILENAME.  If the file could not be written
    (e.g. already exists), FailedWritingError will be raised.
    """
    try:
        fd = os.open(filename, os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0666)
        f = os.fdopen(fd, "w")
        f.write("""<?xml version="1.0" encoding="iso-8859-1"?>
<kofotoshelf>
  <images>
  </images>
  <albums>
    <album id=\"_root\">
      <description>Root album.</description>
      <albumref id=\"_unlinked\" name=\"Unlinked\"/>
    </album>
  </albums>
</kofotoshelf>
""")
        f.close()
    except OSError:
        raise FailedWritingError, filename


######################################################################
### Public classes.

class Shelf:
    """A Kofoto shelf."""

    ##############################
    # Public methods.

    def __init__(self, filename):
        """Constructor."""
        self.filename = filename


    def beginFiddling(self):
        """Begin fiddling with the database.

        This method locks the database and reads it into memory.  If
        the database is not found, ShelfNotFoundError is raised.
        """
        self.albumMap = {}
        self.imageMap = {}
        unlinkedImages = {}
        unlinkedAlbums = {}

        # Magical albums.
        self.albumMap["_unlinked"] = Album(self, "_unlinked", magical=1)

        try:
            self.lockfd = os.open(self.filename, os.O_WRONLY)
        except IOError:
            raise ShelfNotFoundError, self.filename
        fcntl.lockf(self.lockfd, fcntl.LOCK_EX)

        documentElement = parseXmlFile(self.filename)
        shelfTag = documentElement.childNodes[0]
        for node in shelfTag.childNodes:
            if node.nodeType != node.ELEMENT_NODE:
                pass
            elif node.nodeName == "images":
                for imageElement in _xmlElements(node.childNodes):
                    imageId = _latin1(imageElement.getAttribute("id"))
                    if self.imageMap.has_key(imageId):
                        raise ImageExistsError, imageId
                    image = Image(self, imageId)
                    unlinkedImages[imageId] = 1
                    for attrElement in _xmlElements(imageElement.childNodes):
                        elementName = _latin1(attrElement.nodeName)
                        newAttribute = _latin1(attrElement.childNodes[0].data)
                        attrs = image.getAttributes(elementName)
                        attrs.append(newAttribute)
                        image.setAttributes(elementName, attrs)
                    self.imageMap[imageId] = image
            elif node.nodeName == "albums":
                # Go through the album list twice to allow references
                # to albums that have not yet been read.

                for albumElement in _xmlElements(node.childNodes):
                    albumId = _latin1(albumElement.getAttribute("id"))
                    album = Album(self, albumId)
                    if self.albumMap.has_key(albumId):
                        raise AlbumExistsError, albumId
                    self.albumMap[albumId] = album
                    unlinkedAlbums[albumId] = 1

                for albumElement in _xmlElements(node.childNodes):
                    albumId = _latin1(albumElement.getAttribute("id"))
                    album = self.albumMap[albumId]

                    for attrElement in _xmlElements(albumElement.childNodes):
                        elementName = _latin1(attrElement.nodeName)
                        if elementName == "imageref":
                            imgName = _latin1(attrElement.getAttribute("name"))
                            imgId = _latin1(attrElement.getAttribute("id"))
                            album.addChild(imgName, self.imageMap[imgId])
                            if unlinkedImages.has_key(imgId):
                                del unlinkedImages[imgId]
                        elif elementName == "albumref":
                            albName = _latin1(attrElement.getAttribute("name"))
                            albId = _latin1(attrElement.getAttribute("id"))
                            album.addChild(albName, self.albumMap[albId])
                            if unlinkedAlbums.has_key(albId):
                                del unlinkedAlbums[albId]
                        else:
                            newAttribute = _latin1(
                                attrElement.childNodes[0].data)
                            attrs = album.getAttributes(elementName)
                            attrs.append(newAttribute)
                            album.setAttributes(elementName, attrs)

        rootChildren = self.getRootAlbum().getChildren()

        theUnlinkedAlbum = self.getAlbum("_unlinked")
        for albumId in unlinkedAlbums.keys():
            if albumId[0] != "_":
                theUnlinkedAlbum.addChild(albumId, self.getAlbum(albumId))
        for imageId in unlinkedImages.keys():
            theUnlinkedAlbum.addChild(imageId, self.getImage(imageId))

        documentElement.unlink()  # Clean up XML tree.
        self.dirty = 0


    def abortFiddling(self):
        """Abort fiddling with the database.

        This method unlocks the database without saving.
        """
        del self.albumMap
        del self.imageMap
        os.close(self.lockfd)  # Also releases the lock.


    def endFiddling(self):
        """End fiddling with the database.

        The database fiddling will be saved if necessary.
        """
        if self.dirty:
            self.saveFiddling()
        else:
            self.abortFiddling()


    def getRootAlbum(self):
        """Get the root album.

        Returns an Album object.
        """
        return self.albumMap["_root"]


    def createAlbum(self, albumId):
        """Create an empty, unlinked album."""
        self.verifyAlbumId(albumId)
        if self.getAlbum(albumId):
            raise AlbumExistsError, albumId
        else:
            self.setDirty()
            self.albumMap[albumId] = Album(self, albumId)


    def getAlbum(self, albumId):
        """Get the album for a given album ID.

        Returns an Image object, or None if no album found.
        """
        return self.albumMap.get(albumId)


    def getAllAlbums(self):
        """Get a list of all albums."""
        return self.albumMap.values()


    def renameAlbumId(self, oldAlbumId, newAlbumId):
        self.verifyAlbumId(newAlbumId)
        if self.getAlbum(newAlbumId):
            raise AlbumExistsError, newAlbumId
        else:
            self.setDirty()
            alb = self.albumMap[oldAlbumId]
            del self.albumMap[oldAlbumId]
            self.albumMap[newAlbumId] = alb


    def createImage(self, filename):
        """Add a new, unlinked image to the shelf.

        The ID of the image is returned."""
        imageId = computeImageId(filename)
        if self.getImage(imageId):
            raise ImageExistsError, imageId
        else:
            self.setDirty()
            self.imageMap[imageId] = Image(self, imageId)
            return imageId


    def getImage(self, imageId):
        """Get the image for a given image ID.

        Returns an Image object, or None if no image found.
        """
        return self.imageMap.get(imageId)


    def getAllImages(self):
        """Get a list of all images."""
        return self.imageMap.values()


    ##############################
    # Internal methods.

    def setDirty(self):
        """Called by albums and images when saving the database has
        become necessary."""

        self.dirty = 1


    def saveFiddling(self):
        """This method commits the changes and unlocks the database."""

        backupname = self.filename + time.strftime("-%Y-%m-%d-%H:%M:%S")
        shutil.copy2(self.filename, backupname)
        f = os.fdopen(self.lockfd, "w")
        f.truncate(0)

        #
        # Header.
        #
        f.write("<?xml version=\"1.0\" encoding=\"iso-8859-1\"?>\n"
                "<kofotoshelf>\n")

        #
        # Images.
        #
        f.write("  <images>\n")
        for imageId, image in self.imageMap.items():
            f.write("    <image id=\"%s\">\n" % imageId)
            names = image.getAttributeNames()
            names.sort()
            for name in names:
                values = image.getAttributes(name)
                if name == "timestamp":
                    for value in values:
                        f.write("      <%s>%s</%s> <!-- %s -->\n" % (
                            name,
                            value,
                            name,
                            time.ctime(int(value))))
                else:
                    for value in values:
                        f.write("      <%s>%s</%s>\n" % (name, value, name))
            f.write("    </image>\n")
        f.write("  </images>\n")

        #
        # Albums.
        #
        f.write("  <albums>\n")
        for albumId, album in self.albumMap.items():
            if album.isMagical():
                continue

            f.write("    <album id=\"%s\">\n" % albumId)
            names = album.getAttributeNames()
            names.sort()
            for name in names:
                values = album.getAttributes(name)
                for value in values:
                    f.write("      <%s>%s</%s>\n" % (name, value, name))
            for childName, child in album.getChildren():
                if isinstance(child, Image):
                    referenceType = "image"
                else:
                    referenceType = "album"
                f.write("      <%sref id=\"%s\" name=\"%s\"/>\n" % (
                    referenceType,
                    child.getId(),
                    childName))
            f.write("    </album>\n")
        f.write("  </albums>\n")

        #
        # Finished.
        #
        f.write("</kofotoshelf>\n")
        del self.albumMap
        del self.imageMap
        f.close()  # Also releases the lock.


    def verifyAlbumId(self, albumId):
        if albumId[0] == "_":
            raise ReservedAlbumIdError, albumId


class Album:
    """A Kofoto album."""

    ##############################
    # Public methods.

    def getId(self):
        """Get the album ID."""
        return self.albumId


    def setId(self, albumId):
        """Set the album ID."""
        self.albumId = albumId


    def getChildren(self):
        """Get the album's children.

        Returns a list of tuples (name, child) where name is a string
        and child is an Album or Image object.
        """
        return self.children


    def addChild(self, name, child, position=-1):
        """Add a child object.

        NAME (a string) is the name of the object.  CHILD is an Album
        or Image object.  If POSITION is negative, the object is
        placed last.  Otherwise, it is placed before the POSITIONth
        child.
        """
        self.shelf.setDirty()
        if position < 0:
            self.children.append((name, child))
        else:
            self.children.insert(position, (name, child))


    def unlinkChild(self, position):
        """Remove a child at a given position.

        The removed tuple (name, child) is returned."""
        self.shelf.setDirty()
        x = self.children[position]
        del self.children[position]
        return x


    def getAttributes(self, name):
        """Get the attributes with a given name.

        Returns a list of strings.  If there are no matching
        attribute, an empty list is returned.
        """
        return self.attributeMap.get(name, [])


    def setAttributes(self, name, valueList):
        """Set attribute values.

        VALUELIST should be an empty list or a list of strings.  If it
        is an empty list, the attributes are removed.  If it is a list
        of strings, the strings represent the attribute values."""
        self.shelf.setDirty()
        if valueList:
            self.attributeMap[name] = valueList
        elif self.attributeMap.has_key(name):
            del self.attributeMap[name]


    def getAttributeNames(self):
        """Returns a list of available attributes."""
        return self.attributeMap.keys()


    def isMagical(self):
        """Returns true iff the album is magical."""
        return self.magical


    ##############################
    # Internal methods.

    def __init__(self, shelf, albumId, magical=0):
        """Constructor of an Album."""
        self.shelf = shelf
        self.albumId = albumId
        self.attributeMap = {}
        self.children = []
        self.magical = magical


class Image:
    """A Kofoto image."""

    ##############################
    # Public methods.

    def getId(self):
        """Get the image ID."""
        return self.imageId


    def getAttributes(self, name):
        """Get the attributes with a given name.

        Returns a list of strings.  If there are no matching
        attribute, an empty list is returned.
        """
        return self.attributeMap.get(name, [])


    def setAttributes(self, name, valueList):
        """Set attribute values.

        VALUELIST should be an empty list or a list of strings.  If it
        is an empty list, the attributes are removed.  If it is a list
        of strings, the strings represent the attribute values."""
        self.shelf.setDirty()
        if valueList:
            self.attributeMap[name] = valueList
        elif self.attributeMap.has_key(name):
            del self.attributeMap[name]


    def getAttributeNames(self):
        """Returns a list of available attributes."""
        return self.attributeMap.keys()


    ##############################
    # Internal methods.

    def __init__(self, shelf, imageId):
        """Constructor of an Image."""
        self.shelf = shelf
        self.imageId = imageId
        self.attributeMap = {}


######################################################################
# Internal functions.

def _xmlElements(xmlNodes):
    """Returns the XML elements of a list of XML nodes."""
    return [x for x in xmlNodes if x.nodeType == x.ELEMENT_NODE]


def _latin1(unicodeString):
    """Converts a Unicode string to Latin1."""
    return unicodeString.encode("latin1")
