__all__ = ["ImageCache"]

import os
import Image as PILImage
import sets
from kofoto.cachedir import CacheDir
from kofoto.common import symlinkOrCopyFile

class ImageCache:
    def __init__(self, cachelocation, useOrientation=False):
        """Constructor.

        cachelocation specifies the image cache directory. If
        useOrientation is true, the image will be rotated according to
        the orientation attribute.
        """
        self.cachedir = CacheDir(cachelocation)
        self.useOrientation = useOrientation


    def get(self, image, widthlimit, heightlimit):
        """Get a file path to a cached image.

        If the original image doesn't fit within the limits, a smaller
        version of the image will be created and its path returned. If
        the original image fits within the limits, a path to a copy of
        the original image will be returned.
        """
        # Scale image to fit within limits.
        imgwidth, imgheight, w, h, orientation = self._calcImageSize(
            image, widthlimit, heightlimit)

        # Check whether a cached version already exists.
        path = self.cachedir.getFilepath(
            self._getCacheImageName(image, w, h))
        if os.path.exists(path):
            return path

        # No version of the wanted size existed in the cache. Create
        # one.
        pilimg = PILImage.open(image.getLocation())
        if not pilimg.mode in ("L", "RGB", "CMYK"):
            pilimg = pilimg.convert("RGB")
        if imgwidth > widthlimit or imgheight > heightlimit:
            if self.useOrientation and orientation in ("left", "right"):
                coord = h, w
            else:
                coord = w, h
            pilimg.thumbnail(coord, PILImage.ANTIALIAS)
        if self.useOrientation:
            if orientation == "right":
                pilimg = pilimg.rotate(90)
            elif orientation == "down":
                pilimg = pilimg.rotate(180)
            elif orientation == "left":
                pilimg = pilimg.rotate(270)
        pilimg.save(path, "JPEG")
        return path


    def cleanup(self, imagesToKeep, sizelimits):
        keep = sets.Set()
        for image in imagesToKeep:
            for heightlimit, widthlimit in sizelimits:
                junk1, junk2, w, h, junk3 = self._calcImageSize(
                    image, heightlimit, widthlimit)
                keep.add(self._getCacheImageName(image, w, h))
        for filename in self.cachedir.getAllFilenames():
            if not os.path.basename(filename) in keep:
                os.unlink(filename)
        self.cachedir.cleanup()


    def _calcImageSize(self, image, widthlimit, heightlimit):
        imgwidth = int(image.getAttribute(u"width"))
        imgheight = int(image.getAttribute(u"height"))
        if self.useOrientation:
            orientation = image.getAttribute(u"orientation")
            if orientation in ("left", "right"):
                imgwidth, imgheight = imgheight, imgwidth
        else:
            orientation = "up"
        w = imgwidth
        h = imgheight
        if w > widthlimit:
            h = widthlimit * h // w
            w = widthlimit
        if h > heightlimit:
            w = heightlimit * w // h
            h = heightlimit
        return imgwidth, imgheight, w, h, orientation


    def _getCacheImageName(self, image, width, height):
        if self.useOrientation:
            orientation = str(image.getAttribute(u"orientation"))
            if orientation not in ("up", "down", "left", "right"):
                orientation = "up"
        else:
            orientation = "up"
        genname = "%s-%dx%d-%s.jpg" % (
            str(image.getHash()),
            width,
            height,
            orientation)
        return genname
