import os
import Image as PILImage
from kofoto.common import symlinkOrCopyFile

class ImageCache:
    def __init__(self, cachelocation):
        self.cachelocation = cachelocation
        if not os.path.isdir(cachelocation):
            os.mkdir(cachelocation)


    def get(self, image, limit, regenerate=0):
        origpath = image.getLocation()
        orientation = image.getAttribute("orientation")
        genname = self._getCacheImageName(
            origpath, image.getHash(), orientation, limit)
        genpath = os.path.join(self.cachelocation, genname)
        if not os.path.exists(genpath) or regenerate:
            pilimg = PILImage.open(origpath)
            width, height = pilimg.size
            largest = max(width, height)
            savepath = genpath

            if limit < largest:
                if width > height:
                    size = limit, (limit * height) / width
                else:
                    size = (limit * width) / height, limit
                pilimg = pilimg.resize(size)
            elif limit > largest:
                largestpath = os.path.join(
                    self.cachelocation,
                    self._getCacheImageName(
                        origpath, image.getHash(), orientation, largest))
                if os.path.isfile(largestpath):
                    symlinkOrCopyFile(largestpath, genpath)
                    return genpath
                else:
                    savepath = largestpath

            if orientation:
                if orientation == "right":
                    pilimg = pilimg.rotate(90)
                elif orientation == "down":
                    pilimg = pilimg.rotate(180)
                elif orientation == "left":
                    pilimg = pilimg.rotate(270)
            pilimg.save(savepath)
            if limit > largest:
                symlinkOrCopyFile(savepath, genpath)
        return genpath


    def cleanup(self, imagesToKeep, sizes):
        keep = {}
        for image in imagesToKeep:
            maxsize = max(int(image.getAttribute("height")),
                          int(image.getAttribute("width")))
            for size in sizes + [maxsize]:
                keep[self._getCacheImageName(image.getLocation(),
                                             image.getHash(),
                                             image.getAttribute("orientation"),
                                             size)] = 1
        for file in os.listdir(self.cachelocation):
            if not keep.has_key(file):
                os.unlink(os.path.join(self.cachelocation, file))


    def _getCacheImageName(self, origpath, hash, orientation, limit):
        extension = origpath.split(".")[-1]
        if orientation not in ("up", "down", "left", "right"):
            orientation = "up"
        genname = "%s-%s-%s.%s" % (hash, limit, orientation, extension)
        return genname
