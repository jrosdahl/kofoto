import os
import time
from kofoto.common import symlinkOrCopyFile

class OutputEngine:
    def __init__(self, env):
        self.env = env
        self.imagesdest = "images"
        self.blurb = 'Generated by <a href="http://svn.rosdahl.net/svn/kofoto/" target="_top">Kofoto</a> %s.' % time.strftime("%Y-%m-%d %H:%M:%S")


    def getImageReference(self, image, size):
        return self.imgref[(image.getHash(), size)]


    def writeFile(self, filename, text, binary=False):
        if binary:
            mode = "wb"
        else:
            mode = "w"
        file(os.path.join(self.dest, filename), mode).write(text)


    def symlinkFile(self, source, destination):
        symlinkOrCopyFile(source, os.path.join(self.dest, destination))


    def generate(self, root, dest):
        self.dest = dest
        self.imgref = {}

        try:
            os.mkdir(self.dest)
        except OSError:
            pass
        try:
            os.mkdir(os.path.join(self.dest, self.imagesdest))
        except OSError:
            pass

        albummap = {}
        _findAlbumPaths(root, [], albummap)
        for tag, paths in albummap.items():
            self._calculateImageReferences(self.env.shelf.getAlbum(tag))
        for tag, paths in albummap.items():
            self._generateAlbumHelper(self.env.shelf.getAlbum(tag), paths)
        if self.env.verbose:
            self.env.out("Generating index page...\n")
        self.generateIndex(root)


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


    def _calculateImageReferences(self, album):
        #
        # Generate and remember different sizes for images in the album.
        #
        imagechildren = [x for x in album.getChildren() if not x.isAlbum()]
        for child in imagechildren:
            if self.env.verbose:
                self.env.out("Generating image %d..." % child.getId())
            for size in [self.env.thumbnailsize] + self.env.imagesizes:
                if self.env.verbose:
                    self.env.out(" %s" % size)
                imgabsloc = self.env.imagecache.get(child, size)
                imgloc = os.path.join(
                    self.dest,
                    self.imagesdest,
                    os.path.basename(imgabsloc))
                if not os.path.isfile(imgloc):
                    symlinkOrCopyFile(imgabsloc, imgloc)
                self.imgref[(child.getHash(), size)] = "%s/%s" % (
                    self.imagesdest,
                    os.path.basename(imgabsloc))
            if self.env.verbose:
                self.env.out("\n")


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

def _findAlbumPaths(album, path, albummap):
    if album.getTag() in [x.getTag() for x in path]:
        # Already visited album, so break recursion here.
        return
    path = path[:] + [album]
    tag = album.getTag()
    if not albummap.has_key(tag):
        albummap[tag] = []
    albummap[tag].append(path)
    for child in album.getChildren():
        if child.isAlbum():
            _findAlbumPaths(child, path, albummap)
