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
from kofoto.config import *
from kofoto.shelf import Shelf, FailedWritingError
from kofoto.imagecache import ImageCache

######################################################################
# Public classes.

class ClientEnvironmentError(Exception):
    pass

class ConfigFileError(ClientEnvironmentError):
    pass

class MissingConfigFileError(ConfigFileError):
    pass

class BadConfigFileError(ConfigFileError):
    pass

class ShelfError(ClientEnvironmentError):
    pass

class MissingShelfError(ShelfError):
    pass

class BadShelfError(ShelfError):
    pass

class ClientEnvironment(object):
    def __init__(self, localCodeset=None):
        """Initialize the client environment instance.

        If localCodeset is None, the preferred character set encoding
        is read from the environment and used as the local codeset.
        Otherwise, localCodeset is used."""

        if localCodeset == None:
            locale.setlocale(locale.LC_ALL, "")
            self.__codeset = locale.getpreferredencoding()
        else:
            self.__codeset = localCodeset

    def setup(self, configFileLocation=None, shelfLocation=None,
              createMissingConfigFile=True, createMissingShelf=True):
        """Set up the environment.

        If configFileLocation is None, a per-system default value is
        used.

        If shelfLocation is None, a per-system default value is used.

        A missing configuration file will be created iff
        createMissingConfigFile is true.

        A missing shelf will be created iff createMissingShel is true.
        """

        if configFileLocation == None:
            if sys.platform.startswith("win"):
                configFileLocation = os.path.expanduser("~/KofotoData/config.ini")
            else:
                configFileLocation = os.path.expanduser("~/.kofoto/config")

        if not os.path.exists(configFileLocation):
            confdir = os.path.dirname(configFileLocation)
            if confdir and not os.path.exists(confdir):
                os.mkdir(confdir)
                self._writeInfo("Created directory \"%s\".\n" % confdir)
            if createMissingConfigFile:
                createConfigTemplate(configFileLocation)
                self._writeInfo("Created configuration file \"%s\".\n" %
                                configFileLocation)
            else:
                raise MissingConfigFileError, \
                    ("Missing configuration file: \"%s\"\n" %
                         configFileLocation,
                     configFileLocation)
        self.__config = Config(configFileLocation, self.codeset)

        try:
            self.config.read()
            self.config.verify()
        except MissingSectionHeaderError, x:
            raise BadConfigFileError, \
                  ("Bad configuration (missing section headers).\n",
                   configFileLocation)
        except MissingConfigurationKeyError, (section, key):
            raise BadConfigFileError, \
                  ("Missing configuration key in %s section: %s.\n" % (
                       section, key),
                   configFileLocation)
        except BadConfigurationValueError, (section, key, value):
            raise BadConfigFileError, \
                  ("Bad configuration value for %s in %s section: %s.\n" % (
                    key, section, value),
                   configFileLocation)

        if shelfLocation == None:
            shelfLocation = self.unicodeToLocalizedString(
                os.path.expanduser(self.config.get("shelf", "location")))

        self.__shelf = Shelf(shelfLocation, self.codeset)

        if not os.path.exists(shelfLocation):
            if createMissingShelf:
                try:
                    self.shelf.create()
                except FailedWritingError, shelfLocation:
                    raise BadShelfError, \
                        ("Could not create shelf file %s.\n" % shelfLocation,
                         shelfLocation)
                self._writeInfo("Created shelf \"%s\".\n" % shelfLocation)
            else:
                raise MissingShelfError, \
                    ("Could not open shelf \"%s\"" % shelfLocation,
                     shelfLocation)

        self.__imageCache = ImageCache(
            self.unicodeToLocalizedString(
                os.path.expanduser(self.config.get("image cache", "location"))),
            self.config.getboolean("image cache", "use_orientation_attribute"))

    def getCodeset(self):
        return self.__codeset
    codeset = property(getCodeset)

    def getConfig(self):
        return self.__config
    config = property(getConfig)

    def getShelf(self):
        return self.__shelf
    shelf = property(getShelf)

    def getImageCache(self):
        return self.__imageCache
    imageCache = property(getImageCache)

    def unicodeToLocalizedString(self, unicodeString):
        """If unicodeString is a Unicode string, convert it to a
        localized string. Otherwise, unicodeString is returned without
        any conversion."""
        if isinstance(unicodeString, unicode):
            return unicodeString.encode(self.codeset)
        else:
            return unicodeString

    def localizedStringToUnicode(self, localizedString):
        """Convert a localized string to a Unicode string."""
        return localizedString.decode(self.codeset)

    def _writeInfo(self, infoString):
        """Default implementation: Write to standard output."""
        sys.stdout.write(self.unicodeToLocalizedString(infoString))
        sys.stdout.flush()
