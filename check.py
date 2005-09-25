#! /usr/bin/env python

import sys
from pylint import lint

sys.path.insert(0, "src/packages")
lint.Run(["--rcfile", "misc/pylintrc", "kofoto.commandline"])
