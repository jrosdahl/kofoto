"""Configuration module for Kofoto."""

from ConfigParser import *
import os
import re
from kofoto.common import KofotoError

DEFAULT_CONFIGFILE = os.path.expanduser("~/.kofoto/config")

class ConfigError(KofotoError):
    pass

class MissingConfigurationKeyError(KofotoError):
    pass

class BadConfigurationValueError(KofotoError):
    pass

class Config(ConfigParser):
    def __init__(self, filename):
        ConfigParser.__init__(self)
        self.filename = filename

    def read(self):
        ConfigParser.read(self, self.filename)

    def getGeneralConfig(self):
        """Get configuration from the general section as a
        dictionary.

        Contents:

            * shelf_location: Location of the shelf.
            * imagecache_location: Location of the image cache.
            * thumbnail_image_size: Thumbnail size.
            * default_image_size: Default image size.
            * image_sizes: Image sizes as a sorted list of unique
              integers.
        """
        def checkConfigurationItem(key, function):
            if not self.has_option("general", key):
                raise MissingConfigurationKeyError, key
            if function and not function(self.get("general", key)):
                raise BadConfigurationValueError, (key, value)
        def isInt(arg):
            try:
                int(arg)
                return True
            except ValueError:
                return False

        checkConfigurationItem("shelf_location", None)
        checkConfigurationItem("imagecache_location", None)
        checkConfigurationItem("thumbnail_image_size", isInt)
        checkConfigurationItem("default_image_size", isInt)
        checkConfigurationItem("other_image_sizes", None)
        result = {}
        for key in ["shelf_location", "imagecache_location"]:
            result[key] = os.path.expanduser(self.get("general", key))
        for key in ["thumbnail_image_size", "default_image_size"]:
            result[key] = self.getint("general", key)

        imgsizesval = self.get("general", "other_image_sizes")
        # TODO: Use sets module when Python 2.3 or higher is required.
        imgsizesdict = dict([(int(x), True)
                             for x in re.findall("\d+", imgsizesval)])
        imgsizesdict[result["default_image_size"]] = True
        imgsizes = imgsizesdict.keys()
        imgsizes.sort()
        result["image_sizes"] = imgsizes
        return result

def createConfigTemplate(filename):
    file(filename, "w").write(
        """### Configuration file for Kofoto.

## General configuration
[general]

# Default location of the shelf. This is where information about
# albums, images, categories, etc., is stored.
shelf_location = ~/.kofoto/shelf

# Location of the image cache. This is where generated images are
# stored.
imagecache_location = ~/.kofoto/imagecache

# Size of thumbnails.
thumbnail_image_size = 128

# The image size that will be used when first entering an album.
default_image_size = 640

# A list of image sizes (other than default_image_size) to include in
# albums.
other_image_sizes = 400 1024

## Configuration for the GNOME client "gkofoto".
[gnome]

## Configuration for the default output module "woolly".
[woolly]
""")
