import sys
from gkofoto.environment import env
from gkofoto.controller import Controller

def main(bindir, argv):
    setupOk = env.setup(bindir)
    env.controller = Controller()
    env.controller.start(setupOk)
