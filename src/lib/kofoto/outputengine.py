__all__ = ["OutputEngine"]

import os
import time
from sets import Set
from kofoto.cachedir import CacheDir
from kofoto.common import symlinkOrCopyFile

class OutputEngine:
    def __init__(self, env):
        self.env = env
        self.blurb = 'Generated by <a href="http://svn.rosdahl.net/kofoto/kofoto/" target="_top">Kofoto</a> %s.' % time.strftime("%Y-%m-%d %H:%M:%S")


    def getImageReference(self, image, size):
        key = (image.getHash(), size)
        if not self.imgref.has_key(key):
            if self.env.verbose:
                self.env.out("Generating image %d, size %d..." % (
                    image.getId(), size))
            imgabsloc = self.env.imagecache.get(image, size)
            imgloc = self.imagesdest.getFilepath(os.path.basename(imgabsloc))
            if not os.path.isfile(imgloc):
                symlinkOrCopyFile(imgabsloc, imgloc)
            self.imgref[key] = "/".join(imgloc.split(os.sep)[-4:])
            if self.env.verbose:
                self.env.out("\n")
        return self.imgref[key]


    def writeFile(self, filename, text, binary=False):
        if binary:
            mode = "wb"
        else:
            mode = "w"
        file(os.path.join(self.dest, filename), mode).write(text)


    def symlinkFile(self, source, destination):
        symlinkOrCopyFile(source, os.path.join(self.dest, destination))


    def makeDirectory(self, dir):
        absdir = os.path.join(self.dest, dir)
        if not os.path.isdir(absdir):
            os.mkdir(absdir)


    def generate(self, root, subalbums, dest):
        self.dest = dest.encode(self.env.codeset)
        try:
            os.mkdir(self.dest)
        except OSError:
            pass
        self.imagesdest = CacheDir(os.path.join(self.dest, "@images"))
        self.imgref = {}

        albummap = _findAlbumPaths(root)

        albumsToGenerate = Set()
        if subalbums:
            albumsToGenerate |= Set(subalbums)
            for subalbum in subalbums:
                albumsToGenerate |= Set(subalbum.getAlbumParents())
        else:
            albumsToGenerate |= Set(albummap.keys())

        self.preGeneration(root)
        for album, paths in albummap.items():
            if album in albumsToGenerate:
                self._generateAlbumHelper(album, paths)
        self.postGeneration(root)


    def getLimitedSize(self, image, limit):
        width = int(image.getAttribute(u"width"))
        height = int(image.getAttribute(u"height"))
        orientation = image.getAttribute(u"orientation")
        if orientation in ["left", "right"]:
            width, height = height, width
        largest = max(height, width)
        if limit < largest:
           if width > height:
               return limit, (limit * height) / width
           else:
               return (limit * width) / height, limit
        else:
            return width, height


    def _generateAlbumHelper(self, album, paths):
        if self.env.verbose:
            self.env.out("Generating album page for %s...\n" %
                         album.getTag().encode(self.env.codeset))

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
                    "Generating image page for image %d in album %s...\n" % (
                        child.getId(),
                        album.getTag().encode(self.env.codeset)))
            self.generateImage(album, child, imagechildren, ix, paths)


######################################################################

def _findAlbumPaths(startalbum):
    """Traverse all albums reachable from a given album and find
    possible paths to the albums.

    Start recursing at startalbum. The return value is a mapping each
    key is an Album instance and the associated value is a list of
    paths, where a path is a list of Album instances."""
    def helper(album, path):
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
