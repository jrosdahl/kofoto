import os
import Image as PILImage
from kofoto.cachedir import CacheDir
from kofoto.common import symlinkOrCopyFile

class ImageCache:
    def __init__(self, cachelocation):
        self.cachedir = CacheDir(cachelocation)


    def get(self, image, limit):
        origpath = image.getLocation()
        orientation = image.getAttribute(u"orientation")
        genname = self._getCacheImageName(image, limit)
        genpath = self.cachedir.getFilepath(genname)

        if os.path.exists(genpath):
            return genpath

        height = int(image.getAttribute(u"height"))
        width = int(image.getAttribute(u"width"))
        largest = max(height, width)
        if limit > largest:
            largestpath = self.cachedir.getFilepath(
                self._getCacheImageName(image, largest))
            if os.path.isfile(largestpath):
                return largestpath

        pilimg = PILImage.open(origpath)
        savepath = genpath
        if not pilimg.mode in ("L", "RGB", "CMYK"):
            pilimg = pilimg.convert("RGB")
        if limit < largest:
            pilimg.thumbnail((limit, limit), PILImage.ANTIALIAS)
        elif limit > largest:
            savepath = largestpath

        if orientation == "right":
            pilimg = pilimg.rotate(90)
        elif orientation == "down":
            pilimg = pilimg.rotate(180)
        elif orientation == "left":
            pilimg = pilimg.rotate(270)

        if not pilimg.mode in ("L", "RGB", "CMYK"):
            pilimg = pilimg.convert("RGB")
        pilimg.save(savepath, "JPEG")
        return savepath


    def cleanup(self, imagesToKeep, sizes):
        keep = {}
        for image in imagesToKeep:
            maxsize = max(int(image.getAttribute(u"height")),
                          int(image.getAttribute(u"width")))
            for size in sizes + [maxsize]:
                keep[self._getCacheImageName(image, size)] = True
        for filename in self.cachedir.getAllFilenames():
            if not keep.has_key(os.path.basename(filename)):
                os.unlink(filename)
        self.cachedir.cleanup()


    def _getCacheImageName(self, image, limit):
        orientation = image.getAttribute(u"orientation")
        if orientation not in ("up", "down", "left", "right"):
            orientation = "up"
        genname = "%s-%s-%s.jpg" % (str(image.getHash()),
                                    limit,
                                    str(orientation))
        return genname
