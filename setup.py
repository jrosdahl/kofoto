#! /usr/bin/env python

from distutils.core import setup
setup(
    name="kofoto",
    version="0.0.0",
    package_dir={
        "": "src/lib",
        "kofoto": "src/lib/kofoto",
        "gnomekofoto": "src/gnome/gnomekofoto"},
    packages=["kofoto", "kofoto.output", "gnomekofoto"],
    py_modules=["EXIF"],
    scripts=[
        "src/cmdline/renameimage",
        "src/cmdline/kofoto",
        "src/gnome/gkofoto"],
    data_files=[
        ("share/gnomekofoto/glade", ["src/gnome/glade/gkofoto.glade"]),
        ("share/gnomekofoto/icons", ["src/gnome/icons/fullscreen-24.png"])],
    author="Kofoto developers",
    author_email="10711@lyskom.lysator.liu.se",
    url="http://svn.rosdahl.net/kofoto/kofoto/")
