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

    def getcoordlist(self, section, option):
        val = self.get(section, option)
        coords = re.split("[,\s]+", val)
        ret = []
        for coord in coords:
            parts = coord.split("x")
            if len(parts) > 2:
                raise BadConfigurationValueError, (section, option, val)
            if len(parts) == 1:
                parts.append(parts[0])
            try:
                x = int(parts[0])
                y = int(parts[1])
            except ValueError:
                raise BadConfigurationValueError, (section, option, val)
            ret.append((x, y))
        return ret

    def getGeneralConfig(self):
        """Get configuration from the general section as a
        dictionary.

        Contents:

            * shelf_location: Location of the shelf (encoded in the
              local character encoding).
            * imagecache_location: Location of the image cache
              (encoded in the local character encoding).
            * use_orientation_attribute: Whether the image cache
              should pay attention to the orientation attribute.
            * thumbnail_size_limit: Thumbnail size limit (a tuple of
              width and height).
            * default_image_size_limit: Default image size limit (a
              tuple of width and height).
            * image_size_limits: Image size limits (a sorted list of
              unique tuples of width and height.
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
            "image cache", "use_orientation_attribute", None)
        checkConfigurationItem(
            "album generation", "thumbnail_size_limit", None)
        checkConfigurationItem(
            "album generation", "default_image_size_limit", None)
        checkConfigurationItem(
            "album generation", "other_image_size_limits", None)
        result = {}
        for key, section, option in [
            ("shelf_location", "shelf", "location"),
            ("imagecache_location", "image cache",  "location")]:
            result[key] = os.path.expanduser(
                self.get(section, option).encode(self.encoding))
        for key, section, option in [
            ("use_orientation_attribute",
             "image cache",
             "use_orientation_attribute")]:
            result[key] = self.getboolean(section, option)
        for key in ["thumbnail_size_limit", "default_image_size_limit"]:
            result[key] = self.getcoordlist("album generation", key)[0]

        imgsizesval = self.getcoordlist(
            "album generation", "other_image_size_limits")
        imgsizesset = Set(imgsizesval) # Get rid of duplicates.
        imgsizesset.add(result["default_image_size_limit"])
        imgsizes = list(imgsizesset)
        imgsizes.sort(lambda x, y: cmp(x[0] * x[1], y[0] * y[1]))
        result["image_size_limits"] = imgsizes
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

# Whether generated/displayed images should be rotated based on the
# orientation attribute, which in turn is derived from the EXIF
# attribute "Image Orientation".
use_orientation_attribute = no

######################################################################
## Configuration for album generation in general.
[album generation]

# Size limit of thumbnails.
thumbnail_size_limit = 128

# The image size limit that will be used when first entering an album.
default_image_size_limit = 640

# A list of image size limits (other than default_image_size_limit) to
# include in albums.
other_image_size_limits = 400 1024x800

######################################################################
## Configuration for the graphical client "gkofoto".
[gkofoto]

# Size limit of thumbnails. Use the same size limit as in the album
# generation section above to share cached thumbnails.
thumbnail_size_limit = 128

# The columns that should be shown in the table view by default.
default_table_columns = thumbnail @captured @title @description albumtag

# The column to sort on by default.
default_sort_column = @captured

open_command = gimp-remote --new %(locations)s
rotate_right_command = jpegtran -rotate 90 -perfect -copy all -outfile %(location)s %(location)s
rotate_left_command = jpegtran -rotate 270 -perfect -copy all -outfile %(location)s %(location)s

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
