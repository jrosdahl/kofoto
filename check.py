#! /usr/bin/env python

import sys
from pylint import lint

sys.path.insert(0, "src/packages")
if len(sys.argv) > 1:
    modules = sys.argv[1:]
else:
    modules = ["kofoto", "kofoto.commandline", "kofoto.output"]

tests_to_disable = [
    "C0101", # "Too short variable name."
    "W0142", # "Used * or ** magic."
    "W0704", # "Except doesn't do anything."
]

lint.Run(
    ["--rcfile", "misc/pylintrc"] +
    ["--disable-msg=" + x for x in tests_to_disable] +
    modules)
