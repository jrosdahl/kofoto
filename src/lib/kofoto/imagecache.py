import os
import Image as PILImage

class ImageCache:
    def __init__(self, cachelocation):
        self.cachelocation = cachelocation
        if not os.path.isdir(cachelocation):
            os.mkdir(cachelocation)


    def get(self, image, limit, regenerate=0):
        origpath = image.getLocation()
        genname = self._getCacheImageName(origpath, image.getHash(), limit)
        genpath = os.path.join(self.cachelocation, genname)
        if not os.path.exists(genpath) or regenerate:
            pilimg = PILImage.open(origpath)
            width, height = pilimg.size
            largest = max(width, height)
            if limit < largest:
                if width > height:
                    size = limit, (limit * height) / width
                else:
                    size = (limit * width) / height, limit
                pilimg = pilimg.resize(size)
            elif limit > largest:
                largestpath = os.path.join(
                    self.cachelocation,
                    self._getCacheImageName(origpath, image.getHash(), largest))
                if os.path.isfile(largestpath):
                    try:
                        os.symlink(largestpath, genpath)
                    except AttributeError:
                        import shutil
                        shutil.copy(largestpath, genpath)
                    return genpath
            orientation = image.getAttribute("orientation")
            if orientation:
                if orientation == "right":
                    pilimg = pilimg.rotate(90)
                elif orientation == "down":
                    pilimg = pilimg.rotate(180)
                elif orientation == "left":
                    pilimg = pilimg.rotate(270)
            pilimg.save(genpath)
        return genpath


    def cleanup(self, imagesToKeep, sizes):
        keep = {}
        for image in imagesToKeep:
            for size in sizes:
                keep[self._getCacheImageName(image.getLocation(),
                                             image.getHash(),
                                             size)] = 1
        for file in os.listdir(self.cachelocation):
            if not keep.has_key(file):
                os.unlink(os.path.join(self.cachelocation, file))


    def _getCacheImageName(self, origpath, hash, limit):
        extension = origpath.split(".")[-1]
        genname = "%s-%s.%s" % (hash, limit, extension)
        return genname
