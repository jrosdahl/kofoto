__all__ = ["ImageCache"]

import os
import Image as PILImage
from kofoto.common import calculateDownscaledDimensions, symlinkOrCopyFile

class ImageCache:
    def __init__(self, cacheLocation, useOrientation=False):
        """Constructor.

        cachelocation specifies the image cache directory. If
        useOrientation is true, the image will be rotated according to
        the orientation attribute.
        """
        self.cacheLocation = cacheLocation
        self.useOrientation = useOrientation


    def cleanup(self):
        """Clean up the cache.

        All cached images whose original images no longer exist in the
        filesystem will be removed.
        """

        for dirpath, dirnames, filenames in os.walk(self.cacheLocation,
                                                    topdown=False):
            realdir = dirpath[len(self.cacheLocation):]
            for filename in filenames:
                a = os.path.splitext(filename)[0].split("-")
                if len(a) >= 4:
                    realfilename = "-".join(a[0:-3])
                    mtime = int(a[-1])
                    try:
                        currentmtime = os.path.getmtime(
                            os.path.join(realdir, realfilename))
                        if currentmtime == mtime:
                            # Keep.
                            continue
                    except OSError:
                        pass
                os.unlink(os.path.join(dirpath, filename))
            for dirname in dirnames:
                # Remove directories if they are empty.
                try:
                    os.rmdir(os.path.join(dirpath, dirname))
                except OSError:
                    pass


    def get(self, imageOrLocation, widthlimit, heightlimit):
        """Get a file path to a cached image and the cached image's
        size.

        imageOrLocation could either be an kofoto.shelf.Image instance
        or a location string. If it's a location, the path should
        preferably be normalized (e.g. with os.path.realpath()). If
        the image does not exist at the given location or cannot be
        parsed, OSError is raised.

        If the original image doesn't fit within the limits, a smaller
        version of the image will be created and its path returned. If
        the original image fits within the limits, a path to a copy of
        the original image will be returned.

        Returns a tuple of file path, width and height.
        """
        if isinstance(imageOrLocation, (str, unicode)):
            location = imageOrLocation
            mtime = os.path.getmtime(location)
            width, height = PILImage.open(location).size
            orientation = "up"
        else:
            image = imageOrLocation
            location = image.getLocation()
            mtime = image.getModificationTime()
            width, height = image.getSize()
            if self.useOrientation:
                orientation = image.getAttribute(u"orientation")
                if not orientation:
                    orientation = "up"
            else:
                orientation = "up"
        return self._get(
            location, mtime, width, height, widthlimit, heightlimit,
            orientation)


    def _get(self, location, mtime, width, height, widthlimit,
             heightlimit, orientation):
        # Scale image to fit within limits.
        w, h = calculateDownscaledDimensions(
            width, height, widthlimit, heightlimit)
        if orientation in ["left", "right"]:
            w, h = h, w

        # Check whether a cached version already exists.
        path = self._getCachedImagePath(location, mtime, w, h, orientation)
        if os.path.exists(path):
            return path, w, h

        # No version of the wanted size existed in the cache. Create
        # one.
        directory, filename = os.path.split(path)
        if not os.path.isdir(directory):
            os.makedirs(directory)
        pilimg = PILImage.open(location)
        if not pilimg.mode in ("L", "RGB", "CMYK"):
            pilimg = pilimg.convert("RGB")
        if width > widthlimit or height > heightlimit:
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
        return path, w, h


    def _getCachedImagePath(self, location, mtime, width, height,
                            orientation):
        drive, drivelessPath = os.path.splitdrive(location)
        directory, filename = os.path.split(drivelessPath[1:])
        if drive:
            directory = os.path.join(drive[0], directory)
        genname = "%s-%dx%d-%s-%s.jpg" % (
            filename,
            width,
            height,
            orientation,
            mtime)
        return os.path.join(self.cacheLocation, directory, genname)
