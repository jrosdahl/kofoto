#! /usr/bin/env python

from distutils.core import setup
import os

package_dir = {
    "": "src/lib",
    "kofoto": "src/lib/kofoto",
    "gkofoto": "src/gkofoto",
    }
packages = [
    "kofoto",
    "kofoto.output",
    "gkofoto",
    ]
scripts = [
    "src/cmdline/renameimage",
    "src/cmdline/kofoto",
    "src/cmdline/kofoto-upload",
    "src/gkofoto/gkofoto",
    ]
data_files = [
    ("share/gkofoto/glade", ["src/gkofoto/glade/gkofoto.glade"]),
    ("share/gkofoto/icons", ["src/gkofoto/icons/album.png",
                             "src/gkofoto/icons/fullscreen-24.png",
                             "src/gkofoto/icons/objectview.png",
                             "src/gkofoto/icons/tableview.png",
                             "src/gkofoto/icons/thumbnailsview.png"])
    ]
if os.name == "posix":
    if os.system("cd src/web && make") != 0:
        import sys
        sys.exit(1)
    package_dir["kofotoweb"] = "src/web/kofotoweb"
    packages.append("kofotoweb")
    scripts.append("src/web/webkofoto")
    data_files.append(("share/kofotoweb/static", [
        "src/web/static/webkofoto.css",
        ]))

setup(
    name="kofoto",
    version="0.0.0",
    package_dir=package_dir,
    packages=packages,
    py_modules=["EXIF"],
    scripts=scripts,
    data_files=data_files,
    author="Kofoto developers",
    author_email="10711@lyskom.lysator.liu.se",
    url="http://svn.rosdahl.net/kofoto/kofoto/")
