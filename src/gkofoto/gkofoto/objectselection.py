from environment import env
from sets import Set

class ObjectSelection:
    def __init__(self, objectCollection):
        # Don't forget to update this class when the model is reordered or
        # when rows are removed or added.
        self.__selectedObjects = {}
        # When objects are stored in self.__selectedObjects, the key MUST be
        # the location in the UNSORTED model since this class is not
        # notified when/if the model is re-sorted.
        #
        # This class must know about each object's row to be able to distinguish
        # individual objects in an album that contains multiple instances
        # of the same image or album.
        self.__changedCallbacks = Set()
        self.__objectCollection = objectCollection
    def addChangedCallback(self, callback):
        self.__changedCallbacks.add(callback)

    def removeChangedCallback(self, callback):
        self.__changedCallbacks.remove(callback)

    def unselectAll(self, notify=True):
        self.__selectedObjects.clear()
        if notify:
            self.__invokeChangedCallbacks()

    def setSelection(self, rowNrs, notify=True):
        self.__selectedObjects.clear()
        for rowNr in rowNrs:
            self.addSelection(rowNr, False)
        if notify:
            self.__invokeChangedCallbacks()

    def addSelection(self, rowNr, notify=True):
        unsortedRowNr = self.__objectCollection.convertToUnsortedRowNr(rowNr)
        self.__selectedObjects[unsortedRowNr] = self.__getObject(unsortedRowNr)
        if notify:
            self.__invokeChangedCallbacks()

    def removeSelection(self, rowNr, notify=True):
        unsortedRowNr = self.__objectCollection.convertToUnsortedRowNr(rowNr)
        del self.__selectedObjects[unsortedRowNr]
        if notify:
            self.__invokeChangedCallbacks()

    def getSelectedObjects(self):
        return self.__selectedObjects.values()

    def getLowestSelectedRowNr(self):
        rowNrs = list(self)
        if (len(rowNrs) > 0):
            rowNrs.sort()
            return rowNrs[0]
        else:
            return None

    def getMap(self):
        return self.__selectedObjects

    def getImageFilenamesToPreload(self):
        oc = self.__objectCollection
        model = oc.getModel()
        if len(self) == 0:
            rowNr = 0
        else:
            rowNumbers = list(self)
            rowNumbers.sort()
            rowNr = rowNumbers[0]
        filenames = []
        for x in [rowNr, rowNr + 1, rowNr - 1, rowNr + 2]: # TODO: Make configurable.
            if 0 <= x < len(model):
                ux = oc.convertToUnsortedRowNr(x)
                filenames.append(self.__getObject(ux).getLocation())
        env.debug("filenames to preload: %s" % str(filenames))
        return filenames

    def __contains__(self, rowNr):
        unsortedRowNr = self.__objectCollection.convertToUnsortedRowNr(rowNr)
        return unsortedRowNr in self.__selectedObjects.keys()

    def __len__(self):
        return len(self.__selectedObjects)

    def __iter__(self):
        for unsortedRowNr in self.__selectedObjects.keys():
            rowNr = self.__objectCollection.convertFromUnsortedRowNr(unsortedRowNr)
            yield rowNr

    def __getitem__(self, rowNr):
        unsortedRowNr = self.__objectCollection.convertToUnsortedRowNr(rowNr)
        return self.__selectedObjects[unsortedRowNr]

    def __invokeChangedCallbacks(self):
        env.debug("Invoking selection changed callbacks: " + str(self.__selectedObjects.keys()))
        for callback in self.__changedCallbacks:
            callback(self)

    def __getObject(self, unsortedRowNr):
        objectId = self.__objectCollection.getUnsortedModel()[unsortedRowNr][self.__objectCollection.COLUMN_OBJECT_ID]
        return env.shelf.getObject(objectId)
