"""Common code for Kofoto libraries."""

######################################################################
### Exceptions.

class KofotoError(Exception):
    """Base class for Kofoto exceptions."""
    pass

######################################################################
### Functions.

def symlinkOrCopyFile(source, destination):
    try:
        import os
        os.symlink(source, destination)
    except OSError:
        # Destination (probably) already exists.
        pass
    except AttributeError:
        import shutil
        shutil.copy(source, destination)
