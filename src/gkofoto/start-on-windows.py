import os
import sys

if sys.platform.startswith("win"):
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

bindir = os.path.dirname(sys.argv[0])

from gkofoto.main import main
main(bindir, sys.argv)
