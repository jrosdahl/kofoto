"""Common code for Kofoto libraries."""

######################################################################
### Public names.

__all__ = [
    "KofotoError",
    "UnimplementedError",
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

class UnimplementedError(KofotoError):
    """Unimplemented method."""

######################################################################
### Functions.

def calculateDownscaledDimensions(width, height, widthlimit, heightlimit):
    """Scale down width and height to fit within given limits."""

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
    """Create a symbolic link, or copy if support links are not supported."""

    try:
        os.unlink(destination)
    except OSError:
        pass
    try:
        os.symlink(source, destination)
    except AttributeError:
        # The platform doesn't support symlinks.

        import shutil
        if not os.path.dirname(source):
            # Handle the case of "ln -s foo dir/bar".
            source = os.path.join(os.path.dirname(destination), source)
        shutil.copy(source, destination)
