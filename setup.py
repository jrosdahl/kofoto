#! /usr/bin/env python

from distutils.core import setup
import os

package_dir = {
    "": "src/lib",
    "kofoto": "src/lib/kofoto",
    "gnomekofoto": "src/gnome/gnomekofoto",
    }
packages = [
    "kofoto",
    "kofoto.output",
    "gnomekofoto",
    ]
scripts = [
    "src/cmdline/renameimage",
    "src/cmdline/kofoto",
    "src/cmdline/kofoto-upload",
    "src/gnome/gkofoto",
    ]
data_files = [
    ("share/gnomekofoto/glade", ["src/gnome/glade/gkofoto.glade"]),
    ("share/gnomekofoto/icons", ["src/gnome/icons/album.png",
                                 "src/gnome/icons/fullscreen-24.png",
                                 "src/gnome/icons/objectview.png",
                                 "src/gnome/icons/tableview.png",
                                 "src/gnome/icons/thumbnailsview.png"])
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
