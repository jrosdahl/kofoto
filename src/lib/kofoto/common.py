"""Common code for Kofoto libraries."""

######################################################################
### Public names.

__all__ = ["KofotoError", "pathSplit", "symlinkOrCopyFile"]

######################################################################
### Imports.

import os

######################################################################
### Exceptions.

class KofotoError(Exception):
    """Base class for Kofoto exceptions."""
    pass

######################################################################
### Functions.

def symlinkOrCopyFile(source, destination):
    import os
    try:
        os.unlink(destination)
    except OSError:
        pass
    try:
        os.symlink(source, destination)
    except AttributeError:
        import shutil
        shutil.copy(source, destination)

def pathSplit(path):
    result = []
    while True:
        if not path:
            break
        path, tail = os.path.split(path)
        result.insert(0, tail)
    return result
