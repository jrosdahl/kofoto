#! /usr/bin/env python

from distutils.core import setup
setup(
    name="kofoto",
    version="0.0.0",
    package_dir={
        "": "src/lib",
        "kofoto": "src/lib/kofoto",
        "gnomekofoto": "src/gnome/gnomekofoto"},
    packages=["kofoto", "gnomekofoto"],
    py_modules=["EXIF"],
    scripts=["src/cmdline/kofoto", "src/gnome/gkofoto"],
    data_files=[
        ("share/gnomekofoto/glade", ["src/gnome/glade/gkofoto.glade"]),
        ("share/gnomekofoto/icons", ["src/gnome/icons/fullscreen-24.png"])],
    author="Joel Rosdahl",
    author_email="joel@rosdahl.net",
    url="http://svn.rosdahl.net/kofoto/kofoto/")
