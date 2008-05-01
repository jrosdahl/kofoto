"""Common code for Kofoto libraries."""

######################################################################
### Public names.

__all__ = [
    "KofotoError",
    "NotImplementedError",
    "symlink_or_copy_file",
    ]

######################################################################
### Imports.

import os

######################################################################
### Exceptions.

class KofotoError(Exception):
    """Base class for Kofoto exceptions."""

######################################################################
### Functions.

def symlink_or_copy_file(source, destination):
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
