#! /usr/bin/env python

from distutils.core import setup
import glob
import os
import shutil
import sys

package_dirs = {
    "kofoto": "src/lib/kofoto",
    "gkofoto": "src/gkofoto/gkofoto",
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
versionDict = {}
execfile("src/lib/kofoto/version.py", versionDict)
common_setup_options = {
    "name": "kofoto",
    "version": versionDict["version"],
    "description": "A tool for organizing and viewing images.",
    "package_dir": package_dirs,
    "packages": packages,
    "data_files": data_files,
    "author": "Joel Rosdahl and Ulrik Svensson",
    "author_email": "kofoto@rosdahl.net",
    "maintainer": "Joel Rosdahl and Ulrik Svensson",
    "maintainer_email": "kofoto@rosdahl.net",
    "url": "http://kofoto.rosdahl.net",
    "license": "BSD",
    "group": "Applications/Graphics",
    "requires": "python >= 2.3, gtk+ >= 2.2, glade >= 2.0, pygtk, sqlite >= 2.8, pysqlite, PIL",
}

def run(**setup_options):
    options = common_setup_options.copy()
    options.update(setup_options)
    setup(**options)

def unix_install():
    shutil.copy("src/gkofoto/start-installed.py", "gkofoto")
    setup_options = {
        "scripts": [
            "src/cmdline/kofoto",
            "gkofoto",
            ]
        }
    run(**setup_options)
    os.unlink("gkofoto")

if __name__ == "__main__":
    unix_install()
