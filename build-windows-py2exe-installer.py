#! /usr/bin/env python

import glob
import os
import py2exe
import setup
import shutil
import sys
import _winreg
import msvcrt
from os.path import join, isdir, basename

options = {
    "py2exe": {
        "includes": "pango,atk,gobject",
        "packages": ["encodings"],
        },
    }

shutil.copy("src/cmdline/kofoto", "kofoto.py")
shutil.copy("src/gkofoto/start-installed.py", "gkofoto.py")
console = ["kofoto.py"]
windows = ["gkofoto.py"]
sys.argv = [sys.argv[0], "py2exe"]

setup.run(options=options, console=console, windows=windows)

os.unlink("kofoto.py")
os.unlink("gkofoto.py")
shutil.rmtree(glob.glob("dist/tcl")[0])
os.remove(glob.glob("dist/tcl*.dll")[0])
os.remove(glob.glob("dist/tk*.dll")[0])

k = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, "Software\\GTK\\2.0")
gtkdir = _winreg.QueryValueEx(k, "Path")[0]
for dir in ["bin", "etc", "lib", "share"]:
    for dirpath, dirnames, filenames in os.walk(join(gtkdir, dir)):
        destdir = join("dist", dirpath[len(gtkdir) + 1:])
        if not isdir(destdir):
            os.makedirs(destdir)
        for filename in filenames:
            print "copying %s --> %s" % (join(dirpath, filename), destdir)
            shutil.copy(join(dirpath, filename), destdir)

shutil.copy("COPYING.txt", "dist/license.txt")
license_file = open("dist/license.txt", "a")
for x in ["python", "gtk", "pygtk", "pil", "pysqlite"]:
    f = open("packaging/%s-license.txt" % x)
    license_file.write("\n")
    license_file.write(f.read())

versionDict = {}
execfile("src/lib/kofoto/version.py", versionDict)

print "creating kofoto.iss"
template = \
    open("packaging/windows/kofoto.iss.template").read() \
        .replace("%version%", versionDict["version"]) \
        .replace("%licensefile%", join(os.getcwd(), "dist", "license.txt")) \
        .replace("%distdir%", join(os.getcwd(), "dist"))
issfile = open("kofoto.iss", "w")
issfile.write(template)
