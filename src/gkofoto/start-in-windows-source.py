# This file makes it possible to run GKofoto in Windows directly from
# the source directory by double-clicking on it. A console window is
# also created.

import os
import sys
import _winreg
import msvcrt

try:
    k = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, "Software\\GTK\\2.0")
except EnvironmentError:
    print "You must install the GTK+ 2.2 Runtime Environment to run this program."
    while not msvcrt.kbhit():
        pass
    sys.exit(1)
else:
    gtkdir = _winreg.QueryValueEx(k, "Path")
    os.environ["PATH"] += ";%s/lib;%s/bin" % (gtkdir[0], gtkdir[0])

# Allow (default) datafile location to be determined under Windows 98.
if os.path.expanduser("~") == "~":
    # Probably running under Windows 98 or similar OS where the
    # environment variables HOMEPATH and HOMEDRIVE (and HOME) are not
    # set. We have to fake it instead.
    try:
        # Look up where "My Documents" lives.
        key = _winreg.OpenKey(
            _winreg.HKEY_CURRENT_USER,
            "Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Shell Folders")
        home, dummy = _winreg.QueryValueEx(key, "Personal")
        # At this point home is _probably_ a Unicode string.
    except EnvironmentError:
        home = None

    if home == None:
        # Unable to look up the location so just make one up, however
        # nasty that location may be. We do output where the data
        # location is on gkofoto startup.
        home = "C:\\"

    os.environ["HOME"] = home
    # Note: Use os.environ as os.putenv() at least in Windows 98 only
    # changes variable for sub processes; this process would not see
    # the change.

execfile("start-in-unix-source.py")
