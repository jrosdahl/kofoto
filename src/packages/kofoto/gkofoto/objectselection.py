from kofoto.gkofoto.environment import env

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
        self.__changedCallbacks = set()
        self.__objectCollection = objectCollection
        self.addChangedCallback(self._nrOfSelectedObjectsChanged)

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
        conv = self.__objectCollection.convertFromUnsortedRowNr
        items = self.__selectedObjects.items()
        items.sort(key=lambda x: conv(x[0]))
        return [x[1] for x in items]

    def getLowestSelectedRowNr(self):
        rowNrs = sorted(self)
        if (len(rowNrs) > 0):
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
            rowNumbers = sorted(self)
            rowNr = rowNumbers[0]
        filenames = []
        for x in [rowNr - 2, rowNr + 2, rowNr - 1, rowNr + 1]: # TODO: Make configurable.
            if 0 <= x < len(model):
                ux = oc.convertToUnsortedRowNr(x)
                obj = self.__getObject(ux)
                if not obj.isAlbum():
                    imageversion = obj.getPrimaryVersion()
                    if imageversion:
                        filenames.append(imageversion.getLocation())
        env.debug("filenames to preload: %s" % str(filenames))
        return filenames

    def _nrOfSelectedObjectsChanged(self, objectSelection):
        env.widgets["statusbarSelectedObjects"].pop(1)
        env.widgets["statusbarSelectedObjects"].push(
            1, "%d selected" % len(objectSelection))

    def __contains__(self, rowNr):
        unsortedRowNr = self.__objectCollection.convertToUnsortedRowNr(rowNr)
        return unsortedRowNr in self.__selectedObjects

    def __len__(self):
        return len(self.__selectedObjects)

    def __iter__(self):
        for unsortedRowNr in self.__selectedObjects:
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
