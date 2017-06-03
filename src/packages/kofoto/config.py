"""Configuration module for Kofoto."""

__all__ = [
    "BadConfigurationValueError",
    "Config",
    "ConfigError",
    "DEFAULT_CONFIGFILE_LOCATION",
    "DEFAULT_IMAGECACHE_LOCATION",
    "DEFAULT_SHELF_LOCATION",
    "MissingConfigurationKeyError",
    "MissingSectionHeaderError",
    "createConfigTemplate",
]

from ConfigParser import ConfigParser
from ConfigParser import MissingSectionHeaderError as \
    ConfigParserMissingSectionHeaderError
import codecs
import os
import re
import sys
from kofoto.common import KofotoError

if sys.platform.startswith("win"):
    DEFAULT_CONFIGFILE_LOCATION = os.path.join(
        u"~", u"KofotoData", u"config.ini")
    DEFAULT_SHELF_LOCATION = os.path.join(
        u"~", u"KofotoData", u"metadata.db")
    DEFAULT_IMAGECACHE_LOCATION = os.path.join(
        u"~", u"KofotoData", u"ImageCache")
else:
    DEFAULT_CONFIGFILE_LOCATION = os.path.join(
        u"~", u".kofoto", u"config")
    DEFAULT_SHELF_LOCATION = os.path.join(
        u"~", u".kofoto", u"metadata.db")
    DEFAULT_IMAGECACHE_LOCATION = os.path.join(
        u"~", u".kofoto", u"imagecache")

class ConfigError(KofotoError):
    """Configuration error."""
    pass

class MissingSectionHeaderError(KofotoError):
    """A section header is missing in the configuration file."""
    pass

class MissingConfigurationKeyError(KofotoError):
    """A key is missing in the configuration file."""
    pass

class BadConfigurationValueError(KofotoError):
    """A value is badly formatted in the configuration file."""
    pass

class Config(ConfigParser):
    """A customized configuration parser."""

    def __init__(self, encoding):
        """Constructor.

        Arguments:

        encoding -- The encoding of the configuration files.
        """
        ConfigParser.__init__(self)
        self.encoding = encoding

    def read(self, filenames):
        """Read configuration files."""
        if isinstance(filenames, basestring):
            filenames = [filenames]
        for filename in filenames:
            try:
                fp = codecs.open(filename, "r", self.encoding)
                self.readfp(fp, filename)
            except ConfigParserMissingSectionHeaderError:
                raise MissingSectionHeaderError
            except IOError:
                # From ConfigParser.read documentation: "If a file
                # named in filenames cannot be opened, that file will
                # be ignored."
                pass

    def getcoordlist(self, section, option):
        """Get a coordinate list.

        Coordinate lists look like this:

        100x200, 1024x768 3000x2000

        Returns a list of two-tuples of integers.
        """
        val = self.get(section, option)
        coords = re.split("[,\s]+", val)
        ret = []
        for coord in coords:
            parts = coord.split("x")
            if len(parts) > 2:
                raise BadConfigurationValueError(section, option, val)
            if len(parts) == 1:
                parts.append(parts[0])
            try:
                x = int(parts[0])
                y = int(parts[1])
            except ValueError:
                raise BadConfigurationValueError(section, option, val)
            ret.append((x, y))
        return ret

    def verify(self):
        """Verify the Kofoto configuration."""

        def checkConfigurationItem(section, key, function):
            """Internal helper."""
            if not self.has_option(section, key):
                raise MissingConfigurationKeyError(section, key)
            value = self.get(section, key)
            if function and not function(value):
                raise BadConfigurationValueError(section, key, value)

        checkConfigurationItem("database", "location", None)
        checkConfigurationItem("image cache", "location", None)
        checkConfigurationItem(
            "image cache", "use_orientation_attribute", None)
        checkConfigurationItem(
            "album generation", "thumbnail_size_limit", None)
        checkConfigurationItem(
            "album generation", "default_image_size_limit", None)
        checkConfigurationItem(
            "album generation", "other_image_size_limits", None)


def createConfigTemplate(fileobject):
    """Write a Kofoto configuration template to a file.

    Arguments:

    fileobject -- File object to write the template to.
    """

    fileobject.write(
        u'''### Configuration file for Kofoto.

######################################################################
## General configuration
[database]

# Default location of the metadata database. This is where information
# about albums, images, categories, etc., is stored.
location = %s

######################################################################
## Configuration of the image cache.
[image cache]

# Location of the image cache. This is where generated images are
# stored.
location = %s

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
thumbnail_size_limit = 256

# The columns that should be shown in the table view by default.
default_table_columns = thumbnail versions @captured @title @description albumtag

# The column to sort on by default.
default_sort_column = @captured

open_command = gimp-remote --new %%(locations)s
rotate_right_command = jpegtran -rotate 90 -perfect -copy all -outfile "%%(location)s" "%%(location)s"
rotate_left_command = jpegtran -rotate 270 -perfect -copy all -outfile "%%(location)s" "%%(location)s"

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
''' % (DEFAULT_SHELF_LOCATION, DEFAULT_IMAGECACHE_LOCATION))
