#! /usr/bin/env python

from distutils.core import setup
import glob
import os
import shutil
import sys

if sys.argv[1] == "windows":
    windows_mode = True
    del sys.argv[1]
else:
    windows_mode = False

package_dir = {
    "kofoto": "src/lib/kofoto",
    "gkofoto": "src/gkofoto",
    }
packages = [
    "kofoto",
    "kofoto.output",
    "gkofoto",
    ]
data_files = [
    ("share/gkofoto/glade", ["src/gkofoto/glade/gkofoto.glade"]),
    ("share/gkofoto/icons", glob.glob("src/gkofoto/icons/*.png")),
    ]

if windows_mode:
    shutil.copy("src/gkofoto/start", "src/gkofoto/gkofoto-start.pyw")
    scripts = [
        "src/cmdline/kofoto",
        "src/gkofoto/gkofoto-start.pyw",
        "src/gkofoto/scripts/gkofoto-windows-postinstall.py",
        ]
else:
    shutil.copy("src/gkofoto/start", "src/gkofoto/gkofoto")
    scripts = [
        "src/cmdline/kofoto",
        "src/cmdline/kofoto-upload",
        "src/gkofoto/gkofoto",
        ]

versionDict = {}
execfile("src/lib/kofoto/version.py", versionDict)

setup(
    name="kofoto",
    version=versionDict["version"],
    description="A tool for organizing and viewing images.",
    package_dir=package_dir,
    packages=packages,
    scripts=scripts,
    data_files=data_files,
    author="Joel Rosdahl and Ulrik Svensson",
    author_email="kofoto@rosdahl.net",
    url="http://svn.rosdahl.net/kofoto/kofoto/",
    )

if windows_mode:
    os.unlink("src/gkofoto/gkofoto-start.pyw")
else:
    os.unlink("src/gkofoto/gkofoto")
