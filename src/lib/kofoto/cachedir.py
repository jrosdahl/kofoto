# Be compatible with Python 2.2.
from __future__ import generators

from os import listdir, mkdir, rmdir
from os.path import exists, join

class CacheDir:
    def __init__(self, basename):
        self.basename = basename
        if not exists(basename):
            mkdir(basename)

    def getFilepath(self, filename):
        for dir in [join(self.basename, filename[0]),
                    join(self.basename, filename[0], filename[1])]:
            if not exists(dir):
                mkdir(dir)
        return join(self.basename, filename[0], filename[1], filename)

    def getAllFilenames(self):
        for dir in listdir(self.basename):
            for subdir in listdir(join(self.basename, dir)):
                for filename in listdir(join(self.basename, dir, subdir)):
                    yield join(self.basename, dir, subdir, filename)

    def cleanup(self):
        for dir in listdir(self.basename):
            for subdir in listdir(join(self.basename, dir)):
                abssubdir = join(self.basename, dir, subdir)
                if not listdir(abssubdir):
                    rmdir(abssubdir)
