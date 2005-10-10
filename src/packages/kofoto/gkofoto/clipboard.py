from sets import Set
from kofoto.shelf import Album, Image
from kofoto.gkofoto.categories import ClipboardCategories

class Clipboard:

    # TYPES
    OBJECTS    = 0 # shelf.Album and shelf.Image
    CATEGORIES = 1 # shelf.Category

    def __init__(self):
        self.__objects = None
        self.__types = None
        self.__changedCallbacks = Set()
        self.clear()

    def addChangedCallback(self, callback):
        self.__changedCallbacks.add(callback)

    def removeChangedCallback(self, callback):
        self.__changedCallbacks.remove(callback)

    def setObjects(self, iterable):
        self.__objects = []
        self.__types = Clipboard.OBJECTS
        for obj in iterable:
            if (isinstance(obj, Image) or isinstance(obj, Album)):
                self.__objects.append(obj)
            else:
                self.clear()
                raise Exception("Object is not an Image nor an Album") # TODO
        self.__invokeChangedCallbacks()

    def setCategories(self, clipboardCategories):
        self.__objects = []
        if isinstance(clipboardCategories, ClipboardCategories):
            self.__objects.append(clipboardCategories)
        else:
            self.clear()
            raise Exception("Object is not a ClipboardCategories") # TODO
        self.__types = Clipboard.CATEGORIES
        self.__invokeChangedCallbacks()

    def clear(self):
        self.__objects = []
        self.__types = None
        self.__invokeChangedCallbacks()

    def removeObjects(self, obj):
        self.__objects = [x for x in self.__objects if x != obj]
        self.__invokeChangedCallbacks()

    def hasCategories(self):
        return (self.__types == Clipboard.CATEGORIES and len(self.__objects) > 0)

    def hasObjects(self):
        return (self.__types == Clipboard.OBJECTS and len(self.__objects) > 0)

    def __len__(self):
        return len(self.__objects)

    def __iter__(self):
        return self.__objects.__iter__()

    def __getitem__(self, index):
        return self.__objects.__getitem__(index)

    def __invokeChangedCallbacks(self):
        for callback in self.__changedCallbacks:
            callback(self)
