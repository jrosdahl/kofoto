"""Client environment module for Kofoto."""

__all__ = [
    "BadConfigFileError",
    "ClientEnvironment",
    "ClientEnvironmentError",
    "ConfigFileError",
    "MissingConfigFileError",
    "MissingShelfError",
]

import locale
import os
import sys
from kofoto.config import \
    BadConfigurationValueError, \
    Config, \
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

    codeset            -- The codeset to use for encoding to and decoding from
                          the current locale.
    config             -- A kofoto.config.Config instance.
    configFileLocation -- Location of the configuration file.
    shelf              -- A kofoto.shelf.Shelf instance.
    shelfLocation      -- Location of the shelf.
    imageCache         -- A kofoto.imagecache.ImageCache instance.
    version            -- Kofoto version (a string).
    """

    def __init__(self, localCodeset=None):
        """Initialize the client environment instance.

        If localCodeset is None, the preferred character set encoding
        is read from the environment and used as the local codeset.
        Otherwise, localCodeset is used.

        Note that the setup method must be called to further
        initialize the instance.
        """

        if localCodeset == None:
            locale.setlocale(locale.LC_ALL, "")
            self.__codeset = locale.getpreferredencoding()
        else:
            self.__codeset = localCodeset

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
            if sys.platform.startswith("win"):
                self.__configFileLocation = os.path.expanduser(
                    os.path.join("~", "KofotoData", "config.ini"))
            else:
                self.__configFileLocation = os.path.expanduser(
                    os.path.join("~", ".kofoto", "config"))
        else:
            self.__configFileLocation = configFileLocation

        if not os.path.exists(self.configFileLocation):
            confdir = os.path.dirname(self.configFileLocation)
            if confdir and not os.path.exists(confdir):
                os.mkdir(confdir)
                self._writeInfo("Created directory \"%s\".\n" % confdir)
            if createMissingConfigFile:
                createConfigTemplate(self.configFileLocation)
                self._writeInfo("Created configuration file \"%s\".\n" %
                                self.configFileLocation)
            else:
                raise MissingConfigFileError, \
                    ("Missing configuration file: \"%s\"\n" %
                         self.configFileLocation,
                     self.configFileLocation)
        self.__config = Config(self.codeset)

        try:
            self.config.read(self.configFileLocation)
            self.config.verify()
        except MissingSectionHeaderError:
            raise BadConfigFileError, \
                  ("Bad configuration (missing section headers).\n",
                   self.configFileLocation)
        except MissingConfigurationKeyError, (section, key):
            raise BadConfigFileError, \
                  ("Missing configuration key in %s section: %s.\n" % (
                       section, key),
                   self.configFileLocation)
        except BadConfigurationValueError, (section, key, value):
            raise BadConfigFileError, \
                  ("Bad configuration value for %s in %s section: %s.\n" % (
                    key, section, value),
                   self.configFileLocation)

        if shelfLocation == None:
            self.__shelfLocation = \
                os.path.expanduser(
                    self.unicodeToLocalizedString(
                        self.config.get("database", "location")))
        else:
            self.__shelfLocation = shelfLocation

        self.__shelf = Shelf(self.shelfLocation, self.codeset)

        if not os.path.exists(self.shelfLocation):
            if createMissingShelf:
                try:
                    self.shelf.create()
                except FailedWritingError, self.shelfLocation:
                    raise BadShelfError, \
                        ("Could not create metadata database \"%s\".\n" % (
                             self.shelfLocation),
                         self.shelfLocation)
                self._writeInfo(
                    "Created metadata database \"%s\".\n" % self.shelfLocation)
            else:
                raise MissingShelfError, \
                    ("Could not open metadata database \"%s\"" % (
                        self.shelfLocation),
                     self.shelfLocation)

        self.__imageCache = ImageCache(
            os.path.expanduser(
                self.unicodeToLocalizedString(
                    self.config.get("image cache", "location"))),
            self.config.getboolean("image cache", "use_orientation_attribute"))

    def getCodeset(self):
        """Get codeset."""
        return self.__codeset
    codeset = property(getCodeset)

    def getConfig(self):
        """Get the Config instance."""
        return self.__config
    config = property(getConfig)

    def getConfigFileLocation(self):
        """Get the configuration file location."""
        return self.__configFileLocation
    configFileLocation = property(getConfigFileLocation)

    def getShelf(self):
        """Get the Shelf instance."""
        return self.__shelf
    shelf = property(getShelf)

    def getShelfLocation(self):
        """Get the shelf location."""
        return self.__shelfLocation
    shelfLocation = property(getShelfLocation)

    def getImageCache(self):
        """Get the ImageCache instance."""
        return self.__imageCache
    imageCache = property(getImageCache)

    def getVersion(self):
        """Get the Kofoto version (a string)."""
        return kofotoVersion
    version = property(getVersion)

    def unicodeToLocalizedString(self, unicodeString):
        """Convert a Unicode string to a localized string.

        If unicodeString is a Unicode string, convert it to a
        localized string. Otherwise, unicodeString is returned without
        any conversion.
        """
        if isinstance(unicodeString, unicode):
            return unicodeString.encode(self.codeset)
        else:
            return unicodeString

    def localizedStringToUnicode(self, localizedString):
        """Convert a localized string to a Unicode string."""
        return localizedString.decode(self.codeset)

    def _writeInfo(self, infoString):
        """Write an informational string to a suitable place.

        This is the default implementation: write to standard output. 
        Subclasses should override this method if they want to handle
        the output themselves.
        """
        sys.stdout.write(self.unicodeToLocalizedString(infoString))
        sys.stdout.flush()
