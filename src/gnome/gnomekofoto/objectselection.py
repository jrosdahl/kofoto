from environment import env
from sets import Set

class ObjectSelection:
    def __init__(self, changedCallback):
        self._set = Set()
        self._changedCallback = changedCallback

    def clear(self):
        self._set.clear()
        self._changedCallback()

    def set(self, objectIdList):
        self._set.clear()
        for objectId in objectIdList:
            self._set.add(objectId)
        self._changedCallback()

    def add(self, objectId):
        self._set.add(objectId)
        self._changedCallback()

    def remove(self, objectId):
        self._set.remove(objectId)
        self._changedCallback()

    def __contains__(self, objectId):
        return objectId in self._set

    def __len__(self):
        return len(self._set)

    def __iter__(self):
        return self._set.__iter__()
