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

shutil.copy("src/gkofoto/start-installed.py", "kofoto.py")
windows = ["kofoto.py"]
sys.argv = [sys.argv[0], "py2exe"]

setup.run(options=options, windows=windows)

os.unlink("kofoto.py")
shutil.rmtree(glob.glob("dist/tcl")[0])
os.remove(glob.glob("dist/tcl*.dll")[0])
os.remove(glob.glob("dist/tk*.dll")[0])

k = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, "Software\\GTK\\2.0")
gtkdir = _winreg.QueryValueEx(k, "Path")[0]
for dir in ["etc", "lib", "share"]:
    destdir = join("dist", dir)
    if not isdir(destdir):
        os.mkdir(destdir)
    for subdir in glob.glob(join(gtkdir, dir, "*")):
        subdestdir = join(destdir, basename(subdir))
        print "copying %s --> %s" % (subdir, subdestdir)
        if not isdir(subdestdir):
            shutil.copytree(subdir, subdestdir)

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
