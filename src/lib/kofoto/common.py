"""Common code for Kofoto libraries."""

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
