import ConfigParser
import os
import sys

class PersistentState(object):
    def __init__(self):
        self.__configParser = ConfigParser.ConfigParser()
        cp = self.__configParser

        # Defaults:
        cp.add_section("state")
        cp.set("state", "filter-text", "")

        home = os.path.expanduser("~")
        if sys.platform.startswith("win"):
            self.__stateFile = os.path.join(
                home, "KofotoData", "state", "gkofoto.ini")
        else:
            self.__stateFile = os.path.join(
                home, ".kofoto", "state", "gkofoto")
        if not os.path.isdir(os.path.dirname(self.__stateFile)):
            os.mkdir(os.path.dirname(self.__stateFile))
        if os.path.isfile(self.__stateFile):
            self.__configParser.read(self.__stateFile)

    def save(self):
        self.__configParser.write(open(self.__stateFile, "w"))

    def getFilterText(self):
        return self.__configParser.get("state", "filter-text")

    def setFilterText(self, text):
        self.__configParser.set("state", "filter-text", text)

    filterText = property(getFilterText, setFilterText)
