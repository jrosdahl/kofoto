from environment import env
from sets import Set

class ObjectSelection:
    def __init__(self):
        self.__selectedObjects = {}
        self.__changedCallbacks = Set()

    def addChangedCallback(self, callback):
        self.__changedCallbacks.add(callback)

    def removeChangedCallback(self, callback):
        self.__changedCallbacks.remove(callback)

    def unselectAll(self):
        self.__selectedObjects.clear()
        self.__invokeChangedCallbacks()

    def setSelection(self, objectIds):
        self.__selectedObjects.clear()
        for objectId in objectIds:
            self.__selectedObjects[objectId] = env.shelf.getObject(objectId)
        self.__invokeChangedCallbacks()

    def addSelection(self, objectId):
        self.__selectedObjects[objectId] = env.shelf.getObject(objectId)
        self.__invokeChangedCallbacks()

    def removeSelection(self, objectId):
        del self.__selectedObjects[objectId]
        self.__invokeChangedCallbacks()

    def getSelectedIds(self):
        return self.__selectedObjects.keys()

    def getSelectedObjects(self):
        return self.__selectedObjects.values()
    
    def __contains__(self, objectId):
        return objectId in self.__selectedObjects.keys()

    def __len__(self):
        return len(self.__selectedObjects)

    def __iter__(self):
        return self.__selectedObjects.__iter__()

    def __getitem__(self, selectedId):
        return self.__selectedObjects[selectedId]
    
    def __invokeChangedCallbacks(self):
        env.debug("Invoking selection changed callbacks: " + str(self.__selectedObjects.keys()))
        for callback in self.__changedCallbacks:
            callback(self)
        
    
