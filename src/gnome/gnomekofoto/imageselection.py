from environment import env
from sets import Set

class ImageSelection:
    def __init__(self, changedCallback):
        self._set = Set()
        self._changedCallback = changedCallback

    def clear(self):
        self._set.clear()
        self._changedCallback()

    def set(self, imageIdList):
        self._set.clear()
        for imageId in imageIdList:
            self._set.add(imageId)
        self._changedCallback()

    def add(self, imageId):
        self._set.add(imageId)
        self._changedCallback()

    def remove(self, imageId):
        self._set.remove(imageId)
        self._changedCallback()

    def __contains__(self, imageId):
        return imageId in self._set

    def __len__(self):
        return len(self._set)

    def __iter__(self):
        return self._set.__iter__()
