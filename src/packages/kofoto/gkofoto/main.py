import os
import sys
from kofoto.clientenvironment import DEFAULT_CONFIGFILE_LOCATION
from kofoto.gkofoto.environment import env
from kofoto.gkofoto.controller import Controller
from optparse import OptionParser

def setupWindowsEnvironment(bindir):
    # Allow (default) datafile location to be determined under Windows 98.
    if os.path.expanduser("~") == "~":
        # Probably running under Windows 98 or similar OS where the
        # environment variables HOMEPATH and HOMEDRIVE (and HOME) are not
        # set. We have to fake it instead.
        try:
            import _winreg

            # Look up where "My Documents" lives.
            key = _winreg.OpenKey(
                _winreg.HKEY_CURRENT_USER,
                "Software\\Microsoft\\Windows\\CurrentVersion"
                "\\Explorer\\Shell Folders")
            home, dummy = _winreg.QueryValueEx(key, "Personal")
            # At this point home is _probably_ a Unicode string.
        except EnvironmentError:
            home = None

        if home == None:
            # Unable to look up the location so just make one up, however
            # nasty that location may be. We do output where the data
            # location is on gkofoto startup.
            home = "C:\\"

        os.environ["HOME"] = home
        # Note: Use os.environ as os.putenv() at least in Windows 98 only
        # changes variable for sub processes; this process would not see
        # the change.

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

    if sys.platform == "win32":
        setupWindowsEnvironment(bindir)

    setupOk = env.setup(
        bindir, options.debug, options.configfile, options.database)
    env.controller = Controller()
    env.controller.start(setupOk)
