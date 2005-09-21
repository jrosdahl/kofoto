"""Kofoto client utility functions."""

######################################################################
### Public names.

__all__ = [
    "DIRECTORIES_TO_IGNORE",
    "walk_files",
    ]

######################################################################
### Libraries.

import os

######################################################################
### Implementation.

DIRECTORIES_TO_IGNORE = [
    ".jimageviewpics",
    ".svn",
    ".thumbnails",
    ".xvpics",
    "CVS",
    "MT",
    "_darcs",
    "{arch}",
    ]

def walk_files(paths, directories_to_ignore=None):
    """Traverse paths and return filename while ignoring some directories.

    Arguments:

        paths -- A list of files and directories to traverse.

        directories_to_ignore -- A list of directory names to ignore.
        If None, directories in DIRECTORIES_TO_IGNORE are ignored.

    Returns:

        An iterable returning paths to the found files.
    """
    if directories_to_ignore == None:
        directories_to_ignore = DIRECTORIES_TO_IGNORE
    for x in paths:
        if os.path.isfile(x):
            yield x
        elif os.path.isdir(x):
            if os.path.basename(x) in directories_to_ignore:
                continue
            for dirpath, dirnames, filenames in os.walk(x):
                for igndir in directories_to_ignore:
                    try:
                        dirnames.remove(igndir)
                    except ValueError:
                        pass
                for filename in filenames:
                    yield os.path.join(dirpath, filename)
