"""Client environment module for Kofoto."""

__all__ = [
    "BadConfigFileError",
    "ClientEnvironment",
    "ClientEnvironmentError",
    "ConfigFileError",
    "MissingConfigFileError",
    "MissingShelfError",
]

import codecs
import locale
import os
import sys
from kofoto.clientutils import expanduser
from kofoto.config import \
    BadConfigurationValueError, \
    Config, \
    DEFAULT_CONFIGFILE_LOCATION, \
    MissingConfigurationKeyError, \
    MissingSectionHeaderError, \
    createConfigTemplate
from kofoto.shelf import Shelf, FailedWritingError
from kofoto.imagecache import ImageCache
from kofoto.version import version as kofotoVersion

######################################################################
# Public classes.

class ClientEnvironmentError(Exception):
    """Base class for exceptions in the module."""
    pass

class ConfigFileError(ClientEnvironmentError):
    """Base class for configuration file exceptions in the module."""
    pass

class MissingConfigFileError(ConfigFileError):
    """Missing configuration file.

    Exception parameter: configuration file location.
    """
    pass

class BadConfigFileError(ConfigFileError):
    """Bad configuration file.

    Exception parameter: configuration file location.
    """
    pass

class ShelfError(ClientEnvironmentError):
    """Base class for shelf-related exceptions in the module."""
    pass

class MissingShelfError(ShelfError):
    """Missing shelf.

    Exception parameter: shelf location.
    """
    pass

class BadShelfError(ShelfError):
    """Bad shelf.

    Exception parameter: shelf location.
    """
    pass

class ClientEnvironment(object):
    """Environment useful for a Kofoto client.

    A properly initialized ClientEnvironment instance has the
    following available attributes:

    config             -- A kofoto.config.Config instance.
    configFileLocation -- Location of the configuration file.
    filesystemEncoding -- The codeset to use for encoding to and decoding from
                          paths in the file system.
    imageCache         -- A kofoto.imagecache.ImageCache instance.
    localeEncoding     -- The codeset to use for encoding to and decoding from
                          the current locale.
    shelf              -- A kofoto.shelf.Shelf instance.
    shelfLocation      -- Location of the shelf.
    version            -- Kofoto version (a string).
    """

    def __init__(self):
        """Initialize the client environment instance.

        Note that the setup method must be called to further
        initialize the instance.
        """

        self.__localeEncoding = locale.getpreferredencoding()
        self.__filesystemEncoding = sys.getfilesystemencoding()

        # These are initiazlied in the setup method.
        self.__config = None
        self.__configFileLocation = None
        self.__imageCache = None
        self.__shelf = None
        self.__shelfLocation = None

    def setup(self, configFileLocation=None, shelfLocation=None,
              createMissingConfigFile=True, createMissingShelf=True):
        """Set up the environment.

        If configFileLocation is None, a per-system default value is
        used.

        If shelfLocation is None, a per-system default value is used.

        A missing configuration file will be created iff
        createMissingConfigFile is true.

        A missing shelf will be created iff createMissingShelf is true.
        """

        if configFileLocation == None:
            self.__configFileLocation = expanduser(DEFAULT_CONFIGFILE_LOCATION)
        else:
            self.__configFileLocation = configFileLocation

        if not os.path.exists(self.configFileLocation):
            confdir = os.path.dirname(self.configFileLocation)
            if confdir and not os.path.exists(confdir):
                os.mkdir(confdir)
                self._writeInfo(u"Created directory \"%s\".\n" % confdir)
            if createMissingConfigFile:
                f = codecs.open(
                    self.configFileLocation, "w", self.localeEncoding)
                createConfigTemplate(f)
                self._writeInfo(u"Created configuration file \"%s\".\n" %
                                self.configFileLocation)
            else:
                raise MissingConfigFileError(
                    u"Missing configuration file: \"%s\"\n" %
                         self.configFileLocation,
                    self.configFileLocation)
        self.__config = Config(self.localeEncoding)

        try:
            self.config.read(self.configFileLocation)
            self.config.verify()
        except MissingSectionHeaderError:
            raise BadConfigFileError(
                  "Bad configuration (missing section headers).\n",
                  self.configFileLocation)
        except MissingConfigurationKeyError, e:
            (section, key) = e
            raise BadConfigFileError(
                  "Missing configuration key in %s section: %s.\n" % (
                      section, key),
                  self.configFileLocation)
        except BadConfigurationValueError, e:
            (section, key, value) = e
            raise BadConfigFileError(
                  "Bad configuration value for %s in %s section: %s.\n" % (
                      key, section, value),
                  self.configFileLocation)

        if shelfLocation == None:
            location = self.config.get("database", "location")
            self.__shelfLocation = expanduser(location)
        else:
            self.__shelfLocation = shelfLocation

        self.__shelf = Shelf(self.shelfLocation)

        if not os.path.exists(self.shelfLocation):
            if createMissingShelf:
                try:
                    self.shelf.create()
                except FailedWritingError:
                    raise BadShelfError(
                        "Could not create metadata database \"%s\".\n" % (
                            self.shelfLocation),
                        self.shelfLocation)
                self._writeInfo(
                    "Created metadata database \"%s\".\n" % self.shelfLocation)
            else:
                raise MissingShelfError(
                    "Could not open metadata database \"%s\"" % (
                        self.shelfLocation),
                    self.shelfLocation)

        self.__imageCache = ImageCache(
            expanduser(self.config.get("image cache", "location")),
            self.config.getboolean("image cache", "use_orientation_attribute"))

    @property
    def localeEncoding(self):
        """Get encoding of the locale."""
        return self.__localeEncoding

    @property
    def filesystemEncoding(self):
        """Get encoding of the filesystem."""
        return self.__filesystemEncoding

    @property
    def config(self):
        """Get the Config instance."""
        return self.__config

    @property
    def configFileLocation(self):
        """Get the configuration file location."""
        return self.__configFileLocation

    @property
    def shelf(self):
        """Get the Shelf instance."""
        return self.__shelf

    @property
    def shelfLocation(self):
        """Get the shelf location."""
        return self.__shelfLocation

    @property
    def imageCache(self):
        """Get the ImageCache instance."""
        return self.__imageCache

    @property
    def version(self):
        """Get the Kofoto version (a string)."""
        return kofotoVersion

    def _writeInfo(self, infoString):
        """Write an informational string to a suitable place.

        Should be overridden by subclasses.
        """
        raise NotImplementedError
