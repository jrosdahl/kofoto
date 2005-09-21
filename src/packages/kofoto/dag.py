"""A directed, acyclic graph."""

__all__ = ["DAG", "LoopError"]

from sets import Set
from kofoto.common import KofotoError

class LoopError(KofotoError):
    pass

class DAG:
    def __init__(self, initlist=None):
        self.roots = Set()
        self.elements = Set()
        self.parents = {}
        self.children = {}
        if initlist:
            for element in initlist:
                self.roots.add(element)
                self.elements.add(element)
                self.parents[element] = Set()
                self.children[element] = Set()

    def __contains__(self, element):
        return element in self.elements

    def __iter__(self):
        return self.elements.__iter__()

    def add(self, element):
        self.roots.add(element)
        self.elements.add(element)
        self.parents[element] = Set()
        self.children[element] = Set()

    def connect(self, parent, child):
        if self.reachable(child, parent):
            raise LoopError, (parent, child)
        self.parents[child].add(parent)
        self.children[parent].add(child)
        self.roots.discard(child)

    def connected(self, parent, child):
        return child in self.children[parent]

    def disconnect(self, parent, child):
        self.parents[child].discard(parent)
        self.children[parent].discard(child)
        if len(self.children[parent]) == 0:
            self.roots.add(parent)

    def getAncestors(self, element):
        visited = Set()
        stack = [element]
        while stack:
            el = stack.pop()
            if el in visited:
                continue
            visited.add(el)
            yield el
            stack.extend(self.parents[el])

    def getChildren(self, element):
        return self.children[element]

    def getDescendants(self, element):
        visited = Set()
        stack = [element]
        while stack:
            el = stack.pop()
            if el in visited:
                continue
            visited.add(el)
            yield el
            stack.extend(self.children[el])

    def getParents(self, element):
        return self.parents[element]

    def getRoots(self):
        return self.roots

    def reachable(self, parent, child):
        return child in self.getDescendants(parent)

    def remove(self, element):
        self.roots.discard(element)
        self.elements.remove(element)
        for parent in self.parents[element]:
            self.children[parent].remove(element)
        for child in self.children[element]:
            self.parents[child].remove(element)
        del self.parents[element]
        del self.children[element]
