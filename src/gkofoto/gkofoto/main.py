import sys
from kofoto.clientenvironment import DEFAULT_CONFIGFILE_LOCATION
from gkofoto.environment import env
from gkofoto.controller import Controller
from optparse import OptionParser

def main(bindir, argv):
    parser = OptionParser(version=env.version)
    parser.add_option(
        "--configfile",
        type="string",
        dest="configfile",
        help="use configuration file CONFIGFILE instead of the default (%s)" % (
            DEFAULT_CONFIGFILE_LOCATION),
        default=None)
    parser.add_option(
        "--database",
        type="string",
        dest="database",
        help="use metadata database DATABASE instead of the default (specified in the configuration file)",
        default=None)
    parser.add_option(
        "--debug",
        action="store_true",
        help="print debug messages to stdout",
        default=False)
    options, args = parser.parse_args(argv[1:])

    if len(args) != 0:
        parser.error("incorrect number of arguments")

    setupOk = env.setup(
        bindir, options.debug, options.configfile, options.database)
    env.controller = Controller()
    env.controller.start(setupOk)