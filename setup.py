#! /usr/bin/env python

from distutils.core import setup
import shutil
import os

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
    ("share/gkofoto/icons", ["src/gkofoto/icons/about-icon.png",
                             "src/gkofoto/icons/album.png",
                             "src/gkofoto/icons/fullscreen-24.png",
                             "src/gkofoto/icons/objectview.png",
                             "src/gkofoto/icons/rotateleft.png",
                             "src/gkofoto/icons/rotateright.png",
                             "src/gkofoto/icons/tableview.png",
                             "src/gkofoto/icons/thumbnailsview.png",
                             "src/gkofoto/icons/unknownimage.png"])
    ]

if os.name == "posix":
    shutil.copy("src/gkofoto/start", "src/gkofoto/gkofoto")
    scripts = [
        "src/cmdline/renameimage",
        "src/cmdline/kofoto",
        "src/cmdline/kofoto-upload",
        "src/gkofoto/gkofoto",
        ]
    if os.system("cd src/web && make") != 0:
        import sys
        sys.exit(1)
    package_dir["kofotoweb"] = "src/web/kofotoweb"
    packages.append("kofotoweb")
    scripts.append("src/web/webkofoto")
    data_files.append(("share/kofotoweb/static", [
        "src/web/static/webkofoto.css",
        ]))
else:
    shutil.copy("src/gkofoto/start", "src/gkofoto/gkofoto-start.pyw")
    scripts = [
        "src/cmdline/kofoto",
        "src/gkofoto/gkofoto-start.pyw",
        ]

versionDict = {}
execfile("src/lib/kofoto/version.py", versionDict)

setup(
    windows=["src/gkofoto/gkofoto-start.pyw"],
    name="kofoto",
    version=versionDict["version"],
    package_dir=package_dir,
    packages=packages,
    scripts=scripts,
    data_files=data_files,
    author="Joel Rosdahl and Ulrik Svensson",
    author_email="kofoto@rosdahl.net",
    url="http://svn.rosdahl.net/kofoto/kofoto/")

if os.name == "posix":
    os.unlink("src/gkofoto/gkofoto")
else:
    os.unlink("src/gkofoto/gkofoto-start.pyw")
