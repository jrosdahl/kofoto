"""Common code for Kofoto libraries."""

######################################################################
### Public names.

__all__ = ["KofotoError", "symlinkOrCopyFile"]

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
