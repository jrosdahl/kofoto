#! /usr/bin/env python

import glob
import os
import py2exe
import setup
import shutil
import sys

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
shutil.rmtree(glob.glob(os.path.join("dist", "tcl"))[0])
os.remove(glob.glob(os.path.join("dist", "tcl*.dll"))[0])
os.remove(glob.glob(os.path.join("dist", "tk*.dll"))[0])

import _winreg
import msvcrt
k = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, "Software\\GTK\\2.0")
gtkdir = _winreg.QueryValueEx(k, "Path")[0]
for dir in ["etc", "lib", "share"]:
    destdir = os.path.join("dist", dir)
    if not os.path.isdir(destdir):
        os.mkdir(destdir)
    for subdir in glob.glob(os.path.join(gtkdir, dir, "*")):
        subdestdir = os.path.join(destdir, os.path.basename(subdir))
        print "%s --> %s" % (subdir, subdestdir)
        if not os.path.isdir(subdestdir):
            shutil.copytree(subdir, subdestdir)
