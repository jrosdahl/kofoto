import os
import Image as PILImage
from kofoto.common import symlinkOrCopyFile

class ImageCache:
    def __init__(self, cachelocation):
        self.cachelocation = cachelocation
        if not os.path.isdir(cachelocation):
            os.mkdir(cachelocation)


    def get(self, image, limit):
        origpath = image.getLocation()
        orientation = image.getAttribute("orientation")
        genname = self._getCacheImageName(image, limit)
        genpath = os.path.join(self.cachelocation, genname)

        if os.path.exists(genpath):
            return genpath

        height = int(image.getAttribute("height"))
        width = int(image.getAttribute("width"))
        largest = max(height, width)
        if limit > largest:
            largestpath = os.path.join(
                self.cachelocation,
                self._getCacheImageName(image, largest))
            if os.path.isfile(largestpath):
                return largestpath

        pilimg = PILImage.open(origpath)
        savepath = genpath
        if limit < largest:
            if width > height:
                size = limit, (limit * height) / width
            else:
                size = (limit * width) / height, limit
            pilimg = pilimg.resize(size)
        elif limit > largest:
            savepath = largestpath

        if orientation == "right":
            pilimg = pilimg.rotate(90)
        elif orientation == "down":
            pilimg = pilimg.rotate(180)
        elif orientation == "left":
            pilimg = pilimg.rotate(270)
        pilimg.save(savepath)
        return savepath


    def cleanup(self, imagesToKeep, sizes):
        keep = {}
        for image in imagesToKeep:
            maxsize = max(int(image.getAttribute("height")),
                          int(image.getAttribute("width")))
            for size in sizes + [maxsize]:
                keep[self._getCacheImageName(image, size)] = 1
        for file in os.listdir(self.cachelocation):
            if not keep.has_key(file):
                os.unlink(os.path.join(self.cachelocation, file))


    def _getCacheImageName(self, image, limit):
        extension = image.getLocation().split(".")[-1]
        orientation = image.getAttribute("orientation")
        if orientation not in ("up", "down", "left", "right"):
            orientation = "up"
        genname = "%s-%s-%s.%s" % (image.getHash(), limit,
                                   orientation, extension)
        return genname
