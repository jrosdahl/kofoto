"""Common code for Kofoto libraries."""

######################################################################
### Public names.

__all__ = [
    "KofotoError",
    "calculateDownscaledDimensions",
    "symlinkOrCopyFile",
    ]

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

def calculateDownscaledDimensions(width, height, widthlimit, heightlimit):
    w = width
    h = height
    if w > widthlimit:
        h = widthlimit * h // w
        w = widthlimit
    if h > heightlimit:
        w = heightlimit * w // h
        h = heightlimit
    return w, h

def symlinkOrCopyFile(source, destination):
    try:
        os.unlink(destination)
    except OSError:
        pass
    try:
        os.symlink(source, destination)
    except AttributeError:
        import shutil
        if not os.path.dirname(source):
            # Handle the case of "ln -s foo dir/bar".
            source = os.path.join(os.path.dirname(destination), source)
        shutil.copy(source, destination)
