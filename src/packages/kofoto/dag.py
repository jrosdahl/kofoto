"""Implementation of the DAG class."""

__all__ = ["DAG", "LoopError"]

from sets import Set
from kofoto.common import KofotoError

class LoopError(KofotoError):
    """A loop would have been created."""
    pass

class DAG:
    """A directed, acyclic graph."""
    def __init__(self, initlist=None):
        """Constructor.

        Arguments:

        initlist -- A list of elements to add to the DAG. The element
                    will be unconnected.
        """
        self.roots = Set()
        self.elements = Set()
        self.parents = {}
        self.children = {}
        if initlist:
            for element in initlist:
                self.add(element)

    def __contains__(self, element):
        return element in self.elements

    def __iter__(self):
        return self.elements.__iter__()

    def add(self, element):
        """Add an element to the DAG."""
        self.roots.add(element)
        self.elements.add(element)
        self.parents[element] = Set()
        self.children[element] = Set()

    def connect(self, parent, child):
        """Add an element to another element."""
        if self.reachable(child, parent):
            raise LoopError(parent, child)
        self.parents[child].add(parent)
        self.children[parent].add(child)
        self.roots.discard(child)

    def connected(self, parent, child):
        """Check whether an element is connected to another element."""
        return child in self.children[parent]

    def disconnect(self, parent, child):
        """Disconnect a parent element from a child element.

        If the elements are not connected, nothing will happen.
        """
        self.parents[child].discard(parent)
        self.children[parent].discard(child)
        if len(self.children[parent]) == 0:
            self.roots.add(parent)

    def getAncestors(self, element):
        """Get the ancestors of an element.

        An iterable is returned.
        """
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
        """Get the immediate children of an element.

        An iterable is returned.
        """
        return self.children[element]

    def getDescendants(self, element):
        """Get the descendants of an element.

        An iterable is returned.
        """
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
        """Get the immediate parents of an element.

        An iterable is returned.
        """
        return self.parents[element]

    def getRoots(self):
        """Get the roots of the DAG.

        An iterable is returned.
        """
        return self.roots

    def reachable(self, parent, child):
        """Check whether an element is reachable from another element."""
        return child in self.getDescendants(parent)

    def remove(self, element):
        """Remove an element from the DAG."""
        self.roots.discard(element)
        self.elements.remove(element)
        for parent in self.parents[element]:
            self.children[parent].remove(element)
        for child in self.children[element]:
            self.parents[child].remove(element)
        del self.parents[element]
        del self.children[element]
