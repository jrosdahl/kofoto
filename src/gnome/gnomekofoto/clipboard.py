from sets import Set
from environment import env
from kofoto.shelf import Image
from kofoto.shelf import Album
from kofoto.shelf import Category

class Clipboard:

    # TYPES
    OBJECTS    = 0 # shelf.Album and shelf.Image
    CATEGORIES = 1 # shelf.Category
    
    def __init__(self):
        self.__changedCallbacks = Set()
        self.clear()

    def addChangedCallback(self, callback):
        self.__changedCallbacks.add(callback)

    def removeChangedCallback(self, callback):
        self.__changedCallbacks.remove(callback)

    def setObjects(self, iter):
        self.__objects = []
        self.__types = Clipboard.OBJECTS
        for object in iter:
            if (isinstance(object, Image) or isinstance(object, Album)):
                self.__objects.append(object)
            else:
                self.clear()
                raise "Object is not an Image nor an Album" # TODO
        self.__invokeChangedCallbacks()

    def setCategories(self, iter):
        self.__objects = []
        self.__types = Clipboard.CATEGORIES
        for object in iter:
            if isinstance(object, Category):
                self.__objects.append(object)
            else:
                self.clear()
                raise "Object is not a Category" # TODO
        self.__invokeChangedCallbacks()
        
    def clear(self):
        self.__objects = []
        self.__types = None
        self.__invokeChangedCallbacks()

    def hasCategories(self):
        return (self.__types == Clipboard.CATEGORIES and len(self.__objects) > 0)

    def hasObjects(self):
        return (self.__types == Clipboard.OBJECTS and len(self.__objects) > 0)
        
    def __len__(self):
        return len(self.__objects)

    def __iter__(self):
        return self.__objects.__iter__()

    def __invokeChangedCallbacks(self):
        for callback in self.__changedCallbacks:
            callback(self)
