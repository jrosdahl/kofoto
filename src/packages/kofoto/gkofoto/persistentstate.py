import codecs
import os
import sys
from kofoto.clientutils import expanduser
from kofoto.config import Config

class PersistentState(object):
    def __init__(self, env):
        self.__configParser = Config(env.localeEncoding)
        self.__env = env
        cp = self.__configParser

        # Defaults:
        cp.add_section("state")
        cp.set("state", "filter-text", "")

        home = expanduser("~")
        if sys.platform.startswith("win"):
            self.__stateFile = os.path.join(
                home, u"KofotoData", u"state", u"gkofoto.ini")
        else:
            self.__stateFile = os.path.join(
                home, u".kofoto", u"state", u"gkofoto")
        if not os.path.isdir(os.path.dirname(self.__stateFile)):
            os.mkdir(os.path.dirname(self.__stateFile))
        if os.path.isfile(self.__stateFile):
            cp.read(self.__stateFile)

    def save(self):
        fp = codecs.open(self.__stateFile, "w", self.__env.localeEncoding)
        self.__configParser.write(fp)

    def getFilterText(self):
        return self.__configParser.get("state", "filter-text")

    def setFilterText(self, text):
        self.__configParser.set("state", "filter-text", text)

    filterText = property(getFilterText, setFilterText)
