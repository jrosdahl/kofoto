"""Kofoto client utility functions."""

######################################################################
### Public names.

__all__ = [
    "DIRECTORIES_TO_IGNORE",
    "expanduser",
    "get_file_encoding",
    "walk_files",
    ]

######################################################################
### Libraries.

import locale
import os
import re
import sys

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

def expanduser(path):
    """Expand ~ and ~user constructions.

    If user or $HOME is unknown, do nothing.

    Unlike os.path.expanduser in Python 2.4.1, this function takes and
    returns Unicode strings correctly.
    """
    fs_encoding = sys.getfilesystemencoding()
    return os.path.expanduser(path.encode(fs_encoding)).decode(fs_encoding)

def get_file_encoding(f):
    if hasattr(f, "encoding") and f.encoding:
        return f.encoding
    else:
        return locale.getpreferredencoding()

def group_image_versions(paths):
    original_extensions = [
        ".cr2", ".crw", ".dcr", ".k25", ".kdc", ".mos", ".mrw", ".nef", ".orf",
        ".pef", ".raf", ".raw", ".srf"]
    def order_extension(ext):
        try:
            return original_extensions.index(ext.lower())
        except ValueError:
            # Not a known original extension. Sort it after originals.
            return len(original_extensions)

    def compare_paths(path1, path2):
        (root1, ext1) = os.path.splitext(path1)
        (root2, ext2) = os.path.splitext(path2)
        extcmp = cmp(order_extension(ext1), order_extension(ext2))
        if extcmp != 0:
            return extcmp
        # The extensions are equal. Sort shorter paths before longer,
        # since originals probably have shorter names.
        lencmp = cmp(len(root1), len(root2))
        if lencmp != 0:
            return lencmp
        return cmp(root1, root2)

    pat = re.compile(r"(\w+)", re.UNICODE)
    bins = {}
    for path in paths:
        (head, tail) = os.path.split(path)
        m = pat.match(tail)
        if m:
            key = os.path.join(head, m.group(1))
        else:
            key = path
        bins.setdefault(key, []).append(path)
    for key in sorted(bins):
        vpaths = bins[key]
        vpaths.sort(cmp=compare_paths)
        yield vpaths

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
