"""Configuration module for Kofoto."""

__all__ = [
    "BadConfigurationValueError",
    "Config",
    "ConfigError",
    "DEFAULT_CONFIGFILE",
    "MissingConfigurationKeyError",
    "MissingSectionHeaderError",
    "createConfigTemplate",
]

from ConfigParser import *
ConfigParserMissingSectionHeaderError = MissingSectionHeaderError
import os
import re
from sets import Set
from kofoto.common import KofotoError

DEFAULT_CONFIGFILE = os.path.expanduser("~/.kofoto/config")

class ConfigError(KofotoError):
    pass

class MissingSectionHeaderError(KofotoError):
    pass

class MissingConfigurationKeyError(KofotoError):
    pass

class BadConfigurationValueError(KofotoError):
    pass

class Config(ConfigParser):
    def __init__(self, filename, encoding):
        ConfigParser.__init__(self)
        self.filename = filename
        self.encoding = encoding

    def read(self):
        try:
            ConfigParser.read(self, self.filename)
        except ConfigParserMissingSectionHeaderError:
            raise MissingConfigurationKeyError

    def get(self, *args, **kwargs):
        return unicode(ConfigParser.get(self, *args, **kwargs), self.encoding)

    def getGeneralConfig(self):
        """Get configuration from the general section as a
        dictionary.

        Contents:

            * shelf_location: Location of the shelf (encoded in the
              local character encoding).
            * imagecache_location: Location of the image cache
              (encoded in the local character encoding).
            * thumbnail_size: Thumbnail size.
            * default_image_size: Default image size.
            * image_sizes: Image sizes as a sorted list of unique
              integers.
        """
        def checkConfigurationItem(section, key, function):
            if not self.has_option(section, key):
                raise MissingConfigurationKeyError, (section, key)
            value = self.get(section, key)
            if function and not function(value):
                raise BadConfigurationValueError, (section, key, value)
        def isInt(arg):
            try:
                int(arg)
                return True
            except ValueError:
                return False

        checkConfigurationItem("shelf", "location", None)
        checkConfigurationItem("image cache", "location", None)
        checkConfigurationItem(
            "album generation", "thumbnail_size", isInt)
        checkConfigurationItem(
            "album generation", "default_image_size", isInt)
        checkConfigurationItem(
            "album generation", "other_image_sizes", None)
        result = {}
        for key, section, option in [
            ("shelf_location", "shelf", "location"),
            ("imagecache_location", "image cache",  "location")]:
            result[key] = os.path.expanduser(
                self.get(section, option).encode(self.encoding))
        for key in ["thumbnail_size", "default_image_size"]:
            result[key] = self.getint("album generation", key)

        imgsizesval = self.get("album generation", "other_image_sizes")
        imgsizesset = Set([int(x) for x in re.findall("\d+", imgsizesval)])
        imgsizesset.add(result["default_image_size"])
        imgsizes = list(imgsizesset)
        imgsizes.sort()
        result["image_sizes"] = imgsizes
        return result

def createConfigTemplate(filename):
    file(filename, "w").write(
        """### Configuration file for Kofoto.

######################################################################
## General configuration
[shelf]

# Default location of the shelf. This is where information about
# albums, images, categories, etc., is stored.
location = ~/.kofoto/shelf

######################################################################
## Configuration of the image cache.
[image cache]

# Location of the image cache. This is where generated images are
# stored.
location = ~/.kofoto/imagecache

######################################################################
## Configuration for album generation in general.
[album generation]

# Size of thumbnails.
thumbnail_size = 128

# The image size that will be used when first entering an album.
default_image_size = 640

# A list of image sizes (other than default_image_size) to include in
# albums.
other_image_sizes = 400 1024

######################################################################
## Configuration for the GNOME client "gkofoto".
[gnome client]

# Size of thumbnails. Use the same size as in the album generation
# section above to share cached thumbnails.
thumbnail_size = 128

# The columns that should be shown in the table view by default.
default_table_columns = captured description title

# The column to sort on by default.
default_sort_column = captured

######################################################################
## Configuration for the default output module "woolly".
[woolly]

# A list of tags for categories to display on image pages.
display_categories = 

# Whether automatic descriptions should be used. If enabled and
# neither title nor description is set for an image, a description is
# constructed using the template given by auto_descriptions_template.
enable_auto_descriptions = no

# Template to use when constructing automatic descriptions. The
# template may contain category tags enclosed in angle brackets. If an
# image has several matching subcategories, they are delimited with
# commas.
auto_descriptions_template = <depicted> (<location>)
""")
