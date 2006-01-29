"""Implementation of the OutputEngine class."""

__all__ = ["OutputEngine"]

import codecs
import os
import re
import time
from sets import Set
from kofoto.common import symlink_or_copy_file, UnimplementedError

class OutputEngine:
    """An abstract base class for output generators of an album tree."""

    def __init__(self, env):
        self.env = env
        self.blurb = (
            'Generated by <a href="http://kofoto.rosdahl.net"'
            ' target="_top">Kofoto</a> %s.' %
            time.strftime("%Y-%m-%d %H:%M:%S"))
        self.generatedFiles = Set()
        self.__dest = None
        self.__imgrefMap = None


    def preGeneration(self, root):
        """Method called before generation of the output."""
        raise UnimplementedError


    def postGeneration(self, root):
        """Method called after generation of the output."""
        raise UnimplementedError


    def generateAlbum(self, album, subalbums, images, paths):
        """Method called to generate output of an album.

        Arguments:

        album     -- The Album instance.
        subalbums -- Album children of the album.
        images    -- Image children of the album.
        """
        raise UnimplementedError


    def generateImage(self, album, image, images, number, paths):
        """Method called to generate output of an album.

        Arguments:

        album     -- The parent album of the image.
        image     -- The Image instance.
        images    -- A list of images in the album.
        number    -- The current image's index in the image list.
        paths     -- A list of lists of Album instances.
        """
        raise UnimplementedError


    def getImageReference(self, image, widthlimit, heightlimit):
        """Get a href to an image of given limits."""

        def helper(ext):
            """Internal helper function."""
            # Given the image, this function computes and returns a
            # suitable image name and a reference be appended to
            # "@images/<size>/".
            year = "undated"
            captured = image.getAttribute(u"captured")
            if captured:
                m = re.match(u"^(\d{4})-?(\d{0,2})", captured)
                if m:
                    year = m.group(1)
                    month = m.group(2)
                    if month:
                        timestr = captured \
                                  .replace(" ", "_") \
                                  .replace(":", "") \
                                  .replace("-", "")
                        # Also handle time stamps like "2004-11-11 +/- 3 days"
                        filename = "%s%s" % (
                            re.match("^(\w*)", timestr).group(1),
                            ext)
                        return "/".join([year, month, filename])
            filename = "%s%s" % (image.getId(), ext)
            return "/".join([year, filename])

        imageversion = image.getPrimaryVersion()
        if not imageversion:
            # TODO: Handle this in a better way.
            raise Exception("No image versions for image %d" % image.getid())

        key = (imageversion.getHash(), widthlimit, heightlimit)
        if not self.__imgrefMap.has_key(key):
            if self.env.verbose:
                self.env.out("Generating image %d, size limit %dx%d..." % (
                    image.getId(), widthlimit, heightlimit))
            imgabsloc, width, height = self.env.imageCache.get(
                imageversion, widthlimit, heightlimit)
            ext = os.path.splitext(imgabsloc)[1]
            htmlimgloc = os.path.join(
                "@images",
                "%sx%s" % (widthlimit, heightlimit),
                helper(ext))
            # Generate a unique htmlimgloc/imgloc.
            i = 1
            while True:
                if not htmlimgloc in self.generatedFiles:
                    self.generatedFiles.add(htmlimgloc)
                    break
                base, ext = os.path.splitext(htmlimgloc)
                htmlimgloc = re.sub(r"(-\d*)?$", "-%d" % i, base) + ext
                i += 1
            imgloc = os.path.join(self.__dest, htmlimgloc)
            try:
                os.makedirs(os.path.dirname(imgloc))
            except OSError:
                pass
            symlink_or_copy_file(imgabsloc, imgloc)
            self.__imgrefMap[key] = (
                "/".join(htmlimgloc.split(os.sep)),
                width,
                height)
            if self.env.verbose:
                self.env.out("\n")
        return self.__imgrefMap[key]


    def writeFile(self, filename, text, encoding=None, binary=False):
        """Write a text to a file in the generated directory.

        Arguments:

        filename -- A location in the generated directory.
        text     -- The text to write. If binary is true, text must be a
                    byte string (str), otherwise unicode.
        encoding -- How to encode the text. Only used for non-binary text.
        binary   -- Whether the text is to be treated as binary.
        """
        path = os.path.join(self.__dest, filename)
        if binary:
            assert isinstance(text, str)
            f = open(path, "wb")
        else:
            assert isinstance(text, unicode)
            f = codecs.open(path, "w", encoding)
        f.write(text)


    def symlinkFile(self, source, destination):
        """Create a symlink in the generated directory to a file.

        Arguments:

        source      -- A location in the filesystem.
        destination -- A location in the generated directory.
        """
        symlink_or_copy_file(source, os.path.join(self.__dest, destination))


    def makeDirectory(self, directory):
        """Make a directory in the generated directory."""
        absdir = os.path.join(self.__dest, directory)
        if not os.path.isdir(absdir):
            os.mkdir(absdir)


    def generate(self, root, subalbums, dest):
        """Start the engine.

        Arguments:

        root      -- Album to generate.
        subalbums -- If false, generate all descendants of the root. 
                     Otherwise a list of Album instances to generate.
        """

        def addDescendants(albumset, album):
            """Internal helper function."""
            if not album in albumset:
                albumset.add(album)
                for child in album.getAlbumChildren():
                    addDescendants(albumset, child)

        self.__dest = dest
        try:
            os.mkdir(self.__dest)
        except OSError:
            pass
        self.__imgrefMap = {}

        self.env.out("Calculating album paths...\n")
        albummap = _findAlbumPaths(root)

        albumsToGenerate = Set()
        if subalbums:
            for subalbum in subalbums:
                addDescendants(albumsToGenerate, subalbum)
            for subalbum in subalbums:
                albumsToGenerate |= Set(subalbum.getAlbumParents())
        else:
            albumsToGenerate |= Set(albummap.keys())

        self.preGeneration(root)
        i = 1
        items = albummap.items()
        items.sort(lambda x, y: cmp(x[0].getTag(), y[0].getTag()))
        for album, paths in items:
            if album in albumsToGenerate:
                nchildren = len(list(album.getChildren()))
                if nchildren == 1:
                    childrentext = "1 child"
                else:
                    childrentext = "%d children" % nchildren
                self.env.out(u"Creating album %s (%d of %d) with %s...\n" % (
                    album.getTag(),
                    i,
                    len(albumsToGenerate),
                    childrentext))
                i += 1
                self._generateAlbumHelper(album, paths)
        self.postGeneration(root)


    def _generateAlbumHelper(self, album, paths):
        """Internal helper function."""
        if self.env.verbose:
            self.env.out(u"Generating album page for %s...\n" % album.getTag())

        # Design choice: This output engine sorts subalbums before
        # images.
        children = list(album.getChildren())
        albumchildren = [x for x in children if x.isAlbum()]
        imagechildren = [x for x in children if not x.isAlbum()]

        self.generateAlbum(
            album, albumchildren, imagechildren, paths)

        for ix in range(len(imagechildren)):
            child = imagechildren[ix]
            if self.env.verbose:
                self.env.out(
                    u"Generating image page for image %d in album %s...\n" % (
                        child.getId(),
                        album.getTag()))
            self.generateImage(album, child, imagechildren, ix, paths)


######################################################################

def _findAlbumPaths(startalbum):
    """Traverse all albums reachable from a given album and find
    possible paths to the albums.

    The traversal is started at startalbum. The return value is a
    mapping where each key is an Album instance and the associated
    value is a list of paths, where a path is a list of Album
    instances.
    """
    def helper(album, path):
        """Internal helper function."""
        if album in path:
            # Already visited album, so break recursion here.
            return
        path = path[:] + [album]
        if not albummap.has_key(album):
            albummap[album] = []
        albummap[album].append(path)
        for child in album.getChildren():
            if child.isAlbum():
                helper(child, path)
    albummap = {}
    helper(startalbum, [])
    return albummap
