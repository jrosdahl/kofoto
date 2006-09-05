#! /usr/bin/env python

import os
import sys
from optparse import OptionParser
import warnings
from pylint import lint

def disable_message(arguments, message_id):
    arguments.append("--disable-msg=%s" % message_id)

######################################################################

option_parser = OptionParser()
option_parser.add_option(
    "--all",
    action="store_true",
    help="perform all checks",
    default=False)
option_parser.add_option(
    "--all-complexity",
    action="store_true",
    help="perform all complexity checks",
    default=False)
options, args = option_parser.parse_args(sys.argv[1:])

topdir = os.path.dirname(sys.argv[0])

sys.path.insert(0, os.path.join(topdir, "src/packages"))
if len(args) > 0:
    modules = args
else:
    modules = ["kofoto"]

normally_disabled_tests = [
    "C0103", # "Invalid name"
    "C0111", # "Missing docstring"
    "I0011", # "Locally disabling ..."
    "R0201", # "Method could be a function"
    "R0801", # "Similar lines ..."
    "W0142", # "Used * or ** magic."
    "W0212", # "Access to a protected member foo of a client class"
    "W0511", # "TODO ..."
    "W0704", # "Except doesn't do anything."
]

normally_disabled_complexity_tests = [
    "C0302", # "Too many lines in module"
    "R0901", # "Too many parent classes."
    "R0902", # "Too many instance attributes."
    "R0903", # "Not enough public methods."
    "R0904", # "Too many public methods."
    "R0911", # "Too many return statement."
    "R0912", # "Too many branches."
    "R0913", # "Too many arguments."
    "R0914", # "Too many local variables."
    "R0915", # "Too many statements."
    "C0301", # "Line too long."
]

rc_file_location = os.path.join(topdir, "misc/pylintrc")
flags = ["--rcfile", rc_file_location]
if not options.all:
    for x in normally_disabled_tests:
        disable_message(flags, x)
    if not options.all_complexity:
        for x in normally_disabled_complexity_tests:
            disable_message(flags, x)

lint.Run(flags + modules)
