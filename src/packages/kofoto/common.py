"""Common code for Kofoto libraries."""

######################################################################
### Public names.

__all__ = [
    "KofotoError",
    "UnimplementedError",
    "calculate_downscaled_size",
    "symlink_or_copy_file",
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

def calculate_downscaled_size(width, height, width_limit, height_limit):
    """Scale down width and height to fit within given limits."""

    w = width
    h = height
    if w > width_limit:
        h = width_limit * h // w
        w = width_limit
    if h > height_limit:
        w = height_limit * w // h
        h = height_limit
    return w, h

def calculate_rescaled_size(width, height, width_limit, height_limit):
    """Scale up or down width and height to fit within given limits."""

    w = width_limit
    h = width_limit * height // width
    if h > height_limit:
        w = height_limit * w // h
        h = height_limit
    return w, h

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
