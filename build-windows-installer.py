#! /usr/bin/env python

import setup
import shutil

shutil.copy("src/gkofoto/start-installed.py", "gkofoto-start.pyw")
scripts = [
    "src/cmdline/kofoto",
    "gkofoto-start.pyw",
    "src/gkofoto/scripts/gkofoto-windows-postinstall.py",
    ]
sys.argv = [
    sys.argv[0],
    "bdist_wininst",
    "--install-script",
    "gkofoto-windows-postinstall.py"]
setup.run(scripts=scripts)
os.unlink("gkofoto-start.pyw")
